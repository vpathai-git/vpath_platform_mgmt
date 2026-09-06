#!/usr/bin/env python3
"""Fail when a credential value can reach a console, a log or a tracked file.

Why this exists
---------------
An install run of the platform pipeline printed account passwords in clear text
on stdout, so every captured install log carried them
(``analysis/mars-install/credentials-in-install-logs.issue.md``).  Filtering the
logs afterwards would be a fallback: the value has already been written, and the
next run writes it again.  The only honest fix is that the value never reaches
an output call -- and a gate that fails when one does.

The three rules
---------------
All three are **value-free by construction**: this checker never needs to know a
secret in order to detect one, so it never has to store one.

``SOURCE``
    An output call must not carry a credential-named symbol.  In Python an AST
    walk finds ``print``, ``logging.*`` and the other calls in
    :data:`OUTPUT_CALLS`.  In shell -- and in the embedded shell that the gradle
    ``.kts`` scripts carry in raw strings -- the same rule reads ``log::*``,
    ``echo`` and ``printf`` and fails when a credential-named *expansion*
    (``$PASSWORD``, ``${TOKEN}``) is interpolated into the message.  This is the
    rule that prevents new leaks.

    One shape is deliberately not a log: an output call whose whole argument is
    a single bare expansion (``echo "$SECRET"``) is a function's return channel,
    and every caller in this platform captures it.  A value woven into a message
    (``echo "Password: $PASSWORD"``) is a log line and fails.  ``printf -v``
    assigns to a variable and never reaches an output at all.

``LITERAL``
    A credential-named symbol must not be assigned a quoted literal -- the
    classic hardcoded secret.  Checked in Python via the AST and in
    shell/env/yaml text via a strict ``KEY=VALUE`` shape.  One shape under this
    rule points instead of holding: the bare ``secrets: inherit`` keyword in a
    ``.github/workflows`` file is GitHub Actions' by-reference pass of the
    caller's secrets to a reusable workflow, so no value is present -- quoted,
    renamed or moved elsewhere, it fails again.

``URL``
    A password must not sit inside a connection string.  The userinfo shape
    ``scheme://user:password@host`` hides a credential from every key-based rule
    above, because the DSN's own key (``DATABASE_URL``) names a location, not a
    secret.  The rule matches the *shape*, never a value -- and it is written so
    that this very sentence passes: a userinfo segment that reads ``password``
    names the field rather than filling it.

``PIPELINE``
    A tracked file must not carry an unredacted line in one of the shapes the
    install pipeline emits (:data:`PIPELINE_SHAPES`).  This guards the artifacts
    already in the tree against a careless re-import of a raw run log.

What this checker does NOT claim
--------------------------------
An **unlabelled** secret sitting in running text is not detectable without
knowing the value, and no heuristic here pretends otherwise.  A value-shaped
guess was tried and rejected: on this repository it produced seven findings and
all seven were syntax, not secrets (a type annotation ``api_key: str``, a call
``token = authenticate(...)``, the status word ``canonical``).  A rule that is
pure noise gets suppressed in practice and then guards nothing.  ``SOURCE``
prevents the emission instead, which is the durable half.

Exit codes
----------
    0   no violation
    1   at least one violation (each printed as ``path:line``)
    2   the checker could not run -- never a pass
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

EXIT_OK = 0
EXIT_VIOLATION = 1
EXIT_UNDETERMINED = 2

# A symbol whose name says it holds a credential.  Deliberately narrow: a bare
# `key` matches SSH_KEY paths and cache keys, which are not secrets.
CREDENTIAL_RE = re.compile(
    r"(?i)(password|passwd|\bpwd\b|secret|token|credential|api[_-]?key"
    r"|private[_-]?key|client[_-]?secret)"
)

# A name that merely says *where* a secret lives, or counts something called a
# token, is not itself a secret.  Without this, a k8s manifest's `secretName`
# and an LLM call's `max_tokens` drown the real findings -- measured against the
# server checkout, these two alone accounted for 103 of 235 hits.
REFERENCE_RE = re.compile(r"""(?ix)
    ^(
        .*secret[_-]?(name|namespace|store|ref|key|path|file|id|provider|type)s?
      | (max|min|prompt|completion|total|num|input|output|cached?)[_-]?tokens?
      | tokens?[_-]?(count|limit|used|usage|budget)
      | .*password[_-]?(policy|length|len|file|path|env|var|hash|prompt)
      | env[_-]?var[_-]?in[_-]?secret
      # Shell adds its own vocabulary of pointing-at rather than holding.  Every
      # one of these was measured against the server checkout: a counter, a
      # location or a collection, never a value.
      | .*[_-](count|counter|max|attempt|attempts|retries|url|uri|endpoint
              |size|len|length|hash|digest)
      | .*(map|list|args|opts)
    )$
    """)


def names_a_credential(name: str) -> bool:
    """Does this identifier hold a secret, rather than point at one?"""
    return bool(CREDENTIAL_RE.search(name)) and not REFERENCE_RE.match(name)


# Calls that put their arguments where a human or a log file can read them.
OUTPUT_CALLS = frozenset(
    {
        "print",
        "warn",
        "debug",
        "info",
        "warning",
        "error",
        "critical",
        "exception",
        "log",
    }
)
WRITE_TARGETS = frozenset({"stdout", "stderr"})

# A right-hand side that is a placeholder rather than a value.
PLACEHOLDER_RE = re.compile(r"""(?ix)
    ^(
        [<{\[(].*           # <value>, {{ var }}, [redacted], (unset)
      | \$.*                # $VAR, ${VAR}
      | .*redacted.*
      | \*+
      | x{3,}
      | \.{3,}
      | -+
      | (your|my|the|example|sample|dummy|fake|test)[-_].*
      | changeme
      # A value that names where the real one lives.  The server's schema
      # example declares exactly this convention in
      # config/schemas/example.config.yaml:39-41 and then relies on a reader
      # honouring it -- so the gate honours it too, and can hold the file to it.
      | reference[_-]?to[_-].*
      # An author's explicit declaration that this string guards nothing.  Narrow
      # on purpose -- each of these states non-production intent *inside the
      # value*, so hiding a real secret behind one takes a deliberate lie.  A
      # bare prefix like `dev-` or `sandbox-` is NOT enough and is not accepted.
      | .*not[-_]a[-_](secret|live[-_]secret).*
      | .*do[-_]not[-_]use.*
      | .*(local|dev|development)[-_]testing[-_]only.*
      | mock[-_].*
      | none | null | true | false | unset | empty | unused | n/?a
      | %[sd]
    )$
    """)

REDACTION_MARKER = "redacted-credential"

# The shapes the install pipeline emits.  A tracked file may carry these lines
# only in redacted form.  Both were taken from the mars12 run logs.
PIPELINE_SHAPES = (
    re.compile(r"^\s*\*?\s*Password:\s*\S"),
    re.compile(r"^\[info\]\s+\S+\s*/\s*\S+\s*\("),
)

# A hardcoded secret in shell/env/yaml: KEY=value, with nothing but a comment
# allowed after it.  An annotation or a call can never match this shape.
SHELL_LITERAL_RE = re.compile(r"""(?ix)
    ^\s*(export\s+)?
    (?P<key>[A-Za-z_][A-Za-z0-9_]*)
    \s*[:=]\s*
    (?P<quote>['"]?)(?P<value>[^'"\s#]+)(?P=quote)
    \s*(\#.*)?$
    """)

# An output call in shell, at a command position.  ``log::*`` is this platform's
# logging vocabulary (``lib/log.sh``); ``echo``/``printf`` are the bare ones.
SHELL_OUTPUT_RE = re.compile(r"""(?x)
    (?:^|[;&|(]|\bthen\s|\bdo\s|\belse\s|&&|\|\|)\s*
    (?P<call>log::[A-Za-z_]+|echo|printf)\b
    (?P<args>[^;&|]*)
    """)

# ``$NAME``, ``${NAME}``, ``${NAME:-default}`` -- what the shell interpolates.
SHELL_EXPANSION_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")

# What a printf may carry besides its expansions without becoming a message:
# format directives, escapes, quotes, flags and whitespace.
PRINTF_NOISE_RE = re.compile(r"%[-+ #0-9.]*[a-zA-Z]|\\[nrt0]|['\"]|\s+|^-[a-zA-Z]+")

# A credential embedded in a connection string: scheme://user:password@host.
# Shape only -- the value is never read, only its position.
URL_CREDENTIAL_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s/:@]+:(?P<secret>[^\s/@\"']+)@"
)

SOURCE_SUFFIXES = frozenset({".py"})
# ``.kts`` earns its place here rather than in a Kotlin group of its own: the
# gradle scripts in this platform carry their real work as shell inside
# ``trimIndent()`` raw strings, so the shell rules are the rules that apply.
# It was missing until 2026-07-28, which left 27 tracked files unscanned --
# among them the writer that renders the demo cheat sheet.
SHELL_SUFFIXES = frozenset({".sh", ".env", ".yaml", ".yml", ".cfg", ".ini", ".kts"})
TEXT_SUFFIXES = SOURCE_SUFFIXES | SHELL_SUFFIXES | frozenset({".md", ".txt", ".log"})


class CheckError(Exception):
    """The checker could not establish the facts it needs.  Never a pass."""


@dataclass(frozen=True)
class Violation:
    """One place a credential value can be read.  Carries no value, ever."""

    path: Path
    line: int
    rule: str
    detail: str

    def render(self, root: Path) -> str:
        shown = (
            self.path.relative_to(root) if self.path.is_relative_to(root) else self.path
        )
        return f"{shown}:{self.line}: [{self.rule}] {self.detail}"


# --- Rule SOURCE ----------------------------------------------------------


def _call_name(node: ast.Call) -> str:
    """The bare name an output call is made under, or "" for anything else."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        if func.attr == "write":
            inner = func.value
            return (
                "write"
                if isinstance(inner, ast.Attribute) and inner.attr in WRITE_TARGETS
                else ""
            )
        return func.attr
    return ""


# Builtins that turn a value into a fact *about* the value.  `len(token)` is a
# count, and a count is what an honest diagnostic prints instead of the token.
MEASURING_CALLS = frozenset({"len"})


def _referenced_symbols(node: ast.AST) -> Iterator[str]:
    """Every identifier-ish string an expression reaches for.

    Does not descend into a measuring call: whatever ``len(...)`` wraps leaves
    that call as an integer, so the symbol inside it never reaches the output.
    """
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in MEASURING_CALLS
    ):
        return
    if isinstance(node, ast.Name):
        yield node.id
    elif isinstance(node, ast.Attribute):
        yield node.attr
    for child in ast.iter_child_nodes(node):
        yield from _referenced_symbols(child)


def _output_args(node: ast.Call) -> list[ast.AST]:
    args: list[ast.AST] = list(node.args)
    args += [kw.value for kw in node.keywords if kw.arg not in ("file", "end", "sep")]
    return args


def _scan_output_calls(path: Path, tree: ast.AST) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in OUTPUT_CALLS and name != "write":
            continue
        for part in _output_args(node):
            hit = next(
                (s for s in _referenced_symbols(part) if names_a_credential(s)), None
            )
            if hit is not None:
                yield Violation(
                    path,
                    node.lineno,
                    "SOURCE",
                    f"output call {name!r} carries credential-named symbol {hit!r}",
                )
                break


# --- Rule LITERAL ---------------------------------------------------------


def _assigned_names(node: ast.AST) -> Iterator[str]:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            yield from _referenced_symbols(target)
    elif isinstance(node, ast.AnnAssign):
        yield from _referenced_symbols(node.target)


def _scan_python_literals(path: Path, tree: ast.AST) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        if not value.value or PLACEHOLDER_RE.match(value.value):
            continue
        hit = next((n for n in _assigned_names(node) if names_a_credential(n)), None)
        if hit is not None:
            yield Violation(
                path, node.lineno, "LITERAL", f"{hit!r} is assigned a string literal"
            )


def _is_inherited_workflow_secrets(path: Path, match: re.Match[str]) -> bool:
    """Is this GitHub Actions' by-reference ``secrets: inherit``?

    A job that calls a reusable workflow passes the caller's secrets on by
    reference with the bare keyword ``inherit``.  No value is present in the
    file, so the LITERAL shape rule must not fire on it.  Deliberately narrow,
    and case-sensitive: the key must be exactly ``secrets`` and the value
    exactly ``inherit``, unquoted, in a ``.github/workflows`` YAML file.
    ``SECRETS: inherit``, ``secrets: "inherit"``, ``secrets: inheritance`` and
    the same line in a shell or non-workflow file all stay violations -- a
    quoted scalar is indistinguishable here from a literal that happens to read
    ``inherit``, and the guard keeps the safer verdict.
    """
    return (
        match.group("key") == "secrets"
        and not match.group("quote")
        and match.group("value") == "inherit"
        and path.suffix in {".yml", ".yaml"}
        and path.parent.name == "workflows"
        and path.parent.parent.name == ".github"
    )


def _scan_shell_literals(path: Path, text: str) -> Iterator[Violation]:
    for number, line in enumerate(text.splitlines(), start=1):
        match = SHELL_LITERAL_RE.match(line)
        if match is None:
            continue
        key = match.group("key")
        if not names_a_credential(key):
            continue
        if _is_inherited_workflow_secrets(path, match):
            continue
        if PLACEHOLDER_RE.match(match.group("value")):
            continue
        yield Violation(path, number, "LITERAL", f"{key!r} is assigned a literal value")


# --- Rule SOURCE, shell half ----------------------------------------------

SHELL_EXPANSION_FULL_RE = re.compile(
    r"\$\{[A-Za-z_][A-Za-z0-9_]*[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*"
)


def _is_return_channel(call: str, args: str) -> bool:
    """Does this call hand a value back to a caller rather than log it?

    ``echo "$SECRET"`` is how a shell function returns a value, and every caller
    of that shape in this platform captures the output.  ``printf -v`` does not
    even reach a stream.  A log function is never a return channel, and neither
    is a call that weaves the value into a message.
    """
    if call.startswith("log::"):
        return False
    if re.match(r"\s*-v\b", args):
        return True
    if len(SHELL_EXPANSION_FULL_RE.findall(args)) != 1:
        return False
    residue = PRINTF_NOISE_RE.sub("", SHELL_EXPANSION_FULL_RE.sub("", args))
    return residue == ""


def _without_command_substitution(line: str) -> str:
    """Blank out ``$(...)`` spans, keeping every other column in place.

    A command substitution is a capture, not a stream.  This settles two shapes
    at once: an output call *inside* one hands its text to the shell
    (``ERR=$(printf '%s' "$TOKEN_RESP")`` writes nothing), and an output call
    that *contains* one prints the subshell's verdict rather than the variable
    (``echo "has colon: $([[ "$TOKEN" == *:* ]] && echo yes)"``).  Both were
    real false alarms on the server checkout before this existed.
    """
    out = list(line)
    depth = 0
    index = 0
    while index < len(line):
        if depth == 0:
            if line.startswith("$(", index):
                depth = 1
                out[index] = out[index + 1] = " "
                index += 2
                continue
        else:
            if line[index] == "(":
                depth += 1
            elif line[index] == ")":
                depth -= 1
            out[index] = " "
        index += 1
    return "".join(out)


def _scan_shell_output_calls(path: Path, text: str) -> Iterator[Violation]:
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _without_command_substitution(raw)
        for match in SHELL_OUTPUT_RE.finditer(line):
            call, args = match.group("call"), match.group("args")
            if _is_return_channel(call, args):
                continue
            hit = next(
                (
                    name
                    for name in SHELL_EXPANSION_RE.findall(args)
                    if names_a_credential(name)
                ),
                None,
            )
            if hit is not None:
                yield Violation(
                    path,
                    number,
                    "SOURCE",
                    f"output call {call!r} interpolates credential-named {hit!r}",
                )
                break


# --- Rule URL -------------------------------------------------------------


def _scan_url_credentials(path: Path, text: str) -> Iterator[Violation]:
    for number, line in enumerate(text.splitlines(), start=1):
        for match in URL_CREDENTIAL_RE.finditer(line):
            secret = match.group("secret")
            # A DSN whose password position reads exactly "password" names the
            # field instead of filling it, and `${PGPASSWORD}` is a reference.
            # `fullmatch`, never `search`: a real value that merely *contains*
            # the word -- `notarealsecret` -- must still fail, and did not until
            # the red drill caught this exemption swallowing it.
            if PLACEHOLDER_RE.match(secret) or CREDENTIAL_RE.fullmatch(secret):
                continue
            yield Violation(
                path,
                number,
                "URL",
                "connection string carries a password in its userinfo",
            )
            break


# --- Rule PIPELINE --------------------------------------------------------


def _scan_pipeline_shapes(path: Path, text: str) -> Iterator[Violation]:
    for number, line in enumerate(text.splitlines(), start=1):
        if REDACTION_MARKER in line:
            continue
        if any(shape.search(line) for shape in PIPELINE_SHAPES):
            yield Violation(
                path,
                number,
                "PIPELINE",
                "install-pipeline credential line is not redacted",
            )


# --- driving --------------------------------------------------------------


def tracked_files(root: Path) -> list[Path]:
    """Every file git tracks.  Untracked scratch is not this gate's business."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CheckError("git not found -- cannot establish the tracked set") from exc
    if result.returncode != 0:
        raise CheckError(f"git ls-files failed in {root}: {result.stderr.strip()}")
    names = [n for n in result.stdout.split("\0") if n]
    if not names:
        raise CheckError(f"git tracks no files in {root} -- refusing to pass")
    return [root / n for n in names]


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _scan_one(path: Path, text: str) -> Iterator[Violation]:
    if path.suffix in SOURCE_SUFFIXES:
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:  # a file we cannot parse is not a pass
            raise CheckError(f"{path}: cannot parse: {exc}") from exc
        yield from _scan_output_calls(path, tree)
        yield from _scan_python_literals(path, tree)
    if path.suffix in SHELL_SUFFIXES:
        yield from _scan_shell_literals(path, text)
        yield from _scan_shell_output_calls(path, text)
    yield from _scan_url_credentials(path, text)
    yield from _scan_pipeline_shapes(path, text)


def scan(root: Path, paths: Iterable[Path], excludes: Sequence[str]) -> list[Violation]:
    """Run every rule over the given files, in path order."""
    found: list[Violation] = []
    for path in sorted(paths):
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        if any(rel.startswith(prefix) for prefix in excludes):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        text = _read(path)
        if text is not None:
            found.extend(_scan_one(path, text))
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-no-logged-credentials",
        description="Fail when a credential value can reach a log or a console.",
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        help="repo-relative path prefix to skip (repeatable)",
    )
    parsed = parser.parse_args(argv)
    root = parsed.root.resolve()
    excludes = parsed.exclude if parsed.exclude is not None else [".claude/skills/"]

    try:
        violations = scan(root, tracked_files(root), excludes)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_UNDETERMINED

    for violation in violations:
        print(violation.render(root))
    if violations:
        print(
            f"\nFAIL: {len(violations)} place(s) where a credential value can be "
            f"read. Redact at the source; do not filter the output.",
            file=sys.stderr,
        )
        return EXIT_VIOLATION
    print("OK: no credential value reaches a console, a log or a tracked file.")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
