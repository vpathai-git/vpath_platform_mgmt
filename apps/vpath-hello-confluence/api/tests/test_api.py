"""Fail-hard tests (CLAUDE.md §7): real client + routes, HTTP boundary mocked
(httpx MockTransport) — never a fake Confluence service, never a soft pass."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from confluence import ConfluenceClient, ConfluenceError  # noqa: E402
from confluence import credential as cred  # noqa: E402
from confluence.routes import router  # noqa: E402
from vpath_backend_sdk import require_auth  # noqa: E402

ORIGIN = "https://x.atlassian.net"


# -- client: real pagination + dedup + tree, mocked transport --------------
def _spaces_handler(request: httpx.Request) -> httpx.Response:
    cursor = request.url.params.get("cursor")
    if (
        not cursor
    ):  # page 1 → 2 spaces + a next link (cursor overlaps page 2 on purpose)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"id": "1", "key": "B", "name": "Beta", "type": "global"},
                    {"id": "2", "key": "A", "name": "alpha", "type": "global"},
                ],
                "_links": {"next": "/wiki/api/v2/spaces?cursor=c2"},
            },
        )
    return httpx.Response(
        200,
        json={  # page 2 → repeats id 2 (overlap) + new id 3, no next
            "results": [
                {"id": "2", "key": "A", "name": "alpha", "type": "global"},
                {"id": "3", "key": "C", "name": "Gamma", "type": "global"},
            ],
            "_links": {},
        },
    )


def _client(handler) -> ConfluenceClient:
    return ConfluenceClient(
        ORIGIN, "e:t", http=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_list_spaces_paginates_dedups_and_sorts():
    spaces = _client(_spaces_handler).list_spaces()
    assert [s.key for s in spaces] == [
        "A",
        "B",
        "C",
    ]  # sorted by name, id 2 not duplicated
    assert len(spaces) == 3


def test_non_2xx_raises_confluence_error():
    def boom(_):
        return httpx.Response(401, json={"message": "nope"})

    with pytest.raises(ConfluenceError) as ei:
        _client(boom).list_spaces()
    assert ei.value.status == 401


def test_pagination_hard_cap_fails_loud():
    def always_next(_):
        return httpx.Response(
            200,
            json={
                "results": [{"id": "1", "title": "t"}],
                "_links": {"next": "/wiki/api/v2/pages/1/children?cursor=x"},
            },
        )

    with pytest.raises(ConfluenceError):
        _client(always_next).page_children("1")  # must raise, never loop forever


def test_token_pair_required():
    with pytest.raises(ConfluenceError):
        ConfluenceClient(ORIGIN, "no-colon-here")


# -- routes: not-bound + dispatch, auth dependency overridden --------------
@pytest.fixture()
def app() -> FastAPI:
    a = FastAPI()
    a.include_router(router)
    a.dependency_overrides[require_auth] = (
        lambda: object()
    )  # bypass platform authN in unit test
    return a


def test_spaces_not_bound_returns_422(app):
    r = TestClient(app).get("/spaces")  # no credential headers injected
    assert r.status_code == 422
    assert r.json()["error"] == "resource_not_bound"


def test_resource_status_reflects_headers(app):
    c = TestClient(app)
    assert c.get("/resource/status").json()["bound"] is False
    h = {cred.URL_HEADER: ORIGIN, cred.TOKEN_HEADER: "e:t"}
    assert c.get("/resource/status", headers=h).json()["bound"] is True


def test_spaces_bound_dispatch(app, monkeypatch):
    monkeypatch.setattr(
        "confluence.routes.client_for", lambda req: _client(_spaces_handler)
    )
    r = TestClient(app).get(
        "/spaces", headers={cred.URL_HEADER: ORIGIN, cred.TOKEN_HEADER: "e:t"}
    )
    assert r.status_code == 200
    assert {s["key"] for s in r.json()["spaces"]} == {"A", "B", "C"}


def test_spaces_upstream_error_maps_502(app, monkeypatch):
    class Boom:
        def list_spaces(self):
            raise ConfluenceError(503, "down")

        def close(self): ...

    monkeypatch.setattr("confluence.routes.client_for", lambda req: Boom())
    r = TestClient(app).get(
        "/spaces", headers={cred.URL_HEADER: ORIGIN, cred.TOKEN_HEADER: "e:t"}
    )
    assert r.status_code == 502
    assert r.json()["error"] == "confluence_error"
