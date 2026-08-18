"""Feature checks for Explorer THROWAWAY extract + deploy runbook."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_explorer_readme_is_throwaway() -> None:
    readme = (ROOT / "apps/vpath-explorer/README.md").read_text(encoding="utf-8")
    assert "THROWAWAY" in readme
    assert "Arsany" in readme
    assert "explorer-deploy-demo.notes.md" in readme


def test_explorer_deploy_runbook_exists() -> None:
    notes = ROOT / "analysis/mgmt-console/explorer-deploy-demo.notes.md"
    text = notes.read_text(encoding="utf-8")
    assert "server" in text.lower()
    assert "healthz" in text
    assert "vpath-explorer" in text


def test_explorer_manifest_and_health_route_exist() -> None:
    assert (ROOT / "apps/vpath-explorer/vpath-app.yaml").is_file()
    assert (ROOT / "apps/vpath-explorer/src/app/api/healthz/route.ts").is_file()


def test_explorer_manifest_title_matches_platform_label() -> None:
    text = (ROOT / "apps/vpath-explorer/vpath-app.yaml").read_text(encoding="utf-8")
    assert "title: Explorer" in text
    assert "Explorer Deployment Test" not in text


def test_explorer_runbook_records_vm5_live_status() -> None:
    text = (ROOT / "analysis/mgmt-console/explorer-deploy-demo.notes.md").read_text(
        encoding="utf-8"
    )
    assert "vm5" in text
    assert "terra" in text
    assert "healthz" in text
