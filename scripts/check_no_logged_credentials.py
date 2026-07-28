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
    An output call must not carry a credential-named symbol.  An AST walk finds
    ``print``, ``logging.*`` and the other calls in :data:`OUTPUT_CALLS`, and
    fails when an argument reaches for a name or attribute that looks like a
    credential.  This is the rule that prevents new leaks.

``LITERAL``
    A credential-named symbol must not be assigned a quoted literal -- the
    classic hardcoded secret.  Checked in Python via the AST and in
    shell/env/yaml text via a strict ``KEY=VALUE`` shape.

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
      | none | null | true | false | unset | empty
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

SOURCE_SUFFIXES = frozenset({".py"})
SHELL_SUFFIXES = frozenset({".sh", ".env", ".yaml", ".yml", ".cfg", ".ini"})
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


def _referenced_symbols(node: ast.AST) -> Iterator[str]:
    """Every identifier-ish string an expression reaches for."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            yield child.id
        elif isinstance(child, ast.Attribute):
            yield child.attr


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


def _scan_shell_literals(path: Path, text: str) -> Iterator[Violation]:
    for number, line in enumerate(text.splitlines(), start=1):
        match = SHELL_LITERAL_RE.match(line)
        if match is None:
            continue
        key = match.group("key")
        if not names_a_credential(key):
            continue
        if PLACEHOLDER_RE.match(match.group("value")):
            continue
        yield Violation(path, number, "LITERAL", f"{key!r} is assigned a literal value")


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
