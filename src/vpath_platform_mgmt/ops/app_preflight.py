"""Refuse a repository that cannot build once it lands in the server tree.

The recorded port failure (docs/ops_isolation_plan/07_app_source_delivery.md)
materialized source cleanly and then died in the image build on
``Can't resolve '@vpath/sdk'``: the repository declared
``file:../../kit/sdk``, its own layout, while the server serves the SDK at
``apps_infra/sdk``. That class of failure is cheap to see in the manifest and
the dependency files, and expensive to see on the build host.

Every check answers one question -- would this tree still make sense once it
sits at ``apps_infra/apps/<name>/``? -- so paths are resolved against that
directory rather than pattern-matched. A dependency leaving the app is not
wrong by itself: ``spec.build.sdks`` is exactly how an app declares one, and
every app in ``apps/`` uses it. The manifest is therefore consulted rather than
guessed at, and the only thing that can be wrong is the path.

This module only looks. It writes nothing and reaches nothing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from vpath_platform_mgmt.ops.app_layout import (
    as_file_path,
    home_of,
    inside,
    read_build,
    resolve,
)

MANIFEST = "vpath-app.yaml"
NODE_MANIFEST = "package.json"
PYTHON_MANIFEST = "pyproject.toml"
DEPENDENCY_KEYS = ("dependencies", "devDependencies", "optionalDependencies")

# ponytail: pyproject is scanned line-wise for path dependencies rather than
# parsed, because a finding quotes the offending line verbatim.
# Upgrade trigger: FIRED — the floor is 3.11, so tomllib
# is available; the swap changes the finding text and belongs in its own change.
PATH_DEPENDENCY = re.compile(r"""(?<![\w-])path\s*=\s*["']([^"']+)["']""")
DEPENDENCY_NAME = re.compile(r"""^\s*["']?([A-Za-z][\w.-]*)["']?\s*=""")


class PreflightError(Exception):
    """The repository cannot be published as it stands; nothing was written."""


@dataclass(frozen=True)
class Finding:
    """One reason a repository is not publishable, and how to fix it."""

    file: str
    value: str
    remedy: str

    @property
    def text(self) -> str:
        return f"{self.file}: {self.value} — {self.remedy}"


def _load_json(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{path.name} is not readable JSON: {exc}") from exc
    return parsed if isinstance(parsed, dict) else {}


def _file_dependencies(parsed: dict[str, object]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for key in DEPENDENCY_KEYS:
        block = parsed.get(key)
        if not isinstance(block, dict):
            continue
        for name, spec in block.items():
            if isinstance(spec, str) and spec.startswith("file:"):
                found.append((str(name), spec))
    return found


def unresolvable_node_deps(tree: Path, app: str) -> list[Finding]:
    """``file:`` dependencies that will not resolve from the server tree.

    Leaving the app's own directory is not the fault: the pipeline puts an
    app's declared SDKs in the tree beside it. Not being where the manifest
    says they are is.
    """
    manifest = tree / NODE_MANIFEST
    if not manifest.is_file():
        return []
    sdks = read_build(tree).sdks
    found: list[Finding] = []
    for name, spec in _file_dependencies(_load_json(manifest)):
        resolved = resolve(app, spec.removeprefix("file:"))
        if inside(app, resolved):
            continue
        source = sdks.get(name)
        if source is None:
            found.append(
                Finding(
                    NODE_MANIFEST,
                    f"{name} = {spec}",
                    f"resolves to {resolved}, which the server does not put in "
                    f"the tree — declare {name} in spec.build.sdks, or vendor it",
                )
            )
        elif resolved != source:
            found.append(
                Finding(
                    NODE_MANIFEST,
                    f"{name} = {spec}",
                    f"resolves to {resolved}, but spec.build.sdks puts {name} "
                    f"at {source} — change it to {as_file_path(app, source)}",
                )
            )
    return found


def _dependency_name(line: str, before: int) -> str:
    """The key a ``path = "..."`` belongs to, when the line carries one.

    ``vpath-backend-sdk = { path = "..." }`` names its dependency; a bare
    ``path = "..."`` under a ``[tool.poetry.dependencies.x]`` header does not,
    and must not be reported as a dependency called "path".
    """
    match = DEPENDENCY_NAME.match(line)
    return match.group(1) if match is not None and match.end() <= before else ""


def unresolvable_python_deps(tree: Path, app: str) -> list[Finding]:
    """``path = "..."`` dependencies that will not resolve from the tree.

    Stated name-wise, exactly as the node rule is: a declared SDK pointing at
    the wrong place is told which path to write, not told to declare what it
    has already declared.
    """
    manifest = tree / PYTHON_MANIFEST
    if not manifest.is_file():
        return []
    sdks = read_build(tree).sdks
    found: list[Finding] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = PATH_DEPENDENCY.search(line)
        if match is None:
            continue
        name = _dependency_name(line, match.start())
        resolved = resolve(app, match.group(1))
        if inside(app, resolved):
            continue
        source = sdks.get(name) if name else None
        if source is None:
            found.append(
                Finding(
                    PYTHON_MANIFEST,
                    line.strip(),
                    f"resolves to {resolved}, which the server does not put in "
                    f"the tree — declare {name or 'it'} in spec.build.sdks, or "
                    "publish it to an index",
                )
            )
        elif resolved != source:
            corrected = as_file_path(app, source).removeprefix("file:")
            found.append(
                Finding(
                    PYTHON_MANIFEST,
                    line.strip(),
                    f"resolves to {resolved}, but spec.build.sdks puts {name} "
                    f'at {source} — change path to "{corrected}"',
                )
            )
    return found


def foreign_hash_dirs(tree: Path, app: str) -> list[Finding]:
    """``spec.build.hash.dirs`` entries nothing in the manifest accounts for.

    Hashing a declared SDK is correct -- the app must rebuild when the SDK it
    consumes changes -- so the allowed set is this app plus its declared SDKs.
    """
    build = read_build(tree)
    allowed = {home_of(app), *(source for source in build.sdks.values() if source)}
    expected = ", ".join(sorted(allowed))
    return [
        Finding(
            MANIFEST,
            f"spec.build.hash.dirs: {entry}",
            "the content hash covers this app and the SDKs it declares — "
            f"expected one of {expected}",
        )
        for entry in build.hash_dirs
        if entry not in allowed
    ]


def missing_entrypoint(tree: Path, runtime: str) -> list[Finding]:
    """Whether the detected runtime has something to build."""
    if runtime == "node":
        manifest = tree / NODE_MANIFEST
        if not manifest.is_file():
            return [
                Finding(
                    NODE_MANIFEST,
                    "absent",
                    "a node app is built through its package.json; add one",
                )
            ]
        scripts = _load_json(manifest).get("scripts")
        if not isinstance(scripts, dict) or not scripts.get("build"):
            return [
                Finding(
                    NODE_MANIFEST,
                    "no build script",
                    "the image build runs the package's build step; "
                    "add scripts.build",
                )
            ]
        return []
    if runtime == "python":
        if not (tree / PYTHON_MANIFEST).is_file():
            return [
                Finding(
                    PYTHON_MANIFEST,
                    "absent",
                    "a python app is built through its pyproject.toml; add one",
                )
            ]
        return []
    raise PreflightError(
        f"cannot inspect an app with runtime '{runtime}' (expected node or python)"
    )


def inspect(tree: Path, app: str, runtime: str) -> list[Finding]:
    """Every reason this repository is not publishable, in one pass."""
    root = Path(tree)
    return [
        *unresolvable_node_deps(root, app),
        *unresolvable_python_deps(root, app),
        *foreign_hash_dirs(root, app),
        *missing_entrypoint(root, runtime),
    ]


def require_publishable(tree: Path, app: str, runtime: str) -> None:
    """Pass silently, or refuse naming every finding at once."""
    findings = inspect(tree, app, runtime)
    if not findings:
        return
    detail = "\n  ".join(finding.text for finding in findings)
    raise PreflightError(f"'{app}' cannot be published as it stands:\n  {detail}")
