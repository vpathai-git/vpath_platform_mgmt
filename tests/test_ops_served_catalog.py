"""Tests for reading the platform's own app catalog and comparing it."""

from __future__ import annotations

import httpx
import pytest

from vpath_platform_mgmt.ops.apps import AppEntry
from vpath_platform_mgmt.ops.served_catalog import (
    ServedCatalogError,
    ServedCatalogReader,
    ServedEntry,
    compare,
    parse,
)


def entry(name: str, title: str) -> AppEntry:
    return AppEntry(name=name, title=title, description="", base_path=f"/{name}")


def reader(handler: object, **kwargs: object) -> ServedCatalogReader:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    return ServedCatalogReader(
        "https://10.0.0.4:30600",
        client=httpx.Client(transport=transport),
        **kwargs,  # type: ignore[arg-type]
    )


CATALOG = [
    {"name": "vpath-explorer", "label": "Explorer Deployment Test"},
    {"name": "vpath-web", "label": "Web"},
]


def test_parse_refuses_a_shape_it_does_not_understand() -> None:
    """A silently-empty catalog would read as 'the platform offers nothing'."""
    assert parse(CATALOG)[0].name == "vpath-explorer"
    with pytest.raises(ServedCatalogError, match="not a JSON list"):
        parse({"apps": []})
    with pytest.raises(ServedCatalogError, match="not an object"):
        parse(["vpath-explorer"])
    with pytest.raises(ServedCatalogError, match="string name/label"):
        parse([{"name": "vpath-explorer"}])


def test_compare_only_judges_apps_present_in_both() -> None:
    """The two populations differ by design; only the overlap is drift."""
    state = compare(
        [entry("vpath-explorer", "Explorer Deployment Test"), entry("demo", "Demo")],
        parse(CATALOG),
    )
    assert state["served_total"] == 2
    assert state["shared"] == 1
    assert state["only_here"] == 1  # 'demo' is ours alone, not a fault
    assert state["only_on_platform"] == 1  # 'vpath-web' is theirs alone
    assert state["label_mismatches"] == []


def test_compare_reports_a_label_the_platform_shows_differently() -> None:
    """The exact drift that /api/version can never reveal."""
    state = compare([entry("vpath-explorer", "Explorer")], parse(CATALOG))
    assert state["label_mismatches"] == [
        {
            "name": "vpath-explorer",
            "here": "Explorer",
            "platform": "Explorer Deployment Test",
        }
    ]


def test_reader_fetches_the_catalog_and_caches_it() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json=CATALOG)

    clock = {"t": 100.0}
    served = reader(handler, now=lambda: clock["t"])
    assert [e.label for e in served.entries()] == ["Explorer Deployment Test", "Web"]
    served.entries()
    assert len(calls) == 1  # a page poll must not hammer the platform
    assert calls[0].endswith("/app-catalog.json")
    clock["t"] += 31.0
    served.entries()
    assert len(calls) == 2  # ...but the cache does expire


def test_an_unreachable_platform_raises_rather_than_reporting_empty() -> None:
    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    with pytest.raises(ServedCatalogError, match="did not answer"):
        reader(down).entries()

    with pytest.raises(ServedCatalogError, match="answered 503"):
        reader(lambda _: httpx.Response(503)).entries()


def test_served_entry_is_just_what_the_browser_gets() -> None:
    assert ServedEntry("vpath-web", "Web").label == "Web"
