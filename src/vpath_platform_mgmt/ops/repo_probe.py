"""Read the few files registration needs, without cloning the repository.

Registering an app needs three files and a commit sha — its manifest, and
whichever of ``package.json`` / ``pyproject.toml`` reveals the runtime. Cloning
to get them fails in two ways that have nothing to do with the app: an INTERNAL
repository is invisible to git unless its credential helper happens to hold a
token, and a deep tree overruns Windows' path limit during checkout even with
``core.longpaths`` set.

So this asks GitHub instead, through ``gh``, which already holds the operator's
authentication. We never see or store a token — that is the point of borrowing
gh rather than handling credentials here.

The probed files are written into a temporary directory, so the registry keeps
inspecting a plain directory and cannot tell the difference between a probe and
a clone. Cloning is still the right tool for *sending* an app, where the whole
tree genuinely is the payload — that half lives in ``repo_tarball``, split out
to keep each module under the project's line limit.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from vpath_platform_mgmt.ops.repo_fetch import FetchError, RunResult, Runner, run

PROBE_FILES = ("vpath-app.yaml", "package.json", "pyproject.toml")
API_TIMEOUT_SECONDS = 60
HOSTS = ("github.com", "www.github.com")
SAFE_PATH_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class Probed:
    """What the repository says about itself, at one commit."""

    slug: str
    ref: str
    commit: str
    files: dict[str, str] = field(default_factory=dict)
    path: str = ""

    @property
    def repo_url(self) -> str:
        return f"https://github.com/{self.slug}.git"


def _check_segments(value: str, kind: str) -> None:
    """Refuse anything that is not plainly ``/``-joined safe path segments.

    Owner, repository, ref and path are all concatenated into the same
    credentialed ``gh api`` URL. A stray ``?`` in any of them would become the
    URL's *first* ``?`` and let the caller's own text choose what is served;
    a ``..`` segment would walk to a different resource entirely. So each is
    refused rather than rewritten into something safe.
    """
    for segment in value.split("/"):
        if segment == ".." or not SAFE_PATH_SEGMENT.match(segment):
            raise FetchError(
                f"'{value}' is not a usable {kind} — only letters, digits, "
                "'.', '_' and '-' segments joined by '/' are allowed, with "
                "no '..'"
            )


def parse_slug(url: str) -> str:
    """``owner/repo`` from anything a human pastes, or refuse.

    Only GitHub is understood here; any other host has to be cloned, and the
    caller is told so rather than being handed a wrong guess.
    """
    trimmed = url.strip().removesuffix(".git")
    for prefix in ("https://", "http://", "ssh://", "git@"):
        trimmed = trimmed.removeprefix(prefix)
    trimmed = trimmed.replace("github.com:", "github.com/")
    parts = [part for part in trimmed.split("/") if part]
    if len(parts) < 3 or parts[0] not in HOSTS:
        raise FetchError(
            f"'{url}' is not a github.com repository — only GitHub can be "
            "registered without cloning"
        )
    _check_segments(parts[1], "repository owner")
    _check_segments(parts[2], "repository name")
    return f"{parts[1]}/{parts[2]}"


def clean_ref(ref: str) -> str:
    """A branch, tag or sha safe to put in a URL path, or a refusal.

    ``ref`` becomes a path segment in ``repos/<slug>/commits/<ref>``, so it
    gets exactly the validation ``path`` gets and for the same reason.
    """
    trimmed = ref.strip()
    if not trimmed:
        raise FetchError("no ref given — name the branch, tag or commit to read")
    _check_segments(trimmed, "ref")
    return trimmed


def _gh(args: Sequence[str], runner: Runner) -> RunResult:
    return runner(["gh", *args], API_TIMEOUT_SECONDS)


def resolve_commit(slug: str, ref: str, runner: Runner = run) -> str:
    """The sha ``ref`` points at, so provenance records a commit not a branch."""
    result = _gh(["api", f"repos/{slug}/commits/{ref}", "--jq", ".sha"], runner)
    sha = result.stdout.strip()
    if not result.ok or not sha:
        raise FetchError(_why(slug, ref, result))
    return sha


def read_file(slug: str, ref: str, path: str, runner: Runner = run) -> str | None:
    """One file's text, or None when the repository does not have it."""
    result = _gh(
        ["api", f"repos/{slug}/contents/{path}?ref={ref}", "--jq", ".content"], runner
    )
    if not result.ok:
        return None
    encoded = result.stdout.strip()
    if not encoded:
        return None
    try:
        return base64.b64decode(encoded).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise FetchError(f"{slug}: {path} is not readable text ({exc})") from exc


def _clean_path(path: str) -> str:
    """A repository-relative directory, or a refusal naming what broke.

    Leading and trailing slashes are the one thing normalised away, because a
    pasted ``/examples/app/`` is still unambiguously that directory. The
    result is what every stage below uses, so ``Probed.path`` and not the
    operator's raw text is what reaches the registry and the send stage.
    """
    trimmed = path.strip("/")
    if trimmed:
        _check_segments(trimmed, "path")
    return trimmed


def probe(url: str, ref: str = "main", runner: Runner = run, path: str = "") -> Probed:
    """Resolve the commit and read the files registration depends on.

    ``path`` selects the app within the repository. An organisation repository
    is often a workspace whose root is not an app at all, and reading its root
    would describe the workspace rather than the app -- so the caller says
    which directory it means, and empty means the repository itself.

    The files are read at the *resolved commit*, never at ``ref``: a branch
    that moves between the two calls would otherwise have the gate inspect and
    the registry record a manifest that is not the one the tarball ships.
    """
    slug = parse_slug(url)
    prefix = _clean_path(path)
    resolved = clean_ref(ref)
    commit = resolve_commit(slug, resolved, runner)
    found = {}
    for name in PROBE_FILES:
        text = read_file(slug, commit, f"{prefix}/{name}" if prefix else name, runner)
        if text is not None:
            found[name] = text
    return Probed(slug=slug, ref=resolved, commit=commit, files=found, path=prefix)


def materialise(probed: Probed, into: Path) -> Path:
    """Write the probed files so the registry sees an ordinary directory."""
    target = Path(into)
    target.mkdir(parents=True, exist_ok=True)
    for name, text in probed.files.items():
        (target / name).write_text(text, encoding="utf-8")
    return target


def _why(slug: str, ref: str, result: RunResult) -> str:
    """gh's own message, which distinguishes 'not found' from 'no access'."""
    detail = (result.stderr or result.stdout).strip()
    for line in reversed(detail.splitlines()):
        if line.strip():
            detail = line.strip()
            break
    if "Not Found" in detail or "404" in detail:
        detail = (
            f"{detail} — if the repository is private or INTERNAL, check "
            "'gh auth status' covers that organisation"
        )
    try:
        parsed = json.loads(result.stdout or "{}")
        detail = str(parsed.get("message", detail))
    except json.JSONDecodeError:
        pass
    return f"cannot read {slug} at ref '{ref}': {detail}"
