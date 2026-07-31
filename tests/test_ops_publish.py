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

    def register(self, repo, ref, commit, tree, generate=None, replace=False, path=""):
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
    pipeline, _ = build(
        tmp_path, local_engine=FakeEngine("local", fails="gradle blew up")
    )

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
