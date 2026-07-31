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
