"""Fail-hard tests (CLAUDE.md §7): the real router + TestClient, auth
overridden — never a soft pass.

Proof of concept story K01 (story-test twin, R-E): the domain api round-trip —
POST /api/draw returns the deterministic card the deck maps the question to.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fortune.deck import draw_fortune  # noqa: E402
from fortune.routes import router  # noqa: E402
from vpath_backend_sdk import require_auth  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[require_auth] = lambda: object()
    return TestClient(app)


def test_draw_returns_the_deterministic_card_for_a_question():
    """K01: the same question always draws the same real card."""
    question = "Will the gate stay green?"
    card = draw_fortune(question)
    resp = _client().post("/api/draw", json={"question": question})
    assert resp.status_code == 200
    assert resp.json() == {"fortune": card.fortune, "sign": card.sign}


def test_empty_question_is_a_real_deterministic_draw():
    """K01: the ask-nothing first-time state is a real card, never a
    placeholder."""
    card = draw_fortune("")
    resp = _client().post("/api/draw", json={})
    assert resp.status_code == 200
    assert resp.json() == {"fortune": card.fortune, "sign": card.sign}
