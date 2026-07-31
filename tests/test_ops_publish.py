"""The five-stage walk from a repository URL to an app running under ArgoCD."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vpath_platform_mgmt.ops.app_registry import Generated, RegistryError
from vpath_platform_mgmt.ops.bundle import BundleError
from vpath_platform_mgmt.ops.model import Role, Verb
from vpath_platform_mgmt.ops.publish import (
    STAGES,
    PublishError,
    PublishPipeline,
    PublishRequest,
)
from vpath_platform_mgmt.ops.repo_fetch import FetchError
from vpath_platform_mgmt.ops.source import SourceError


class FakeRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.registered: list[str] = []
        self.paths: list[str] = []
        self.generated: list[object] = []
        self.replaced: list[bool] = []

    def entries(self) -> list[dict[str, object]]:
        found = []
        for folder in sorted(self.root.glob("*/vpath-source.yaml")):
            data = yaml.safe_load(folder.read_text(encoding="utf-8")) or {}
            found.append({"name": folder.parent.name, **data})
        return found

    def register(self, repo, ref, commit, tree, generate=None, replace=False, path=""):
        self.registered.append(f"{repo}@{commit}")
        self.paths.append(path)
        self.generated.append(generate)
        self.replaced.append(replace)
        target = self.root / "demo-app"
        target.mkdir(parents=True, exist_ok=True)
        (target / "vpath-app.yaml").write_text("kind: VpathApp\n", encoding="utf-8")
        (target / "vpath-source.yaml").write_text(
            yaml.safe_dump({"repo": repo, "ref": ref, "commit": commit, "path": path}),
            encoding="utf-8",
        )
        from vpath_platform_mgmt.ops.app_registry import Registration

        return Registration("demo-app", target, "upstream", commit)


class FakeMaterializer:
    """Stands in for the checkout, provenance file and all.

    The real checkout carries the registered ``vpath-source.yaml`` next to the
    manifest, which is what lets the send stage tell a re-publish from a
    collision, so this fake writes the same fields.
    """

    def __init__(self, root: Path, path: str = "") -> None:
        self.root = root
        self.path = path
        self.calls: list[str] = []
        self.replaced: list[bool] = []

    def target_for(self, app: str) -> Path:
        return self.root / app

    def materialize(self, app, archive_bytes, provenance, replace=False):
        self.calls.append(app)
        self.replaced.append(replace)
        target = self.target_for(app)
        target.mkdir(parents=True, exist_ok=True)
        (target / "vpath-source.yaml").write_text(
            yaml.safe_dump(
                {
                    "commit": provenance.commit,
                    "repo": provenance.repo,
                    "path": self.path,
                }
            ),
            encoding="utf-8",
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

    pipeline, parts = build(
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
    assert parts["registry"].paths == ["examples/demo-app"]


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


REPO_URL = "https://github.com/org/demo-app.git"


def registered(root: Path, name: str, repo: str, path: str = "") -> None:
    """Put an existing registration in place, as a previous publish would."""
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    (target / "vpath-app.yaml").write_text("kind: VpathApp\n", encoding="utf-8")
    (target / "vpath-source.yaml").write_text(
        yaml.safe_dump({"repo": repo, "ref": "main", "commit": "b" * 40, "path": path}),
        encoding="utf-8",
    )


def test_the_registry_and_the_send_stage_get_the_probes_normalised_path(
    tmp_path: Path,
) -> None:
    """A pasted '/examples/app' is accepted by the probe and cleaned there.

    ``Path(a) / '/b'`` discards ``a``, so the raw operator string dies at send
    -- after the registry has already written apps/<name>/ with it recorded.
    """
    packed: list[Path] = []

    def probe(url: str, ref: str, path: str = "") -> _Probed:
        return _Probed(url, ref, path.strip("/"))

    def download(slug: str, commit: str, into: Path) -> Path:
        root = Path(into) / "tree"
        (root / "examples" / "demo-app").mkdir(parents=True)
        return root

    pipeline, parts = build(
        tmp_path,
        probe=probe,
        download=download,
        bundle=lambda path: (packed.append(Path(path)), b"tar")[1],
    )
    asked = PublishRequest(
        url="github.com/org/repo",
        ref="main",
        name="demo-app",
        path="/examples/demo-app/",
    )

    pipeline.run(asked, "ops", Role.ADMIN, lambda step: None)

    assert parts["registry"].paths == ["examples/demo-app"]
    assert packed and packed[0].parent.name == "examples"


def test_a_generated_manifest_reaches_the_registry_with_a_resolved_runtime(
    tmp_path: Path,
) -> None:
    """Otherwise spec.build.runtime is '' and the generated app cannot build."""

    def probe(url: str, ref: str, path: str = "") -> _Probed:
        probed = _Probed(url, ref, path)
        probed.files = {"package.json": "{}"}
        return probed

    pipeline, parts = build(tmp_path, probe=probe, runtime_of=lambda tree_: "node")
    asked = PublishRequest(
        url="github.com/org/demo-app",
        ref="main",
        name="demo-app",
        generate=Generated(
            name="demo-app", port=8080, base_path="/demo-app", title="Demo"
        ),
    )

    pipeline.run(asked, "ops", Role.ADMIN, lambda step: None)

    assert parts["registry"].generated[0].runtime == "node"


def test_publishing_over_a_different_repositorys_app_is_refused(
    tmp_path: Path,
) -> None:
    """Add-app must not silently destroy a registration and its checkout."""
    pipeline, parts = build(tmp_path)
    registered(tmp_path / "apps", "demo-app", "https://github.com/org/other.git")

    with pytest.raises(PublishError) as failure:
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    message = str(failure.value)
    assert "demo-app" in message
    assert "org/other" in message
    assert "replace" in message
    assert parts["registry"].registered == []
    assert parts["materializer"].calls == []


def test_republishing_the_same_repository_at_a_new_commit_needs_no_replace(
    tmp_path: Path,
) -> None:
    """Resume is the whole reason replace exists here; it must still work."""
    pipeline, parts = build(tmp_path)
    registered(tmp_path / "apps", "demo-app", REPO_URL)

    result = pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    assert result["stages"]["register"] == "done"
    assert parts["registry"].replaced == [True]


def test_an_explicit_replace_publishes_over_a_foreign_registration(
    tmp_path: Path,
) -> None:
    pipeline, parts = build(tmp_path)
    registered(tmp_path / "apps", "demo-app", "https://github.com/org/other.git")
    asked = PublishRequest(
        url="github.com/org/demo-app", ref="main", name="demo-app", replace=True
    )

    pipeline.run(asked, "ops", Role.ADMIN, lambda step: None)

    assert parts["registry"].registered == [REPO_URL + "@" + "c" * 40]


def test_send_refuses_to_rmtree_a_checkout_it_did_not_put_there(
    tmp_path: Path,
) -> None:
    """materialize() rmtree's its target; a hand-edited app must survive."""
    pipeline, parts = build(tmp_path)
    foreign = tmp_path / "checkout" / "demo-app"
    foreign.mkdir(parents=True)
    (foreign / "vpath-source.yaml").write_text(
        yaml.safe_dump(
            {"repo": "https://github.com/org/other.git", "commit": "b" * 40}
        ),
        encoding="utf-8",
    )
    (foreign / "hand-edited.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(PublishError, match="send"):
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    assert (foreign / "hand-edited.txt").is_file()
    assert parts["materializer"].calls == []


def test_a_name_the_repository_disagrees_with_is_refused_before_preflight(
    tmp_path: Path,
) -> None:
    """Preflight computes every path from the requested name.

    Publishing 'vpath-knowledge-builder' as 'knowledge-builder' otherwise
    reports a foreign hash.dirs entry -- pointing at the manifest when the
    thing that is wrong is the form field.
    """
    inspected: list[str] = []

    def probe(url: str, ref: str, path: str = "") -> _Probed:
        probed = _Probed(url, ref, path)
        probed.files = {
            "vpath-app.yaml": "metadata:\n  name: vpath-knowledge-builder\n"
        }
        return probed

    pipeline, parts = build(
        tmp_path,
        probe=probe,
        inspect=lambda tree_, app, runtime: inspected.append(app),
    )
    asked = PublishRequest(
        url="github.com/org/repo", ref="main", name="knowledge-builder"
    )

    with pytest.raises(PublishError) as failure:
        pipeline.run(asked, "ops", Role.ADMIN, lambda step: None)

    assert "vpath-knowledge-builder" in str(failure.value)
    assert "knowledge-builder" in str(failure.value)
    assert inspected == []
    assert parts["registry"].registered == []


def raiser(error: Exception):
    """A collaborator that always refuses, whatever it is handed."""

    def raise_it(*args: object, **kwargs: object) -> object:
        raise error

    return raise_it


def test_a_download_failure_is_wrapped_as_a_send_refusal(tmp_path: Path) -> None:
    pipeline, _ = build(tmp_path, download=raiser(FetchError("gh: 404")))

    with pytest.raises(PublishError, match="send: gh: 404"):
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)


def test_a_bundle_failure_is_wrapped_as_a_send_refusal(tmp_path: Path) -> None:
    """BundleError was absent from the except tuple, so it escaped the walk."""
    pipeline, _ = build(tmp_path, bundle=raiser(BundleError("has no vpath-app.yaml")))

    with pytest.raises(PublishError, match="send: has no vpath-app.yaml"):
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)


def test_a_materializer_refusal_is_wrapped_as_a_send_refusal(tmp_path: Path) -> None:
    class Refusing(FakeMaterializer):
        def materialize(self, app, archive_bytes, provenance, replace=False):
            raise SourceError("upload has no vpath-app.yaml at its root")

    pipeline, _ = build(tmp_path, materializer=Refusing(tmp_path / "checkout"))

    with pytest.raises(PublishError, match="send: upload has no"):
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)


def test_a_target_outside_the_checkout_is_wrapped_as_a_send_refusal(
    tmp_path: Path,
) -> None:
    """target_for() sat outside the try, so its refusal escaped untyped."""

    class Refusing(FakeMaterializer):
        def target_for(self, app: str) -> Path:
            raise SourceError("invalid app name " + app)

    pipeline, _ = build(tmp_path, materializer=Refusing(tmp_path / "checkout"))

    with pytest.raises(PublishError, match="send: invalid app name"):
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)


def test_a_registry_refusal_is_wrapped_as_a_register_refusal(tmp_path: Path) -> None:
    class Refusing(FakeRegistry):
        def register(self, **kwargs: object) -> object:
            raise RegistryError("port 8080 is already used by 'other'")

    pipeline, _ = build(tmp_path, registry=Refusing(tmp_path / "apps"))

    with pytest.raises(PublishError, match="register: port 8080"):
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)


def test_an_install_failure_names_its_stage(tmp_path: Path) -> None:
    pipeline, _ = build(
        tmp_path, gitops_engine=FakeEngine("gitops", fails="argo never converged")
    )

    with pytest.raises(PublishError) as failure:
        pipeline.run(request(), "ops", Role.ADMIN, lambda step: None)

    assert "install" in str(failure.value)
    assert "argo never converged" in str(failure.value)
