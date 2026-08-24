"""The publish walk against the real registry, materializer and preflight.

Every other publish test doubles all eleven collaborators, which proves the
sequencing and nothing about the seams between the units. This one wires the
real ones together and walks them end to end: only the two calls that would
need a network (``probe`` and ``download``) are stubbed, and the two engine
stages run on ``SimulatedEngine``. Every Critical found in the final review
was a seam defect a test at this level would have caught.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from vpath_platform_mgmt.cli.app_cmds import _place_registered_files
from vpath_platform_mgmt.ops.app_preflight import require_publishable
from vpath_platform_mgmt.ops.app_registry import (
    AppRegistry,
    Generated,
    detect_runtime,
)
from vpath_platform_mgmt.ops.bundle import bundle
from vpath_platform_mgmt.ops.engine import SimulatedEngine
from vpath_platform_mgmt.ops.model import Role
from vpath_platform_mgmt.ops.publish import PublishError, PublishPipeline
from vpath_platform_mgmt.ops.publish_stages import PublishRequest
from vpath_platform_mgmt.ops.repo_probe import Probed, materialise
from vpath_platform_mgmt.ops.source import SourceMaterializer
from vpath_platform_mgmt.ops.tree_hash import git_tree_sha

APP = "vpath-demo-app"
COMMIT = "a" * 40
NEXT_COMMIT = "b" * 40
SLUG = "org/demo-app"
PACKAGE = json.dumps({"name": APP, "scripts": {"build": "next build"}})


def manifest_text(app: str) -> str:
    """A manifest the preflight gate passes and the catalog can read."""
    return yaml.safe_dump(
        {
            "apiVersion": "vpath/v1",
            "kind": "VpathApp",
            "metadata": {"name": app, "namespace": app},
            "spec": {
                "type": "web",
                "basePath": f"/{app}",
                "port": 8080,
                "ui": {"title": "Demo", "sidebar": True},
                "build": {
                    "runtime": "node",
                    "hash": {"dirs": [f"apps_infra/apps/{app}"]},
                },
            },
        },
        sort_keys=False,
    )


def repository(tmp_path: Path, files: dict[str, str]) -> Path:
    """The app repository as the tarball download would leave it on disk."""
    root = tmp_path / "downloaded"
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "index.ts").write_text("export {}\n", encoding="utf-8")
    return root


def pipeline_for(
    tmp_path: Path,
    files: dict[str, str],
    commit: str = COMMIT,
    slug: str = SLUG,
) -> tuple[PublishPipeline, Path, Path]:
    """The real units, wired as ``build_publish_pipeline`` wires them."""
    apps = tmp_path / "apps"
    apps.mkdir(exist_ok=True)
    checkout = tmp_path / "checkout"
    (checkout / "apps_infra" / "apps").mkdir(parents=True, exist_ok=True)
    tree = repository(tmp_path, files)

    def probe(url: str, ref: str, path: str = "") -> Probed:
        return Probed(slug=slug, ref=ref, commit=commit, files=files, path=path)

    def download(slug: str, sha: str, into: Path) -> Path:
        return tree

    return (
        PublishPipeline(
            registry=AppRegistry(apps),
            materializer=SourceMaterializer(checkout),
            local_engine=SimulatedEngine(step_delay=0.0),
            gitops_engine=SimulatedEngine(step_delay=0.0),
            probe=probe,
            materialise=materialise,
            download=download,
            bundle=bundle,
            place=lambda name, payload: _place_registered_files(name, payload, apps),
            inspect=require_publishable,
            runtime_of=detect_runtime,
        ),
        apps,
        checkout / "apps_infra" / "apps",
    )


def asked(**overrides: object) -> PublishRequest:
    fields: dict[str, object] = {
        "url": f"github.com/{SLUG}",
        "ref": "main",
        "name": APP,
    }
    fields.update(overrides)
    return PublishRequest(**fields)  # type: ignore[arg-type]


def test_a_repository_that_ships_a_manifest_walks_to_a_populated_checkout(
    tmp_path: Path,
) -> None:
    pipeline, apps, materialized = pipeline_for(
        tmp_path, {"vpath-app.yaml": manifest_text(APP), "package.json": PACKAGE}
    )

    result = pipeline.run(asked(), "ops", Role.ADMIN, lambda step: None)

    assert result["stages"] == {
        "preflight": "done",
        "register": "done",
        "send": "done",
        "render": "done",
        "install": "done",
    }
    registered = yaml.safe_load(
        (apps / APP / "vpath-source.yaml").read_text(encoding="utf-8")
    )
    assert registered["commit"] == COMMIT
    assert registered["manifest_origin"] == "upstream"
    assert registered["tree_sha"] == git_tree_sha(
        repository(
            tmp_path / "hash",
            {"vpath-app.yaml": manifest_text(APP), "package.json": PACKAGE},
        )
    )
    assert (materialized / APP / "vpath-app.yaml").is_file()
    assert (materialized / APP / "vpath-source.yaml").is_file()
    assert (materialized / APP / "src" / "index.ts").is_file()


def test_a_repository_without_a_manifest_gets_one_that_names_its_runtime(
    tmp_path: Path,
) -> None:
    """Via the API nothing resolves the runtime, so it used to be written ''."""
    pipeline, apps, materialized = pipeline_for(tmp_path, {"package.json": PACKAGE})

    pipeline.run(
        asked(
            generate=Generated(
                name=APP, port=8081, base_path=f"/{APP}", title="Demo App"
            )
        ),
        "ops",
        Role.ADMIN,
        lambda step: None,
    )

    written = yaml.safe_load(
        (apps / APP / "vpath-app.yaml").read_text(encoding="utf-8")
    )
    assert written["spec"]["build"]["runtime"] == "node"
    assert written["spec"]["port"] == 8081
    assert (materialized / APP / "vpath-app.yaml").is_file()


def test_a_second_walk_at_the_same_commit_skips_what_already_happened(
    tmp_path: Path,
) -> None:
    pipeline, _, _ = pipeline_for(
        tmp_path, {"vpath-app.yaml": manifest_text(APP), "package.json": PACKAGE}
    )
    pipeline.run(asked(), "ops", Role.ADMIN, lambda step: None)

    result = pipeline.run(asked(), "ops", Role.ADMIN, lambda step: None)

    assert result["stages"]["register"] == "skipped"
    assert result["stages"]["send"] == "skipped"
    assert result["stages"]["render"] == "done"
    assert result["stages"]["install"] == "done"


def test_the_recorded_sdk_failure_never_reaches_the_registry(
    tmp_path: Path,
) -> None:
    """The port failure in 07_app_source_delivery.md, caught at stage 0."""
    escaping = json.dumps(
        {
            "name": APP,
            "scripts": {"build": "next build"},
            "dependencies": {"@vpath/sdk": "file:../../kit/sdk"},
        }
    )
    manifest = yaml.safe_load(manifest_text(APP))
    manifest["spec"]["build"]["sdks"] = [
        {"name": "@vpath/sdk", "source": "apps_infra/sdk"}
    ]
    manifest["spec"]["build"]["hash"]["dirs"].append("apps_infra/sdk")
    pipeline, apps, materialized = pipeline_for(
        tmp_path,
        {
            "vpath-app.yaml": yaml.safe_dump(manifest, sort_keys=False),
            "package.json": escaping,
        },
    )

    with pytest.raises(PublishError) as failure:
        pipeline.run(asked(), "ops", Role.ADMIN, lambda step: None)

    assert "file:../../sdk" in str(failure.value)
    assert not (apps / APP).exists()
    assert not (materialized / APP).exists()


def test_publishing_a_second_repository_under_a_taken_name_is_refused(
    tmp_path: Path,
) -> None:
    """The registry's own guard, reachable through the orchestrator again."""
    files = {"vpath-app.yaml": manifest_text(APP), "package.json": PACKAGE}
    pipeline, apps, materialized = pipeline_for(tmp_path, files)
    pipeline.run(asked(), "ops", Role.ADMIN, lambda step: None)
    keepsake = materialized / APP / "src" / "index.ts"
    assert keepsake.is_file()

    other, _, _ = pipeline_for(
        tmp_path, files, commit=NEXT_COMMIT, slug="org/somebody-else"
    )
    with pytest.raises(PublishError, match="replace"):
        other.run(
            asked(url="github.com/org/somebody-else"),
            "ops",
            Role.ADMIN,
            lambda step: None,
        )

    assert keepsake.is_file()
