"""Domain API for the Fortune Teller — the only thing this app writes.

Auth: each route depends on `require_auth` (the platform verifies identity).
This app binds NO external system (CLAUDE.md §1 — declare only what you need),
so there is no credential/connector handling here. The draw is fully local and
DETERMINISTIC (CLAUDE.md §7 — no randomness that breaks reproducibility): the
same question always yields the same fortune.

Bad input fails LOUD: the request model rejects an over-long / wrong-typed
question with a 422 (FastAPI validation) — never a silent default. A draw is
ALWAYS a real deck card, never an empty/placeholder fortune.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from vpath_backend_sdk import AuthContext, require_auth

from .deck import draw_fortune

router = APIRouter()


class DrawRequest(BaseModel):
    """The oracle's prompt. The question is OPTIONAL ("ask nothing" == "")."""

    question: Optional[str] = Field(default=None, max_length=500)


class DrawResponse(BaseModel):
    fortune: str
    sign: str


@router.post("/draw", response_model=DrawResponse)
def draw(body: DrawRequest, ctx: AuthContext = Depends(require_auth)) -> DrawResponse:
    """Draw the deterministic card for the (optional) question."""
    card = draw_fortune(body.question or "")
    return DrawResponse(fortune=card.fortune, sign=card.sign)
