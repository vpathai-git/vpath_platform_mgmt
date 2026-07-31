# App Publish Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One console action takes an organisation's repository URL and leaves the app running under ArgoCD.

**Architecture:** A `PublishPipeline` sequences five stages — preflight, register, send, render, install — delegating each to the unit that already owns it. Only the preflight gate is new logic; the rest is wiring. The pipeline runs as a normal `Job` through `OpsService.submit`, so RBAC, audit and the per-app lock apply unchanged.

**Tech Stack:** Python 3.10+, FastAPI, typer, pytest, PyYAML, httpx. No new dependencies.

## Global Constraints

Copied verbatim from `AGENTS.md`; every task's requirements implicitly include these.

- Max 250 lines per file; split into a subfolder module if larger.
- Type hints are required on all public functions; docstrings on public APIs.
- No comments unless critical; self-documenting names; no debug prints in commits. A deliberate simplification is critical: record it as one `# ponytail: <what was skipped>, <upgrade trigger>` marker.
- Cross-platform always: use `pathlib.Path` / `os.path.join()`, and `encoding="utf-8"` on file operations.
- Work in the files that exist; create one only when the task needs it. No unsolicited docs; deliver exactly the requested scope.
- Minimalism first: stdlib before native platform before existing dependency before new code.
- Every non-trivial change leaves a regression test that fails if reverted.
- Coverage must stay at or above 85%; `make check` is the completion gate.
- No fallbacks, no soft passes, no silent degradation. Fail hard with a clear message.
- `pyproject.toml` `[project.dependencies]` is the source of truth; `requirements.txt` mirrors it. **This plan adds no dependency, so neither file is touched and `make scan` is not required.**

**Python floor is 3.10.** `tomllib` is 3.11+ and is therefore unavailable. Task 1 handles this explicitly.

**Quality gate:** `make check` (credentials → black → flake8 → mypy → pytest with `--cov-fail-under=85`). Line length 88.

---

### Task 1: The preflight gate

**Files:**
- Create: `src/vpath_platform_mgmt/ops/app_preflight.py`
- Test: `tests/test_ops_app_preflight.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces:
  - `Finding(file: str, value: str, remedy: str)` — frozen dataclass, with `text` property returning `f"{file}: {value} — {remedy}"`.
  - `PreflightError(Exception)`
  - `inspect(tree: Path, app: str, runtime: str) -> list[Finding]`
  - `require_publishable(tree: Path, app: str, runtime: str) -> None` — raises `PreflightError` listing every finding at once.

Task 4 calls `require_publishable` only.

**The rule this gate enforces.** Every check answers one question — would this
tree still make sense once it sits at `apps_infra/apps/<name>/`? Paths are
therefore *resolved* against that directory, never pattern-matched.

A dependency leaving the app is not wrong by itself. Every app already in
`apps/` declares the SDK it consumes:

```yaml
    hash:
      dirs: [apps_infra/apps/vpath-knowledge-builder, apps_infra/sdk]
    sdks:
      - name: "@vpath/sdk"
        source: apps_infra/sdk
```

`spec.build.sdks` is the server pipeline's own SDK mapping, so both the second
`hash.dirs` entry and the escaping `file:` dependency are *expected*. Only the
path can be wrong:

> For every `spec.build.sdks[]` entry, the `file:` dependency of the same name
> must resolve, relative to `apps_infra/apps/<name>`, to that entry's `source`.

`file:../../kit/sdk` resolves to `apps_infra/kit/sdk`, which does not exist;
`file:../../sdk` resolves to `apps_infra/sdk`, which is what the manifest
names. That single mismatch is the recorded build failure, and the refusal
names the fix. A rule that simply refused every escaping dependency would
reject a correct app for a reason that is not its bug.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ops_app_preflight.py`:

```python
"""The gate that refuses a repository which cannot build on the server."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from vpath_platform_mgmt.ops.app_preflight import (
    PreflightError,
    inspect,
    require_publishable,
)


def write(tree: Path, name: str, text: str) -> None:
    (tree / name).write_text(text, encoding="utf-8")


APP = "vpath-knowledge-builder"
SDK_SOURCE = "apps_infra/sdk"


def manifest(
    app: str, dirs: list[str], sdks: list[dict[str, str]] | None = None
) -> str:
    build: dict[str, object] = {"runtime": "node", "hash": {"dirs": dirs}}
    if sdks is not None:
        build["sdks"] = sdks
    return yaml.safe_dump(
        {
            "apiVersion": "vpath/v1",
            "kind": "VpathApp",
            "metadata": {"name": app},
            "spec": {"build": build},
        },
        sort_keys=False,
    )


def package(dependencies: dict[str, str] | None = None, build: bool = True) -> str:
    body: dict[str, object] = {"name": APP}
    if build:
        body["scripts"] = {"build": "next build"}
    if dependencies is not None:
        body["dependencies"] = dependencies
    return json.dumps(body)


def plain_tree(tmp_path: Path) -> Path:
    """An app with no SDK: one hashed directory and its own dependencies."""
    write(tmp_path, "package.json", package())
    write(tmp_path, "vpath-app.yaml", manifest(APP, [f"apps_infra/apps/{APP}"]))
    return tmp_path


def sdk_tree(tmp_path: Path, dependency: str) -> Path:
    """The real vpath-knowledge-builder shape, with one dependency path.

    Its manifest declares the SDK it consumes and hashes it so a change to the
    SDK rebuilds the app. Both are correct; only the dependency path can be
    wrong.
    """
    write(tmp_path, "package.json", package({"@vpath/sdk": dependency}))
    write(
        tmp_path,
        "vpath-app.yaml",
        manifest(
            APP,
            [f"apps_infra/apps/{APP}", SDK_SOURCE],
            [{"name": "@vpath/sdk", "source": SDK_SOURCE}],
        ),
    )
    return tmp_path


def test_a_self_contained_node_repo_has_no_findings(tmp_path: Path) -> None:
    assert inspect(plain_tree(tmp_path), APP, "node") == []


def test_a_declared_sdk_resolving_where_the_manifest_says_is_clean(
    tmp_path: Path,
) -> None:
    """apps_infra/apps/<name>/../../sdk is apps_infra/sdk — exactly the source."""
    assert inspect(sdk_tree(tmp_path, "file:../../sdk"), APP, "node") == []


def test_the_recorded_sdk_failure_is_refused(tmp_path: Path) -> None:
    """Regression guard for the port failure in 07_app_source_delivery.md.

    Source materialized cleanly and the image build then died on
    'Can't resolve @vpath/sdk': the repository declares file:../../kit/sdk,
    which resolves to apps_infra/kit/sdk, while its own manifest puts the SDK
    at apps_infra/sdk. Publishing must refuse before anything reaches the box,
    and must name the one-line fix.
    """
    findings = inspect(sdk_tree(tmp_path, "file:../../kit/sdk"), APP, "node")

    assert [f.file for f in findings] == ["package.json"]
    assert "file:../../kit/sdk" in findings[0].value
    assert "apps_infra/kit/sdk" in findings[0].remedy
    assert "file:../../sdk" in findings[0].remedy


def test_an_escaping_dependency_the_manifest_never_declares_is_refused(
    tmp_path: Path,
) -> None:
    """With no spec.build.sdks entry, nothing puts that directory in the tree."""
    write(tmp_path, "package.json", package({"@vpath/sdk": "file:../../sdk"}))
    write(tmp_path, "vpath-app.yaml", manifest(APP, [f"apps_infra/apps/{APP}"]))

    findings = inspect(tmp_path, APP, "node")

    assert [f.file for f in findings] == ["package.json"]
    assert "spec.build.sdks" in findings[0].remedy


def test_a_file_dependency_inside_the_app_tree_is_allowed(tmp_path: Path) -> None:
    write(tmp_path, "package.json", package({"@demo/ui": "file:./packages/ui"}))
    write(tmp_path, "vpath-app.yaml", manifest(APP, [f"apps_infra/apps/{APP}"]))

    assert inspect(tmp_path, APP, "node") == []


def test_hashing_a_directory_no_sdk_declares_is_a_finding(tmp_path: Path) -> None:
    write(tmp_path, "package.json", package())
    write(
        tmp_path,
        "vpath-app.yaml",
        manifest(APP, [f"apps_infra/apps/{APP}", SDK_SOURCE]),
    )

    findings = inspect(tmp_path, APP, "node")

    assert [f.file for f in findings] == ["vpath-app.yaml"]
    assert SDK_SOURCE in findings[0].value


def test_hash_dirs_naming_another_app_is_a_finding(tmp_path: Path) -> None:
    write(tmp_path, "package.json", package())
    write(tmp_path, "vpath-app.yaml", manifest(APP, ["apps_infra/apps/other-app"]))

    findings = inspect(tmp_path, APP, "node")

    assert [f.file for f in findings] == ["vpath-app.yaml"]
    assert "other-app" in findings[0].value


def test_a_python_path_dependency_the_manifest_never_declares_is_a_finding(
    tmp_path: Path,
) -> None:
    write(
        tmp_path,
        "pyproject.toml",
        '[project]\nname = "demo-api"\n\n'
        "[tool.poetry.dependencies]\n"
        'vpath-backend-sdk = { path = "../../sdk-python/vpath-backend-sdk" }\n',
    )
    write(
        tmp_path, "vpath-app.yaml", manifest("demo-api", ["apps_infra/apps/demo-api"])
    )

    findings = inspect(tmp_path, "demo-api", "python")

    assert [f.file for f in findings] == ["pyproject.toml"]


def test_a_python_path_dependency_a_declared_sdk_covers_is_allowed(
    tmp_path: Path,
) -> None:
    """The real backend-SDK shape, as every python app in apps/ declares it."""
    source = "apps_infra/sdk-python/vpath-backend-sdk"
    write(
        tmp_path,
        "pyproject.toml",
        '[project]\nname = "demo-api"\n\n'
        "[tool.poetry.dependencies]\n"
        'vpath-backend-sdk = { path = "../../sdk-python/vpath-backend-sdk" }\n',
    )
    write(
        tmp_path,
        "vpath-app.yaml",
        manifest(
            "demo-api",
            ["apps_infra/apps/demo-api", source],
            [{"name": "vpath-backend-sdk", "source": source}],
        ),
    )

    assert inspect(tmp_path, "demo-api", "python") == []


def test_a_node_repo_without_a_build_script_is_a_finding(tmp_path: Path) -> None:
    write(tmp_path, "package.json", package(build=False))
    write(tmp_path, "vpath-app.yaml", manifest(APP, [f"apps_infra/apps/{APP}"]))

    findings = inspect(tmp_path, APP, "node")

    assert [f.file for f in findings] == ["package.json"]
    assert "scripts.build" in findings[0].remedy


def test_a_node_repo_without_a_package_json_is_a_finding(tmp_path: Path) -> None:
    write(tmp_path, "vpath-app.yaml", manifest(APP, [f"apps_infra/apps/{APP}"]))

    assert len(inspect(tmp_path, APP, "node")) == 1


def test_an_unknown_runtime_is_refused_not_ignored(tmp_path: Path) -> None:
    with pytest.raises(PreflightError, match="ruby"):
        inspect(plain_tree(tmp_path), APP, "ruby")


def test_require_publishable_passes_the_real_manifest_shape(tmp_path: Path) -> None:
    require_publishable(sdk_tree(tmp_path, "file:../../sdk"), APP, "node")


def test_require_publishable_reports_every_finding_at_once(tmp_path: Path) -> None:
    write(
        tmp_path,
        "package.json",
        package({"@vpath/sdk": "file:../../kit/sdk"}, build=False),
    )
    write(
        tmp_path,
        "vpath-app.yaml",
        manifest(
            APP,
            ["apps_infra/apps/other-app", SDK_SOURCE],
            [{"name": "@vpath/sdk", "source": SDK_SOURCE}],
        ),
    )

    with pytest.raises(PreflightError) as failure:
        require_publishable(tmp_path, APP, "node")

    message = str(failure.value)
    assert "package.json" in message
    assert "vpath-app.yaml" in message
    assert "scripts.build" in message
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_ops_app_preflight.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'vpath_platform_mgmt.ops.app_preflight'`.

- [ ] **Step 3: Write the implementation**

Create `src/vpath_platform_mgmt/ops/app_preflight.py`:

```python
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
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

APPS_ROOT = "apps_infra/apps"
MANIFEST = "vpath-app.yaml"
NODE_MANIFEST = "package.json"
PYTHON_MANIFEST = "pyproject.toml"
DEPENDENCY_KEYS = ("dependencies", "devDependencies", "optionalDependencies")

# ponytail: pyproject is scanned line-wise for path dependencies rather than
# parsed, because tomllib is 3.11+ and this project's floor is 3.10; adding a
# TOML parser for one check is not worth a dependency.
# Upgrade trigger: the floor reaching 3.11 — replace with tomllib.
PATH_DEPENDENCY = re.compile(r"""path\s*=\s*["']([^"']+)["']""")


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


@dataclass(frozen=True)
class Build:
    """What the manifest says about building this app."""

    hash_dirs: tuple[str, ...]
    sdks: dict[str, str]


def _load_json(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{path.name} is not readable JSON: {exc}") from exc
    return parsed if isinstance(parsed, dict) else {}


def _build_block(tree: Path) -> dict[str, object]:
    manifest = tree / MANIFEST
    if not manifest.is_file():
        return {}
    parsed = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    spec = parsed.get("spec") if isinstance(parsed, dict) else None
    build = spec.get("build") if isinstance(spec, dict) else None
    return build if isinstance(build, dict) else {}


def read_build(tree: Path) -> Build:
    """The hashed directories and declared SDKs, however sparse the manifest."""
    block = _build_block(tree)
    hashed = block.get("hash")
    dirs = hashed.get("dirs") if isinstance(hashed, dict) else None
    declared = block.get("sdks")
    sdks: dict[str, str] = {}
    for entry in declared if isinstance(declared, list) else []:
        if isinstance(entry, dict) and entry.get("name"):
            sdks[str(entry["name"])] = str(entry.get("source", "")).strip("/")
    hashes = (
        tuple(str(entry).strip("/") for entry in dirs) if isinstance(dirs, list) else ()
    )
    return Build(hashes, sdks)


def home_of(app: str) -> str:
    """Where the server puts this app's own tree."""
    return f"{APPS_ROOT}/{app}"


def resolve(app: str, target: str) -> str:
    """Where a path written inside the app lands in the server tree."""
    if target.startswith("/"):
        return target.rstrip("/")
    return posixpath.normpath(f"{home_of(app)}/{target}")


def inside(app: str, resolved: str) -> bool:
    """Whether a resolved path is still the app's own directory."""
    home = home_of(app)
    return resolved == home or resolved.startswith(f"{home}/")


def as_file_path(app: str, source: str) -> str:
    """The dependency path an app would have to write to reach ``source``."""
    return f"file:{posixpath.relpath(source, home_of(app))}"


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


def unresolvable_python_deps(tree: Path, app: str) -> list[Finding]:
    """``path = "..."`` dependencies that will not resolve from the tree."""
    manifest = tree / PYTHON_MANIFEST
    if not manifest.is_file():
        return []
    sources = set(read_build(tree).sdks.values())
    found: list[Finding] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = PATH_DEPENDENCY.search(line)
        if match is None:
            continue
        resolved = resolve(app, match.group(1))
        if inside(app, resolved) or resolved in sources:
            continue
        found.append(
            Finding(
                PYTHON_MANIFEST,
                line.strip(),
                f"resolves to {resolved}, which the server does not put in the "
                "tree — declare it in spec.build.sdks, or publish it to an index",
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
    raise PreflightError(
        f"'{app}' cannot be published as it stands:\n  {detail}"
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/test_ops_app_preflight.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Check the file length**

```bash
python -c "print(sum(1 for _ in open('src/vpath_platform_mgmt/ops/app_preflight.py', encoding='utf-8')))"
```

Expected: under 250. If it is over, move `Build`, `read_build`, `home_of`,
`resolve`, `inside` and `as_file_path` into `ops/app_layout.py` and import
them — that split is along the seam between "where the server puts things"
and "what is wrong with this repository".

- [ ] **Step 6: Run the full gate**

```bash
make check
```

Expected: all steps pass, coverage at or above 85%.

- [ ] **Step 7: Commit**

```bash
git add src/vpath_platform_mgmt/ops/app_preflight.py tests/test_ops_app_preflight.py
git commit -m "feat: refuse a repo whose SDK path is not where its manifest says"
```

---

### Task 2: Provenance travels into the checkout

The send stage must be able to answer "sent at which commit" from the box alone, without asking this repository. Today `_place_manifest` copies only the manifest into the payload.

**Files:**
- Modify: `src/vpath_platform_mgmt/cli/app_cmds.py:251-262` (`_place_manifest`)
- Test: `tests/test_cli_app_send.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_place_registered_files(name: str, tree: Path, apps: Path) -> None` replacing `_place_manifest`. Copies both `vpath-app.yaml` and `vpath-source.yaml` from `apps/<name>/` into the payload root. Task 4 relies on `vpath-source.yaml` being present at `<checkout>/apps_infra/apps/<name>/vpath-source.yaml`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ops_app_preflight.py`? No — append to `tests/test_cli_app_send.py`:

```python
def test_the_payload_carries_provenance_so_the_box_knows_its_commit(
    tmp_path: Path,
) -> None:
    """The checkout must be able to say which commit it holds, on its own."""
    from vpath_platform_mgmt.cli.app_cmds import _place_registered_files

    apps = tmp_path / "apps"
    (apps / "demo-app").mkdir(parents=True)
    (apps / "demo-app" / "vpath-app.yaml").write_text("kind: VpathApp\n", encoding="utf-8")
    (apps / "demo-app" / "vpath-source.yaml").write_text(
        "commit: abc123\n", encoding="utf-8"
    )
    payload = tmp_path / "tree"
    payload.mkdir()

    _place_registered_files("demo-app", payload, apps)

    assert (payload / "vpath-app.yaml").read_text(encoding="utf-8") == "kind: VpathApp\n"
    assert (payload / "vpath-source.yaml").read_text(encoding="utf-8") == "commit: abc123\n"


def test_placing_files_refuses_when_the_manifest_is_missing(tmp_path: Path) -> None:
    from vpath_platform_mgmt.cli.app_cmds import _place_registered_files
    from vpath_platform_mgmt.ops.app_registry import RegistryError

    apps = tmp_path / "apps"
    (apps / "demo-app").mkdir(parents=True)
    payload = tmp_path / "tree"
    payload.mkdir()

    with pytest.raises(RegistryError, match="vpath-app.yaml"):
        _place_registered_files("demo-app", payload, apps)
```

Add `from pathlib import Path` and `import pytest` to the test module's imports if they are not already present.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_cli_app_send.py -v -k place
```

Expected: `ImportError: cannot import name '_place_registered_files'`.

- [ ] **Step 3: Replace `_place_manifest`**

In `src/vpath_platform_mgmt/cli/app_cmds.py`, replace the whole `_place_manifest` function with:

```python
REGISTERED_FILES = ("vpath-app.yaml", "vpath-source.yaml")


def _place_registered_files(name: str, tree: Path, apps: Path | None = None) -> None:
    """Put the registered manifest and its provenance in the payload.

    The server refuses an upload without a manifest, and a generated one lives
    only here -- so it has to travel. Provenance travels with it so the
    checkout can say which commit it holds without asking this repository,
    which is what lets a resumed publish skip a send that already happened.
    """
    root = apps if apps is not None else apps_root()
    for filename in REGISTERED_FILES:
        registered = root / name / filename
        if not registered.is_file():
            raise RegistryError(f"'{name}' has no {filename} at {registered}")
        shutil.copyfile(registered, tree / filename)
```

Update its one caller in `send` (currently `_place_manifest(name, tree, str(entry.get("manifest_origin", "")))`) to:

```python
        _place_registered_files(name, tree)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/test_cli_app_send.py -v
```

Expected: all pass, including the pre-existing send tests.

- [ ] **Step 5: Run the full gate**

```bash
make check
```

- [ ] **Step 6: Commit**

```bash
git add src/vpath_platform_mgmt/cli/app_cmds.py tests/test_cli_app_send.py
git commit -m "feat: send provenance with the source so the box knows its commit"
```

---

### Task 3: The app inside the repository

`vpathai-git/vpathai_publish_knowledge_app` is the repository this pipeline
exists for, and its root is **not** an app: it is `vpath-platform-app-template`,
an npm workspace root (`"private": true`, `"workspaces": ["examples/*"]`) with
no manifest and no build script. The apps live under `examples/`, and the one
being published is `examples/vpath-knowledge-builder`.

`probe` reads its three files at the repository root, so today registration
would refuse this repository as "ships no vpath-app.yaml, generate one" — the
wrong answer to a right repository. The app therefore has to be selected by a
path within the repository, and provenance has to record which one, or a later
`refresh` looks in the wrong place.

**Files:**
- Modify: `src/vpath_platform_mgmt/ops/repo_probe.py` (`Probed`, `probe`)
- Modify: `src/vpath_platform_mgmt/ops/app_registry.py` (`register`, `refresh`, `_write`)
- Test: `tests/test_ops_repo_probe.py`, `tests/test_ops_app_registry.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces:
  - `Probed.path: str = ""` — the directory within the repository that is the app.
  - `probe(url, ref="main", runner=run, path="") -> Probed`, reading `<path>/<file>` for each probed file.
  - `AppRegistry.register(..., path: str = "")`, recording `path` in `vpath-source.yaml`; `refresh` carries the recorded path forward.

Task 4 passes `request.path` into both, and packs the payload from that
subdirectory. `download_tree` is unchanged — the whole repository is still
downloaded once, and the subtree is selected from the extraction.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ops_repo_probe.py`, reusing the module's existing
`responder`, `encoded`, `SHA` and `MANIFEST` helpers:

```python
def test_the_app_may_live_in_a_subdirectory_of_the_repository() -> None:
    """A workspace root is not an app; examples/<app> is."""
    _, runner = responder(
        {
            "commits/main": RunResult(0, SHA + "\n", ""),
            "contents/examples/vpath-knowledge-builder/vpath-app.yaml": RunResult(
                0, encoded(MANIFEST), ""
            ),
        }
    )

    probed = probe(
        "github.com/org/repo",
        "main",
        runner,
        path="examples/vpath-knowledge-builder",
    )

    assert probed.path == "examples/vpath-knowledge-builder"
    assert probed.files == {"vpath-app.yaml": MANIFEST}


def test_a_probe_without_a_path_still_reads_the_repository_root() -> None:
    _, runner = responder(
        {
            "commits/main": RunResult(0, SHA + "\n", ""),
            "contents/vpath-app.yaml": RunResult(0, encoded(MANIFEST), ""),
        }
    )

    probed = probe("github.com/org/repo", "main", runner)

    assert probed.path == ""
    assert probed.files == {"vpath-app.yaml": MANIFEST}


def test_a_path_a_human_pasted_with_slashes_asks_a_clean_url() -> None:
    seen, runner = responder({"commits/main": RunResult(0, SHA + "\n", "")})

    probe("github.com/org/repo", "main", runner, path="/examples/app/")

    asked = [part for argv in seen for part in argv if "contents/" in part]
    assert asked
    assert all("contents/examples/app/" in part for part in asked)
```

Append to `tests/test_ops_app_registry.py`, following the tree fixtures that
module already uses:

```python
def test_provenance_records_which_directory_of_the_repo_is_the_app(
    tmp_path: Path,
) -> None:
    """A later refresh has to look in the same place, and only this says where."""
    registry, tree = registered_tree(tmp_path)

    result = registry.register(
        repo="https://github.com/org/repo.git",
        ref="main",
        commit="c" * 40,
        tree=tree,
        path="examples/vpath-knowledge-builder",
    )

    recorded = yaml.safe_load(
        (result.directory / "vpath-source.yaml").read_text(encoding="utf-8")
    )
    assert recorded["path"] == "examples/vpath-knowledge-builder"


def test_a_repository_that_is_itself_the_app_records_an_empty_path(
    tmp_path: Path,
) -> None:
    registry, tree = registered_tree(tmp_path)

    result = registry.register(
        repo="https://github.com/org/repo.git",
        ref="main",
        commit="c" * 40,
        tree=tree,
    )

    recorded = yaml.safe_load(
        (result.directory / "vpath-source.yaml").read_text(encoding="utf-8")
    )
    assert recorded["path"] == ""


def test_refresh_keeps_the_directory_the_app_was_registered_from(
    tmp_path: Path,
) -> None:
    registry, tree = registered_tree(tmp_path)
    result = registry.register(
        repo="https://github.com/org/repo.git",
        ref="main",
        commit="c" * 40,
        tree=tree,
        path="examples/vpath-knowledge-builder",
    )

    registry.refresh(result.name, tree, "d" * 40)

    recorded = yaml.safe_load(
        (result.directory / "vpath-source.yaml").read_text(encoding="utf-8")
    )
    assert recorded["path"] == "examples/vpath-knowledge-builder"
    assert recorded["commit"] == "d" * 40
```

`registered_tree` stands for whatever this module already uses to build a
tree carrying a `vpath-app.yaml`; use that instead of adding a fixture.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_ops_repo_probe.py tests/test_ops_app_registry.py -v -k "path or directory"
```

Expected: `TypeError: probe() got an unexpected keyword argument 'path'`, and
`KeyError: 'path'` from the registry tests.

- [ ] **Step 3: Let the probe read a subdirectory**

In `src/vpath_platform_mgmt/ops/repo_probe.py`, add the field to `Probed`:

```python
    path: str = ""
```

and give `probe` the parameter:

```python
def probe(
    url: str, ref: str = "main", runner: Runner = run, path: str = ""
) -> Probed:
    """Resolve the commit and read the files registration depends on.

    ``path`` selects the app within the repository. An organisation repository
    is often a workspace whose root is not an app at all, and reading its root
    would describe the workspace rather than the app -- so the caller says
    which directory it means, and empty means the repository itself.
    """
    slug = parse_slug(url)
    commit = resolve_commit(slug, ref, runner)
    prefix = path.strip("/")
    found = {}
    for name in PROBE_FILES:
        text = read_file(slug, ref, f"{prefix}/{name}" if prefix else name, runner)
        if text is not None:
            found[name] = text
    return Probed(slug=slug, ref=ref, commit=commit, files=found, path=prefix)
```

`materialise` is unchanged: it writes the probed files by their bare names, so
the registry keeps inspecting an ordinary directory.

- [ ] **Step 4: Record the path in provenance**

In `src/vpath_platform_mgmt/ops/app_registry.py`, add `path: str = ""` to
`register`'s signature and pass it into `_write`. Give `_write` the same
parameter and put it in the provenance mapping after `commit`:

```python
            "path": path,
```

In `refresh`, carry the recorded value forward:

```python
            path=str(previous.get("path", "")),
```

An entry registered before this task has no `path` key, which reads as the
repository root — the truth for every app registered so far.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
pytest tests/test_ops_repo_probe.py tests/test_ops_app_registry.py -v
```

Expected: all pass, including every pre-existing test in both modules.

- [ ] **Step 6: Run the full gate**

```bash
make check
```

- [ ] **Step 7: Commit**

```bash
git add src/vpath_platform_mgmt/ops/repo_probe.py src/vpath_platform_mgmt/ops/app_registry.py tests/test_ops_repo_probe.py tests/test_ops_app_registry.py
git commit -m "feat: an app may be a directory inside its repository"
```

---

### Task 4: The publish pipeline

**Files:**
- Create: `src/vpath_platform_mgmt/ops/publish.py`
- Test: `tests/test_ops_publish.py`

**Interfaces:**
- Consumes: `app_preflight.require_publishable` (Task 1); `_place_registered_files` (Task 2); `probe(..., path=)` and `AppRegistry.register(..., path=)` (Task 3); `SourceMaterializer.materialize/target_for` (existing); `LocalEngine.run` and `GitOpsEngine.run` (existing); `repo_probe.materialise/download_tree` (existing).
- Produces:
  - `PublishRequest(url: str, ref: str, name: str, path: str = "", generate: Generated | None = None, replace: bool = False)` — frozen dataclass.
  - `PublishError(Exception)`
  - `STAGES: tuple[str, ...] = ("preflight", "register", "send", "render", "install")`
  - `PublishPipeline.run(request: PublishRequest, actor: str, role: Role, emit: StepEmitter) -> dict[str, object]` returning `{"app": str, "commit": str, "stages": {name: "done" | "skipped"}}`.

Task 5 calls `run` only.

**`path` selects the app inside the repository** (Task 3). It reaches three
places: `probe` reads the manifest from there, `register` records it, and the
send stage packs *that subtree* rather than the whole repository — shipping a
workspace root would put five other apps into `apps_infra/apps/<name>`.

**Why only two stages are skippable:** render is idempotent by content hash (an unchanged app rebuilds nothing — `07_app_source_delivery.md`) and install is idempotent in `GitOpsEngine._deploy` ("already in the InstalledSet — verifying sync only"). Both therefore always run and cost nothing when nothing changed. Only register and send are skipped, and only when provenance records the exact commit being published.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ops_publish.py`:

```python
"""The five-stage walk from a repository URL to an app running under ArgoCD."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vpath_platform_mgmt.ops.model import Role, Verb
from vpath_platform_mgmt.ops.publish import (
    STAGES,
    PublishError,
    PublishPipeline,
    PublishRequest,
)


class FakeRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.registered: list[str] = []

    def entries(self) -> list[dict[str, object]]:
        found = []
        for folder in sorted(self.root.glob("*/vpath-source.yaml")):
            data = yaml.safe_load(folder.read_text(encoding="utf-8")) or {}
            found.append({"name": folder.parent.name, **data})
        return found

    def register(self, repo, ref, commit, tree, generate=None, replace=False):
        self.registered.append(f"{repo}@{commit}")
        target = self.root / "demo-app"
        target.mkdir(parents=True, exist_ok=True)
        (target / "vpath-app.yaml").write_text("kind: VpathApp\n", encoding="utf-8")
        (target / "vpath-source.yaml").write_text(
            yaml.safe_dump({"repo": repo, "ref": ref, "commit": commit}),
            encoding="utf-8",
        )
        from vpath_platform_mgmt.ops.app_registry import Registration

        return Registration("demo-app", target, "upstream", commit)


class FakeMaterializer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[str] = []

    def target_for(self, app: str) -> Path:
        return self.root / app

    def materialize(self, app, archive_bytes, provenance, replace=False):
        self.calls.append(app)
        target = self.target_for(app)
        target.mkdir(parents=True, exist_ok=True)
        (target / "vpath-source.yaml").write_text(
            yaml.safe_dump({"commit": provenance.commit}), encoding="utf-8"
        )
        return {"app": app, "file_count": 1, "target": str(target), "replaced": False}


class FakeEngine:
    def __init__(self, name: str, fails: str = "") -> None:
        self.name = name
        self.fails = fails
        self.jobs: list[Verb] = []

    def run(self, job, emit):
        from vpath_platform_mgmt.ops.engine import EngineFailure

        self.jobs.append(job.verb)
        emit(f"{self.name} ran {job.verb.value}")
        if self.fails:
            raise EngineFailure(self.fails)
        return {"engine": self.name}


def build(tmp_path: Path, **overrides):
    apps = tmp_path / "apps"
    apps.mkdir(exist_ok=True)
    checkout = tmp_path / "checkout"
    checkout.mkdir(exist_ok=True)
    tree = tmp_path / "probe"
    tree.mkdir(exist_ok=True)

    parts = {
        "registry": FakeRegistry(apps),
        "materializer": FakeMaterializer(checkout),
        "local_engine": FakeEngine("local"),
        "gitops_engine": FakeEngine("gitops"),
        "probe": lambda url, ref, path="": _Probed(url, ref, path),
        "materialise": lambda probed, into: tree,
        "download": lambda slug, commit, into: tree,
        "bundle": lambda path: b"tar",
        "place": lambda name, payload, apps_dir=None: None,
        "inspect": lambda tree_, app, runtime: None,
        "runtime_of": lambda tree_: "node",
    }
    parts.update(overrides)
    return PublishPipeline(**parts), parts


class _Probed:
    def __init__(self, url: str, ref: str, path: str = "") -> None:
        self.slug = "org/demo-app"
        self.ref = ref
        self.path = path
        self.commit = "c" * 40
        self.repo_url = "https://github.com/org/demo-app.git"
        self.files = {"vpath-app.yaml": "kind: VpathApp\n"}


def request() -> PublishRequest:
    return PublishRequest(url="github.com/org/demo-app", ref="main", name="demo-app")


def test_a_clean_publish_walks_every_stage_in_order(tmp_path: Path) -> None:
    pipeline, parts = build(tmp_path)
    steps: list[str] = []

    result = pipeline.run(request(), "ops", Role.ADMIN, steps.append)

    assert list(result["stages"]) == list(STAGES)
    assert all(state == "done" for state in result["stages"].values())
    assert result["app"] == "demo-app"
    assert parts["local_engine"].jobs == [Verb.DEPLOY]
    assert parts["gitops_engine"].jobs == [Verb.DEPLOY]


def test_preflight_refusal_stops_before_anything_is_written(tmp_path: Path) -> None:
    from vpath_platform_mgmt.ops.app_preflight import PreflightError

    def refuse(tree_, app, runtime):
        raise PreflightError("dependency escapes the app tree")

    pipeline, parts = build(tmp_path, inspect=refuse)

    with pytest.raises(PublishError, match="preflight"):
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    assert parts["registry"].registered == []
    assert parts["materializer"].calls == []


def test_a_render_failure_names_its_stage(tmp_path: Path) -> None:
    pipeline, _ = build(tmp_path, local_engine=FakeEngine("local", fails="gradle blew up"))

    with pytest.raises(PublishError) as failure:
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    assert "render" in str(failure.value)
    assert "gradle blew up" in str(failure.value)


def test_register_is_skipped_when_provenance_already_records_this_commit(
    tmp_path: Path,
) -> None:
    pipeline, parts = build(tmp_path)
    pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)
    parts["registry"].registered.clear()

    result = pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    assert result["stages"]["register"] == "skipped"
    assert result["stages"]["send"] == "skipped"
    assert parts["registry"].registered == []
    assert parts["materializer"].calls == ["demo-app"]


def test_render_and_install_always_run_even_on_a_resumed_publish(
    tmp_path: Path,
) -> None:
    """Both are idempotent in the engine; skipping them could ship stale state."""
    pipeline, parts = build(tmp_path)
    pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    result = pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    assert result["stages"]["render"] == "done"
    assert result["stages"]["install"] == "done"
    assert parts["local_engine"].jobs == [Verb.DEPLOY, Verb.DEPLOY]


def test_a_manifest_naming_a_different_app_is_refused(tmp_path: Path) -> None:
    pipeline, _ = build(tmp_path)
    asked = PublishRequest(url="github.com/org/demo-app", ref="main", name="other-app")

    with pytest.raises(PublishError, match="other-app"):
        pipeline.run(asked, "ops", Role.ADMIN, lambda step: None)


def test_the_subtree_named_by_path_is_what_is_sent(tmp_path: Path) -> None:
    """Shipping a workspace root would put five other apps in the checkout."""
    packed: list[Path] = []

    def download(slug: str, commit: str, into: Path) -> Path:
        root = Path(into) / "tree"
        (root / "examples" / "demo-app").mkdir(parents=True)
        return root

    pipeline, _ = build(
        tmp_path,
        download=download,
        bundle=lambda path: (packed.append(Path(path)), b"tar")[1],
    )
    asked = PublishRequest(
        url="github.com/org/repo",
        ref="main",
        name="demo-app",
        path="examples/demo-app",
    )

    pipeline.run(asked, "ops", Role.ADMIN, lambda step: None)

    assert packed
    assert packed[0].name == "demo-app"
    assert packed[0].parent.name == "examples"


def test_a_path_that_is_not_in_the_repository_is_refused(tmp_path: Path) -> None:
    def download(slug: str, commit: str, into: Path) -> Path:
        root = Path(into) / "tree"
        root.mkdir(parents=True)
        return root

    pipeline, _ = build(tmp_path, download=download)
    asked = PublishRequest(
        url="github.com/org/repo",
        ref="main",
        name="demo-app",
        path="examples/absent",
    )

    with pytest.raises(PublishError, match="examples/absent"):
        pipeline.run(asked, "ops", Role.ADMIN, lambda step: None)


def test_every_stage_is_emitted_as_a_step(tmp_path: Path) -> None:
    pipeline, _ = build(tmp_path)
    steps: list[str] = []

    pipeline.run(request(), "ops", Role.ADMIN, steps.append)

    for stage in STAGES:
        assert any(stage in step for step in steps), stage
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_ops_publish.py -v
```

Expected: `ModuleNotFoundError: No module named 'vpath_platform_mgmt.ops.publish'`.

- [ ] **Step 3: Write the implementation**

Create `src/vpath_platform_mgmt/ops/publish.py`:

```python
"""From a repository URL to an app running under ArgoCD, in one walk.

Five stages, each delegated to the unit that already owns it: preflight
refuses a repository that cannot build, the registry writes the entry, the
materializer places the source in the server checkout, the local engine
renders and commits into the Deploy-of-Record, and the GitOps engine puts the
name in the InstalledSet and waits for ArgoCD.

This module sequences and nothing else -- no HTTP, no subprocess, no git, no
writes of its own -- so every failure is attributable to exactly one owner and
these tests need neither a network nor a box.

Resume is by observation, not by a stored ledger: provenance already records
which commit is registered and which is materialized, so a re-run skips what
genuinely happened. Render and install are never skipped, because both are
already idempotent in the engine -- an unchanged app rebuilds nothing, and an
app already in the InstalledSet only has its sync verified.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from vpath_platform_mgmt.ops.app_preflight import PreflightError
from vpath_platform_mgmt.ops.app_registry import Generated, RegistryError
from vpath_platform_mgmt.ops.engine import EngineFailure, StepEmitter
from vpath_platform_mgmt.ops.model import Job, Role, Verb
from vpath_platform_mgmt.ops.repo_fetch import FetchError
from vpath_platform_mgmt.ops.source import SourceError, SourceProvenance

STAGES: tuple[str, ...] = ("preflight", "register", "send", "render", "install")
PROVENANCE = "vpath-source.yaml"
DONE = "done"
SKIPPED = "skipped"


class PublishError(Exception):
    """A stage refused; the message names the stage and the reason."""


@dataclass(frozen=True)
class PublishRequest:
    """One repository, at one ref, published under one name."""

    url: str
    ref: str
    name: str
    path: str = ""
    generate: Generated | None = None
    replace: bool = False


def _recorded_commit(directory: Path) -> str:
    """The commit a provenance file records, or empty when there is none."""
    provenance = directory / PROVENANCE
    if not provenance.is_file():
        return ""
    data = yaml.safe_load(provenance.read_text(encoding="utf-8")) or {}
    return str(data.get("commit", "")) if isinstance(data, dict) else ""


class PublishPipeline:
    """Walks the five stages; every collaborator is injected."""

    def __init__(
        self,
        registry: Any,
        materializer: Any,
        local_engine: Any,
        gitops_engine: Any,
        probe: Callable[..., Any],
        materialise: Callable[..., Path],
        download: Callable[..., Path],
        bundle: Callable[[Path], bytes],
        place: Callable[..., None],
        inspect: Callable[..., None],
        runtime_of: Callable[[Path], str],
    ) -> None:
        self._registry = registry
        self._materializer = materializer
        self._local = local_engine
        self._gitops = gitops_engine
        self._probe = probe
        self._materialise = materialise
        self._download = download
        self._bundle = bundle
        self._place = place
        self._inspect = inspect
        self._runtime_of = runtime_of

    def run(
        self,
        request: PublishRequest,
        actor: str,
        role: Role,
        emit: StepEmitter,
    ) -> dict[str, object]:
        """Walk every stage, or fail hard naming the one that refused."""
        stages: dict[str, str] = {}
        workspace = Path(tempfile.mkdtemp(prefix="vpath-publish-"))
        try:
            probed = self._probed(request, workspace, emit)
            stages["preflight"] = self._preflight(request, probed, emit)
            stages["register"] = self._register(request, probed, emit)
            stages["send"] = self._send(request, probed, workspace, actor, emit)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
        stages["render"] = self._render(request, actor, role, emit)
        stages["install"] = self._install(request, actor, role, emit)
        return {"app": request.name, "commit": probed.commit, "stages": stages}

    def _probed(
        self, request: PublishRequest, workspace: Path, emit: StepEmitter
    ) -> Any:
        emit(f"reading {request.url} at {request.ref}")
        try:
            return self._probe(request.url, request.ref, path=request.path)
        except FetchError as exc:
            raise PublishError(f"preflight: {exc}") from exc

    def _preflight(
        self, request: PublishRequest, probed: Any, emit: StepEmitter
    ) -> str:
        emit(f"preflight: inspecting {request.name} at {probed.commit[:12]}")
        tree = Path(tempfile.mkdtemp(prefix="vpath-preflight-"))
        try:
            self._materialise(probed, tree)
            runtime = self._runtime_for(request, tree)
            self._inspect(tree, request.name, runtime)
        except (PreflightError, RegistryError) as exc:
            raise PublishError(f"preflight: {exc}") from exc
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        return DONE

    def _runtime_for(self, request: PublishRequest, tree: Path) -> str:
        if request.generate is not None and request.generate.runtime:
            return request.generate.runtime
        return self._runtime_of(tree)

    def _register(
        self, request: PublishRequest, probed: Any, emit: StepEmitter
    ) -> str:
        recorded = next(
            (
                entry
                for entry in self._registry.entries()
                if entry.get("name") == request.name
            ),
            None,
        )
        if recorded is not None and str(recorded.get("commit", "")) == probed.commit:
            emit(f"register: {request.name} already records {probed.commit[:12]}")
            return SKIPPED

        emit(f"register: writing apps/{request.name}")
        tree = Path(tempfile.mkdtemp(prefix="vpath-register-"))
        try:
            self._materialise(probed, tree)
            result = self._registry.register(
                repo=probed.repo_url,
                ref=request.ref,
                commit=probed.commit,
                tree=tree,
                path=request.path,
                generate=request.generate,
                replace=request.replace or recorded is not None,
            )
        except RegistryError as exc:
            raise PublishError(f"register: {exc}") from exc
        finally:
            shutil.rmtree(tree, ignore_errors=True)

        if result.name != request.name:
            raise PublishError(
                f"register: the repository's manifest names '{result.name}', "
                f"not '{request.name}' — publish under the name it declares"
            )
        return DONE

    def _send(
        self,
        request: PublishRequest,
        probed: Any,
        workspace: Path,
        actor: str,
        emit: StepEmitter,
    ) -> str:
        target = self._materializer.target_for(request.name)
        if _recorded_commit(target) == probed.commit:
            emit(f"send: the checkout already holds {probed.commit[:12]}")
            return SKIPPED

        emit(f"send: downloading {probed.slug} at {probed.commit[:12]}")
        try:
            downloaded = self._download(probed.slug, probed.commit, workspace)
            payload = self._subtree(downloaded, request.path)
            self._place(request.name, payload)
            archive = self._bundle(payload)
            summary = self._materializer.materialize(
                request.name,
                archive,
                SourceProvenance(
                    repo=probed.repo_url, ref=request.ref, commit=probed.commit
                ),
                replace=True,
            )
        except (FetchError, RegistryError, SourceError) as exc:
            raise PublishError(f"send: {exc}") from exc
        emit(f"send: placed {summary.get('file_count')} files in the checkout")
        return DONE

    @staticmethod
    def _subtree(downloaded: Path, path: str) -> Path:
        """The directory inside the repository that is the app.

        A repository is often a workspace whose root holds several apps;
        sending the root would put all of them in one app's directory. The
        path is operator input, so it is resolved and checked to stay inside
        the download rather than trusted.
        """
        if not path:
            return downloaded
        root = downloaded.resolve()
        target = (downloaded / path).resolve()
        if not target.is_dir() or root not in target.parents:
            raise PublishError(
                f"send: '{path}' is not a directory in this repository"
            )
        return target

    def _render(
        self, request: PublishRequest, actor: str, role: Role, emit: StepEmitter
    ) -> str:
        emit(f"render: building and committing {request.name}")
        self._engine_deploy(self._local, request, actor, role, "render", emit)
        return DONE

    def _install(
        self, request: PublishRequest, actor: str, role: Role, emit: StepEmitter
    ) -> str:
        emit(f"install: putting {request.name} in the InstalledSet")
        self._engine_deploy(self._gitops, request, actor, role, "install", emit)
        return DONE

    def _engine_deploy(
        self,
        engine: Any,
        request: PublishRequest,
        actor: str,
        role: Role,
        stage: str,
        emit: StepEmitter,
    ) -> None:
        job = Job(
            verb=Verb.DEPLOY,
            app=request.name,
            actor=actor,
            role=role,
            engine=engine.name,
        )
        try:
            engine.run(job, emit)
        except EngineFailure as exc:
            raise PublishError(f"{stage}: {exc}") from exc
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/test_ops_publish.py -v
```

Expected: 9 passed. If `PublishPipeline.__init__` exceeds the complexity limit, that is expected to pass — it is assignment only.

- [ ] **Step 5: Check the file length**

```bash
python -c "print(sum(1 for _ in open('src/vpath_platform_mgmt/ops/publish.py', encoding='utf-8')))"
```

Expected: under 250. If it is over, split the stage bodies into `ops/publish_stages.py` and keep `PublishPipeline` as the sequencer.

- [ ] **Step 6: Run the full gate**

```bash
make check
```

- [ ] **Step 7: Commit**

```bash
git add src/vpath_platform_mgmt/ops/publish.py tests/test_ops_publish.py
git commit -m "feat: walk a repo URL to a running app in five delegated stages"
```

---

### Task 5: The publish verb and its guardrails

**Files:**
- Modify: `src/vpath_platform_mgmt/ops/model.py:22-58` (`Verb`, `VERB_ROLE`, `lock_scope`), `src/vpath_platform_mgmt/ops/model.py:70-102` (`Job`)
- Modify: `src/vpath_platform_mgmt/ops/service.py:44-137` (`OpsService.__init__`, `submit`, `_run`)
- Test: `tests/test_ops_service.py`

**Interfaces:**
- Consumes: `PublishPipeline.run(request, actor, role, emit)` and `PublishRequest` (Task 4).
- Produces:
  - `Verb.PUBLISH = "publish"`, `VERB_ROLE[Verb.PUBLISH] = Role.ADMIN`, `lock_scope(Verb.PUBLISH, app) == f"app:{app}"`.
  - `Job.payload: dict[str, object] | None = None`, included in `to_dict()`.
  - `OpsService.__init__(..., publish: PublishPipeline | None = None)`.
  - `OpsService.submit(verb_name, app, actor, role_name, confirm="", payload=None) -> Job`.

Task 6 calls `submit("publish", name, actor, role, payload={...})`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ops_service.py`:

```python
def test_publish_requires_admin(simulated_service) -> None:
    from vpath_platform_mgmt.ops.model import RefusedError

    with pytest.raises(RefusedError, match="admin"):
        simulated_service.submit("publish", "demo-app", "dev", "app-dev")


def test_publish_without_a_pipeline_fails_the_job_naming_why() -> None:
    from vpath_platform_mgmt.ops.engine import SimulatedEngine
    from vpath_platform_mgmt.ops.model import JobState
    from vpath_platform_mgmt.ops.service import OpsService

    service = OpsService(SimulatedEngine(), instance_name="sim")
    job = service.submit("publish", "demo-app", "ops", "admin", payload={"url": "u"})
    service.wait(job.id)

    assert job.state is JobState.FAILED
    assert "publish" in job.log[-1]


def test_publish_dispatches_to_the_pipeline_not_the_engine() -> None:
    from vpath_platform_mgmt.ops.engine import SimulatedEngine
    from vpath_platform_mgmt.ops.model import JobState
    from vpath_platform_mgmt.ops.service import OpsService

    seen: list[str] = []

    class Pipeline:
        def run(self, request, actor, role, emit):
            seen.append(request.name)
            emit("pipeline ran")
            return {"app": request.name, "commit": "c" * 40, "stages": {}}

    service = OpsService(SimulatedEngine(), instance_name="sim", publish=Pipeline())
    job = service.submit(
        "publish",
        "demo-app",
        "ops",
        "admin",
        payload={"url": "github.com/org/demo-app", "ref": "main"},
    )
    service.wait(job.id)

    assert job.state is JobState.SUCCEEDED, job.log
    assert seen == ["demo-app"]
    assert job.result is not None and job.result["app"] == "demo-app"


def test_publish_holds_the_app_lock() -> None:
    from vpath_platform_mgmt.ops.model import Verb, lock_scope

    assert lock_scope(Verb.PUBLISH, "demo-app") == "app:demo-app"
```

If `simulated_service` is not an existing fixture in this module, construct the service inline the way the surrounding tests already do.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_ops_service.py -v -k publish
```

Expected: `UnknownVerbError: unknown verb 'publish'`.

- [ ] **Step 3: Add the verb and the payload**

In `src/vpath_platform_mgmt/ops/model.py`, add to `Verb`:

```python
    PUBLISH = "publish"
```

Add to `VERB_ROLE`:

```python
    Verb.PUBLISH: Role.ADMIN,
```

Add to `Job` after `result`:

```python
    payload: dict[str, object] | None = None
```

and include it in `to_dict()`:

```python
            "payload": self.payload,
```

`lock_scope` needs no change: publish is neither destructive nor a read, so it already returns `f"app:{app}"`.

- [ ] **Step 4: Dispatch publish to the pipeline**

In `src/vpath_platform_mgmt/ops/service.py`, add the constructor parameter:

```python
        publish: "PublishPipeline | None" = None,
```

with `self._publish = publish` in the body, and at the top of the module:

```python
from vpath_platform_mgmt.ops.publish import PublishError, PublishPipeline, PublishRequest
```

Give `submit` the payload:

```python
    def submit(
        self,
        verb_name: str,
        app: str,
        actor: str,
        role_name: str,
        confirm: str = "",
        payload: dict[str, object] | None = None,
    ) -> Job:
```

and pass it into the `Job(...)` construction as `payload=payload`.

In `_run`, replace the single `self._engine.run(job, emit)` call with a dispatch:

```python
        try:
            if job.verb is Verb.PUBLISH:
                result = self._run_publish(job, emit)
            else:
                result = self._engine.run(job, emit)
        except (EngineFailure, PublishError) as exc:
            self._finish(job, scope, JobState.FAILED, str(exc))
            return
```

and add the method:

```python
    def _run_publish(self, job: Job, emit: _Emit) -> dict[str, object] | None:
        """Publish is the one verb an engine cannot serve: it spans two.

        Rendering runs on the local engine and installing on the GitOps one,
        so the pipeline holds both. A console configured for neither says so
        rather than failing somewhere less obvious.
        """
        if self._publish is None:
            raise PublishError(
                "publish needs both a server checkout and the Deploy-of-Record; "
                "this console is configured for neither, so it runs on the box's "
                "Ops API"
            )
        payload = job.payload or {}
        request = PublishRequest(
            url=str(payload.get("url", "")),
            ref=str(payload.get("ref", "") or "main"),
            name=job.app,
            path=str(payload.get("path", "")),
            generate=payload.get("generate"),  # type: ignore[arg-type]
            replace=bool(payload.get("replace", False)),
        )
        return self._publish.run(request, job.actor, job.role, emit)
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
pytest tests/test_ops_service.py -v
```

Expected: all pass, including the pre-existing service tests.

- [ ] **Step 6: Run the full gate**

```bash
make check
```

- [ ] **Step 7: Commit**

```bash
git add src/vpath_platform_mgmt/ops/model.py src/vpath_platform_mgmt/ops/service.py tests/test_ops_service.py
git commit -m "feat: publish as a guarded verb spanning both engines"
```

---

### Task 6: The publish route and its wiring

**Files:**
- Modify: `src/vpath_platform_mgmt/api/routes_apps.py` (add `_register_publish`, extend `register`)
- Modify: `src/vpath_platform_mgmt/api/app.py` (pass nothing new — the pipeline reaches routes through `service`)
- Modify: `src/vpath_platform_mgmt/api/server.py:98-112` (`build_engine`), add `build_publish_pipeline`, extend the `OpsService(...)` construction in `main`
- Test: `tests/test_api_app_store.py`

**Interfaces:**
- Consumes: `OpsService.submit(..., payload=...)` (Task 5); `PublishPipeline` (Task 4); `app_preflight.require_publishable` (Task 1); `_place_registered_files` (Task 2).
- Produces:
  - `POST /api/apps/publish` accepting `{"url", "ref", "name", "path", "generate": {...} | null, "replace": bool}`, returning the job dict with status 202.
  - `build_publish_pipeline(env: Mapping[str, str]) -> PublishPipeline | None` in `server.py` — returns `None` unless both `VPATH_MGMT_SERVER_CHECKOUT` and the gitops settings are present.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api_app_store.py`:

```python
def test_publish_submits_a_job_and_returns_it(admin_client) -> None:
    response = admin_client.post(
        "/api/apps/publish",
        json={"url": "github.com/org/demo-app", "ref": "main", "name": "demo-app"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["verb"] == "publish"
    assert body["app"] == "demo-app"


def test_publish_refuses_a_non_admin(app_dev_client) -> None:
    response = app_dev_client.post(
        "/api/apps/publish",
        json={"url": "github.com/org/demo-app", "ref": "main", "name": "demo-app"},
    )

    assert response.status_code == 403


def test_publish_refuses_a_request_without_a_url(admin_client) -> None:
    response = admin_client.post(
        "/api/apps/publish", json={"ref": "main", "name": "demo-app"}
    )

    assert response.status_code == 400
    assert "url" in response.json()["detail"]


def test_publish_refuses_a_request_without_a_name(admin_client) -> None:
    response = admin_client.post(
        "/api/apps/publish", json={"url": "github.com/org/demo-app"}
    )

    assert response.status_code == 400
    assert "name" in response.json()["detail"]
```

Reuse whatever admin and non-admin client fixtures this module already defines; if it builds clients inline, follow that pattern instead of adding fixtures.

Also append to `tests/test_api_console.py` (or wherever `server.py` builders are tested):

```python
def test_no_publish_pipeline_without_a_checkout() -> None:
    from vpath_platform_mgmt.api.server import build_publish_pipeline

    assert build_publish_pipeline({"VPATH_MGMT_GITEA_URL": "https://gitea"}) is None


def test_no_publish_pipeline_without_the_deploy_record(tmp_path) -> None:
    from vpath_platform_mgmt.api.server import build_publish_pipeline

    assert build_publish_pipeline({"VPATH_MGMT_SERVER_CHECKOUT": str(tmp_path)}) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_api_app_store.py -v -k publish
```

Expected: 404 on the route, and `ImportError` for `build_publish_pipeline`.

- [ ] **Step 3: Add the route**

In `src/vpath_platform_mgmt/api/routes_apps.py`, add:

```python
def _publish_request(body: dict[str, object]) -> tuple[str, dict[str, object]]:
    """The app name and job payload, refusing a request that cannot be run."""
    missing = [key for key in ("url", "name") if not body.get(key)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"publish needs {' and '.join(missing)}",
        )
    return str(body["name"]), {
        "url": str(body["url"]),
        "ref": str(body.get("ref") or "main"),
        "path": str(body.get("path") or ""),
        "generate": body.get("generate"),
        "replace": bool(body.get("replace", False)),
    }


def _register_publish(app: FastAPI, identity: IdentityFn, service: OpsService) -> None:
    @app.post("/api/apps/publish", status_code=202)
    async def publish(request: Request) -> dict[str, object]:
        """Walk a repository from URL to running under ArgoCD (Admin)."""
        caller = identity(request)
        name, payload = _publish_request(await request.json())
        job = service.submit("publish", name, caller.actor, caller.role, payload=payload)
        return job.to_dict()
```

and call it from `register`:

```python
    _register_publish(app, identity, service)
```

RBAC is not re-checked here: `OpsService.submit` refuses a non-admin and audits the refusal, and the API already maps `RefusedError` to 403.

- [ ] **Step 4: Build the pipeline in `server.py`**

Add to `src/vpath_platform_mgmt/api/server.py`:

```python
def build_publish_pipeline(env: Mapping[str, str]) -> PublishPipeline | None:
    """The pipeline, or None when this console cannot serve publish.

    Publish spans both engines: rendering needs the checkout on this host and
    installing needs the Deploy-of-Record. A console with only one of them
    cannot do it, and says so at the verb rather than half way through.
    """
    checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
    if not checkout or not env.get("VPATH_MGMT_GITEA_URL", ""):
        return None
    return PublishPipeline(
        registry=AppRegistry(build_catalog_root(env)),
        materializer=SourceMaterializer(Path(checkout)),
        local_engine=LocalEngine(Path(checkout), extra_env=parse_engine_env(env)),
        gitops_engine=build_gitops_engine(env),
        probe=repo_probe.probe,
        materialise=repo_probe.materialise,
        download=repo_probe.download_tree,
        bundle=bundle,
        place=_place_registered_files,
        inspect=require_publishable,
        runtime_of=detect_runtime,
    )


def build_catalog_root(env: Mapping[str, str]) -> Path:
    """This repository's ``apps/`` folder, which the registry owns."""
    return Path(env.get("VPATH_MGMT_APPS_DIR", "") or (repo_root() / "apps"))
```

with these imports:

```python
from vpath_platform_mgmt.cli.app_cmds import _place_registered_files
from vpath_platform_mgmt.cli.bundle import bundle
from vpath_platform_mgmt.ops import repo_probe
from vpath_platform_mgmt.ops.app_preflight import require_publishable
from vpath_platform_mgmt.ops.app_registry import AppRegistry, detect_runtime
from vpath_platform_mgmt.ops.publish import PublishPipeline
```

If importing a private name from `cli.app_cmds` trips the linter, rename it to `place_registered_files` in `cli/app_cmds.py` and update Task 2's test import in the same commit.

In `main`, pass it through:

```python
    service = OpsService(
        engine,
        instance_name=resolve_instance_name(os.environ, engine.name),
        tunnel_config=build_tunnel_config(os.environ),
        publish=build_publish_pipeline(os.environ),
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
pytest tests/test_api_app_store.py tests/test_api_console.py -v
```

- [ ] **Step 6: Run the full gate**

```bash
make check
```

- [ ] **Step 7: Commit**

```bash
git add src/vpath_platform_mgmt/api/routes_apps.py src/vpath_platform_mgmt/api/server.py tests/test_api_app_store.py tests/test_api_console.py
git commit -m "feat: POST /api/apps/publish, wired only where both halves exist"
```

---

### Task 7: The tunnel reaches the box's Ops API

The publish job runs on the box. A workstation console must be able to post to it.

**Files:**
- Modify: `src/vpath_platform_mgmt/ops/tunnel.py:45-98` (`TunnelConfig`, `from_env`)
- Test: `tests/test_ops_tunnel.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `TunnelConfig(host, user, key, port=1085, ops_port: int = 0)`. When `ops_port` is non-zero, `argv()` includes `-L 127.0.0.1:<ops_port>:127.0.0.1:<ops_port>` immediately after the `-D` pair. `from_env` reads it from `VPATH_MGMT_TUNNEL_OPS_PORT`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ops_tunnel.py`:

```python
def test_argv_forwards_the_ops_api_port_when_one_is_configured() -> None:
    from vpath_platform_mgmt.ops.tunnel import TunnelConfig

    argv = TunnelConfig(host="box", user="ops", key="k", ops_port=8765).argv()

    assert "-L" in argv
    assert argv[argv.index("-L") + 1] == "127.0.0.1:8765:127.0.0.1:8765"


def test_argv_has_no_forward_when_no_ops_port_is_configured() -> None:
    from vpath_platform_mgmt.ops.tunnel import TunnelConfig

    assert "-L" not in TunnelConfig(host="box", user="ops", key="k").argv()


def test_from_env_reads_the_ops_port() -> None:
    from vpath_platform_mgmt.ops.tunnel import from_env

    config = from_env(
        {
            "VPATH_MGMT_SSH_HOST": "box",
            "VPATH_MGMT_SSH_USER": "ops",
            "VPATH_MGMT_SSH_KEY": "k",
            "VPATH_MGMT_TUNNEL_OPS_PORT": "8765",
        }
    )

    assert config.ops_port == 8765


def test_from_env_refuses_a_non_numeric_ops_port() -> None:
    from vpath_platform_mgmt.ops.tunnel import TunnelError, from_env

    with pytest.raises(TunnelError, match="VPATH_MGMT_TUNNEL_OPS_PORT"):
        from_env(
            {
                "VPATH_MGMT_SSH_HOST": "box",
                "VPATH_MGMT_SSH_USER": "ops",
                "VPATH_MGMT_SSH_KEY": "k",
                "VPATH_MGMT_TUNNEL_OPS_PORT": "eight",
            }
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_ops_tunnel.py -v -k ops_port
```

Expected: `TypeError: __init__() got an unexpected keyword argument 'ops_port'`.

- [ ] **Step 3: Extend the config**

In `src/vpath_platform_mgmt/ops/tunnel.py`, add the field:

```python
    ops_port: int = 0
```

and in `argv()`, insert after the `-D` pair:

```python
        forward = (
            ["-L", f"127.0.0.1:{self.ops_port}:127.0.0.1:{self.ops_port}"]
            if self.ops_port
            else []
        )
```

placing `*forward` into the returned list after `f"127.0.0.1:{self.port}"`.

In `from_env`, after the existing port parsing:

```python
    raw_ops = env.get("VPATH_MGMT_TUNNEL_OPS_PORT", "") or "0"
    if not raw_ops.isdigit():
        raise TunnelError(
            f"VPATH_MGMT_TUNNEL_OPS_PORT is not a port number: {raw_ops!r}"
        )
```

and pass `ops_port=int(raw_ops)` into the returned `TunnelConfig`.

The boundary this module defends is unchanged: the forwarded port comes from configuration, never from a request.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/test_ops_tunnel.py -v
```

- [ ] **Step 5: Document the new setting**

Add to `.env.console.example`, beside the other tunnel settings:

```bash
# Forward the box's Ops API so a workstation console can submit publish jobs
# to the engine that runs beside the checkout. Leave empty on the box itself.
VPATH_MGMT_TUNNEL_OPS_PORT=
```

- [ ] **Step 6: Run the full gate**

```bash
make check
```

- [ ] **Step 7: Commit**

```bash
git add src/vpath_platform_mgmt/ops/tunnel.py tests/test_ops_tunnel.py .env.console.example
git commit -m "feat: forward the box's Ops API port through the tunnel"
```

---

### Task 8: The console Add-app form

**Files:**
- Modify: `src/vpath_platform_mgmt/api/console.html`, `src/vpath_platform_mgmt/api/console.js`, `src/vpath_platform_mgmt/api/console.css`
- Test: `tests/test_api_console.py`

**Interfaces:**
- Consumes: `POST /api/apps/publish` (Task 6).
- Produces: no Python interface. The form posts the request body from Task 6 and hands the returned job id to the existing job panel.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_api_console.py`:

```python
def test_the_console_offers_an_add_app_form() -> None:
    from pathlib import Path

    html = (
        Path("src/vpath_platform_mgmt/api/console.html").read_text(encoding="utf-8")
    )

    assert 'id="add-app"' in html
    assert 'id="add-app-url"' in html
    assert 'id="add-app-name"' in html


def test_the_console_posts_to_the_publish_route() -> None:
    from pathlib import Path

    script = Path("src/vpath_platform_mgmt/api/console.js").read_text(encoding="utf-8")

    assert "/api/apps/publish" in script
```

Follow this module's existing style: if it asserts against a served response rather than the file on disk, do the same.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pytest tests/test_api_console.py -v -k add_app
```

Expected: FAIL — `'id="add-app"' in html` is False.

- [ ] **Step 3: Add the form**

In `console.html`, inside the applications section, add:

```html
<form id="add-app" class="add-app">
  <h3>Add an application</h3>
  <input id="add-app-url" name="url" placeholder="github.com/org/repo" required />
  <input id="add-app-ref" name="ref" placeholder="main" value="main" />
  <input id="add-app-path" name="path" placeholder="examples/my-app (blank = repo root)" />
  <input id="add-app-name" name="name" placeholder="app name" required />
  <details>
    <summary>The repository ships no vpath-app.yaml</summary>
    <input id="add-app-port" name="port" type="number" placeholder="port" />
    <input id="add-app-base-path" name="base_path" placeholder="/app" />
    <input id="add-app-title" name="title" placeholder="sidebar title" />
  </details>
  <button type="submit">Publish</button>
  <p id="add-app-error" class="error" hidden></p>
</form>
```

- [ ] **Step 4: Wire the submit**

In `console.js`, following the file's existing fetch and error-rendering conventions:

```javascript
async function publishApp(form) {
  const value = (id) => document.getElementById(id).value.trim();
  const port = Number(value("add-app-port"));
  const generate = port
    ? {
        name: value("add-app-name"),
        port,
        base_path: value("add-app-base-path"),
        title: value("add-app-title"),
      }
    : null;
  const response = await api("/api/apps/publish", {
    method: "POST",
    body: JSON.stringify({
      url: value("add-app-url"),
      ref: value("add-app-ref") || "main",
      path: value("add-app-path"),
      name: value("add-app-name"),
      generate,
    }),
  });
  return response;
}
```

Bind it to the form's submit event, render a failure into `#add-app-error`, and on success let the existing job poll pick the job up — do not add a second polling loop.

The generation fields are only sent when a port was given, because the registry refuses them for a repository that ships its own manifest.

- [ ] **Step 5: Style the form**

In `console.css`, add rules for `.add-app` matching the existing panel styles. No new colours or fonts.

- [ ] **Step 6: Run the tests to verify they pass**

```bash
pytest tests/test_api_console.py -v
```

- [ ] **Step 7: Verify in the browser**

Start the console with the simulated engine and confirm the form renders, that submitting without a URL is refused by the browser, and that a submit with a URL produces a job row. Publish itself will fail on a simulated console — that is correct, and the message should say the console is configured for neither half.

- [ ] **Step 8: Run the full gate**

```bash
make check
```

- [ ] **Step 9: Commit**

```bash
git add src/vpath_platform_mgmt/api/console.html src/vpath_platform_mgmt/api/console.js src/vpath_platform_mgmt/api/console.css tests/test_api_console.py
git commit -m "feat: add an application from the console in one action"
```

---

## Verification

After Task 8, the whole chain is exercised by `make check`. The specific guarantees a reviewer should confirm:

1. `pytest tests/test_ops_app_preflight.py::test_the_recorded_sdk_failure_is_refused` passes — the failure from `07_app_source_delivery.md` is now caught before anything reaches the box. Reverting `app_preflight.py` fails this test.
2. `pytest tests/test_ops_publish.py::test_preflight_refusal_stops_before_anything_is_written` passes — a refusal writes nothing.
3. `pytest tests/test_ops_publish.py::test_register_is_skipped_when_provenance_already_records_this_commit` passes — resume works and is keyed to the commit.
4. `pytest tests/test_ops_publish.py::test_the_subtree_named_by_path_is_what_is_sent` passes — a workspace repository ships the app, not its siblings.
5. `make check` reports coverage at or above 85%.
