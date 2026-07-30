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

Task 3 calls `require_publishable` only.

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


def manifest(app: str, dirs: list[str]) -> str:
    return yaml.safe_dump(
        {
            "apiVersion": "vpath/v1",
            "kind": "VpathApp",
            "metadata": {"name": app},
            "spec": {"build": {"runtime": "node", "hash": {"dirs": dirs}}},
        },
        sort_keys=False,
    )


def good_node_tree(tmp_path: Path, app: str = "demo-app") -> Path:
    write(
        tmp_path,
        "package.json",
        json.dumps({"name": app, "scripts": {"build": "next build"}}),
    )
    write(tmp_path, "vpath-app.yaml", manifest(app, [f"apps_infra/apps/{app}"]))
    return tmp_path


def test_a_self_contained_node_repo_has_no_findings(tmp_path: Path) -> None:
    assert inspect(good_node_tree(tmp_path), "demo-app", "node") == []


def test_a_dependency_escaping_the_app_tree_is_a_finding(tmp_path: Path) -> None:
    tree = good_node_tree(tmp_path)
    write(
        tree,
        "package.json",
        json.dumps(
            {
                "name": "demo-app",
                "scripts": {"build": "next build"},
                "dependencies": {"@vpath/sdk": "file:../../kit/sdk"},
            }
        ),
    )
    findings = inspect(tree, "demo-app", "node")
    assert [f.file for f in findings] == ["package.json"]
    assert "file:../../kit/sdk" in findings[0].value


def test_a_file_dependency_inside_the_app_tree_is_allowed(tmp_path: Path) -> None:
    tree = good_node_tree(tmp_path)
    write(
        tree,
        "package.json",
        json.dumps(
            {
                "name": "demo-app",
                "scripts": {"build": "next build"},
                "dependencies": {"@demo/ui": "file:./packages/ui"},
            }
        ),
    )
    assert inspect(tree, "demo-app", "node") == []


def test_a_python_path_dependency_escaping_the_tree_is_a_finding(
    tmp_path: Path,
) -> None:
    write(tmp_path, "pyproject.toml", '[project]\nname = "demo-app"\n')
    write(
        tmp_path,
        "vpath-app.yaml",
        manifest("demo-app", ["apps_infra/apps/demo-app"]),
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo-app"\n\n'
        "[tool.poetry.dependencies]\n"
        'vpath-sdk = { path = "../../kit/sdk" }\n',
        encoding="utf-8",
    )
    findings = inspect(tmp_path, "demo-app", "python")
    assert [f.file for f in findings] == ["pyproject.toml"]


def test_hash_dirs_naming_another_app_is_a_finding(tmp_path: Path) -> None:
    tree = good_node_tree(tmp_path)
    write(tree, "vpath-app.yaml", manifest("demo-app", ["apps_infra/apps/other-app"]))
    findings = inspect(tree, "demo-app", "node")
    assert [f.file for f in findings] == ["vpath-app.yaml"]
    assert "other-app" in findings[0].value


def test_hash_dirs_outside_the_apps_root_is_a_finding(tmp_path: Path) -> None:
    tree = good_node_tree(tmp_path)
    write(tree, "vpath-app.yaml", manifest("demo-app", ["apps_infra/sdk"]))
    assert len(inspect(tree, "demo-app", "node")) == 1


def test_a_node_repo_without_a_build_script_is_a_finding(tmp_path: Path) -> None:
    tree = good_node_tree(tmp_path)
    write(tree, "package.json", json.dumps({"name": "demo-app"}))
    findings = inspect(tree, "demo-app", "node")
    assert [f.file for f in findings] == ["package.json"]
    assert "scripts.build" in findings[0].remedy


def test_a_node_repo_without_a_package_json_is_a_finding(tmp_path: Path) -> None:
    write(tmp_path, "vpath-app.yaml", manifest("demo-app", ["apps_infra/apps/demo-app"]))
    assert len(inspect(tmp_path, "demo-app", "node")) == 1


def test_require_publishable_passes_a_clean_tree(tmp_path: Path) -> None:
    require_publishable(good_node_tree(tmp_path), "demo-app", "node")


def test_require_publishable_reports_every_finding_at_once(tmp_path: Path) -> None:
    tree = good_node_tree(tmp_path)
    write(
        tree,
        "package.json",
        json.dumps({"dependencies": {"@vpath/sdk": "file:../../kit/sdk"}}),
    )
    write(tree, "vpath-app.yaml", manifest("demo-app", ["apps_infra/apps/other-app"]))
    with pytest.raises(PreflightError) as failure:
        require_publishable(tree, "demo-app", "node")
    message = str(failure.value)
    assert "package.json" in message
    assert "vpath-app.yaml" in message
    assert "scripts.build" in message


def test_the_recorded_sdk_failure_is_refused(tmp_path: Path) -> None:
    """Regression guard for the port failure in 07_app_source_delivery.md.

    Source materialized cleanly and the image build then died on
    'Can't resolve @vpath/sdk'. Publishing must refuse before anything is
    written to the box.
    """
    write(
        tmp_path,
        "package.json",
        json.dumps(
            {
                "name": "vpath-explorer",
                "scripts": {"build": "next build"},
                "dependencies": {"@vpath/sdk": "file:../../kit/sdk"},
            }
        ),
    )
    write(
        tmp_path,
        "vpath-app.yaml",
        manifest("vpath-explorer", ["apps_infra/apps/vpath-explorer"]),
    )
    with pytest.raises(PreflightError, match="kit/sdk"):
        require_publishable(tmp_path, "vpath-explorer", "node")
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

This module only looks. It writes nothing, reaches nothing, and every check
answers one question: would this tree still make sense once it sits at
``apps_infra/apps/<name>/``?
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

APPS_ROOT = "apps_infra/apps"
MANIFEST = "vpath-app.yaml"
NODE_MANIFEST = "package.json"
PYTHON_MANIFEST = "pyproject.toml"
DEPENDENCY_KEYS = ("dependencies", "devDependencies", "optionalDependencies")

# ponytail: pyproject is scanned line-wise for escaping path dependencies
# rather than parsed, because tomllib is 3.11+ and this project's floor is
# 3.10; adding a TOML parser for one check is not worth a dependency.
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


def _load_json(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{path.name} is not readable JSON: {exc}") from exc
    return parsed if isinstance(parsed, dict) else {}


def _escapes(value: str) -> bool:
    """Whether a relative path leaves the app's own directory."""
    return Path(value).as_posix().startswith("..") or value.startswith("/")


def escaping_node_deps(tree: Path) -> list[Finding]:
    """``file:`` dependencies pointing outside the app's own tree."""
    manifest = tree / NODE_MANIFEST
    if not manifest.is_file():
        return []
    parsed = _load_json(manifest)
    found: list[Finding] = []
    for key in DEPENDENCY_KEYS:
        block = parsed.get(key)
        if not isinstance(block, dict):
            continue
        for name, spec in block.items():
            if not isinstance(spec, str) or not spec.startswith("file:"):
                continue
            if _escapes(spec.removeprefix("file:")):
                found.append(
                    Finding(
                        NODE_MANIFEST,
                        f"{name} = {spec}",
                        "the server builds this app from apps_infra/apps/<name>, "
                        "so a dependency outside that directory cannot resolve; "
                        "vendor it or publish it to the registry",
                    )
                )
    return found


def escaping_python_deps(tree: Path) -> list[Finding]:
    """``path = "..."`` dependencies pointing outside the app's own tree."""
    manifest = tree / PYTHON_MANIFEST
    if not manifest.is_file():
        return []
    found: list[Finding] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = PATH_DEPENDENCY.search(line)
        if match is not None and _escapes(match.group(1)):
            found.append(
                Finding(
                    PYTHON_MANIFEST,
                    line.strip(),
                    "the server builds this app from apps_infra/apps/<name>, "
                    "so a path dependency outside that directory cannot "
                    "resolve; vendor it or publish it to an index",
                )
            )
    return found


def foreign_hash_dirs(tree: Path, app: str) -> list[Finding]:
    """``spec.build.hash.dirs`` entries that are not this app's directory."""
    manifest = tree / MANIFEST
    if not manifest.is_file():
        return []
    parsed = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    spec = parsed.get("spec") if isinstance(parsed, dict) else None
    build = spec.get("build") if isinstance(spec, dict) else None
    hashed = build.get("hash") if isinstance(build, dict) else None
    dirs = hashed.get("dirs") if isinstance(hashed, dict) else None
    if not isinstance(dirs, list):
        return []
    expected = f"{APPS_ROOT}/{app}"
    return [
        Finding(
            MANIFEST,
            f"spec.build.hash.dirs: {entry}",
            f"the content hash must cover this app only — expected {expected}",
        )
        for entry in dirs
        if str(entry).rstrip("/") != expected
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
        *escaping_node_deps(root),
        *escaping_python_deps(root),
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

Expected: 11 passed.

- [ ] **Step 5: Run the full gate**

```bash
make check
```

Expected: all steps pass, coverage at or above 85%.

- [ ] **Step 6: Commit**

```bash
git add src/vpath_platform_mgmt/ops/app_preflight.py tests/test_ops_app_preflight.py
git commit -m "feat: refuse a repo whose dependencies escape its own tree"
```

---

### Task 2: Provenance travels into the checkout

The send stage must be able to answer "sent at which commit" from the box alone, without asking this repository. Today `_place_manifest` copies only the manifest into the payload.

**Files:**
- Modify: `src/vpath_platform_mgmt/cli/app_cmds.py:251-262` (`_place_manifest`)
- Test: `tests/test_cli_app_send.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_place_registered_files(name: str, tree: Path, apps: Path) -> None` replacing `_place_manifest`. Copies both `vpath-app.yaml` and `vpath-source.yaml` from `apps/<name>/` into the payload root. Task 3 relies on `vpath-source.yaml` being present at `<checkout>/apps_infra/apps/<name>/vpath-source.yaml`.

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

### Task 3: The publish pipeline

**Files:**
- Create: `src/vpath_platform_mgmt/ops/publish.py`
- Test: `tests/test_ops_publish.py`

**Interfaces:**
- Consumes: `app_preflight.require_publishable` (Task 1); `AppRegistry.register/refresh/entries` and `Generated` (existing); `SourceMaterializer.materialize/target_for` (existing); `LocalEngine.run` and `GitOpsEngine.run` (existing); `repo_probe.probe/materialise/download_tree` (existing).
- Produces:
  - `PublishRequest(url: str, ref: str, name: str, generate: Generated | None = None, replace: bool = False)` — frozen dataclass.
  - `PublishError(Exception)`
  - `STAGES: tuple[str, ...] = ("preflight", "register", "send", "render", "install")`
  - `PublishPipeline.run(request: PublishRequest, actor: str, role: Role, emit: StepEmitter) -> dict[str, object]` returning `{"app": str, "commit": str, "stages": {name: "done" | "skipped"}}`.

Task 4 calls `run` only.

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
        "probe": lambda url, ref: _Probed(url, ref),
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
    def __init__(self, url: str, ref: str) -> None:
        self.slug = "org/demo-app"
        self.ref = ref
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
            return self._probe(request.url, request.ref)
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
            payload = self._download(probed.slug, probed.commit, workspace)
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

Expected: 7 passed. If `PublishPipeline.__init__` exceeds the complexity limit, that is expected to pass — it is assignment only.

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

### Task 4: The publish verb and its guardrails

**Files:**
- Modify: `src/vpath_platform_mgmt/ops/model.py:22-58` (`Verb`, `VERB_ROLE`, `lock_scope`), `src/vpath_platform_mgmt/ops/model.py:70-102` (`Job`)
- Modify: `src/vpath_platform_mgmt/ops/service.py:44-137` (`OpsService.__init__`, `submit`, `_run`)
- Test: `tests/test_ops_service.py`

**Interfaces:**
- Consumes: `PublishPipeline.run(request, actor, role, emit)` and `PublishRequest` (Task 3).
- Produces:
  - `Verb.PUBLISH = "publish"`, `VERB_ROLE[Verb.PUBLISH] = Role.ADMIN`, `lock_scope(Verb.PUBLISH, app) == f"app:{app}"`.
  - `Job.payload: dict[str, object] | None = None`, included in `to_dict()`.
  - `OpsService.__init__(..., publish: PublishPipeline | None = None)`.
  - `OpsService.submit(verb_name, app, actor, role_name, confirm="", payload=None) -> Job`.

Task 5 calls `submit("publish", name, actor, role, payload={...})`.

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

### Task 5: The publish route and its wiring

**Files:**
- Modify: `src/vpath_platform_mgmt/api/routes_apps.py` (add `_register_publish`, extend `register`)
- Modify: `src/vpath_platform_mgmt/api/app.py` (pass nothing new — the pipeline reaches routes through `service`)
- Modify: `src/vpath_platform_mgmt/api/server.py:98-112` (`build_engine`), add `build_publish_pipeline`, extend the `OpsService(...)` construction in `main`
- Test: `tests/test_api_app_store.py`

**Interfaces:**
- Consumes: `OpsService.submit(..., payload=...)` (Task 4); `PublishPipeline` (Task 3); `app_preflight.require_publishable` (Task 1); `_place_registered_files` (Task 2).
- Produces:
  - `POST /api/apps/publish` accepting `{"url", "ref", "name", "generate": {...} | null, "replace": bool}`, returning the job dict with status 202.
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

### Task 6: The tunnel reaches the box's Ops API

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

### Task 7: The console Add-app form

**Files:**
- Modify: `src/vpath_platform_mgmt/api/console.html`, `src/vpath_platform_mgmt/api/console.js`, `src/vpath_platform_mgmt/api/console.css`
- Test: `tests/test_api_console.py`

**Interfaces:**
- Consumes: `POST /api/apps/publish` (Task 5).
- Produces: no Python interface. The form posts the request body from Task 5 and hands the returned job id to the existing job panel.

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

After Task 7, the whole chain is exercised by `make check`. The specific guarantees a reviewer should confirm:

1. `pytest tests/test_ops_app_preflight.py::test_the_recorded_sdk_failure_is_refused` passes — the failure from `07_app_source_delivery.md` is now caught before anything reaches the box. Reverting `app_preflight.py` fails this test.
2. `pytest tests/test_ops_publish.py::test_preflight_refusal_stops_before_anything_is_written` passes — a refusal writes nothing.
3. `pytest tests/test_ops_publish.py::test_register_is_skipped_when_provenance_already_records_this_commit` passes — resume works and is keyed to the commit.
4. `make check` reports coverage at or above 85%.
