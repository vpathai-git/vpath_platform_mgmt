"""The oracle's deck — a fixed, curated set of fortunes.

DETERMINISTIC by design (CLAUDE.md §7: never randomness that breaks
reproducibility). The card for a question is chosen by a STABLE hash of the
question text, so the same question always draws the same fortune — which is
what lets the UI test cite an exact rendered string. Python's builtin hash()
is salted per process (PYTHONHASHSEED) and would break that across runs, so we
hash with hashlib.sha256 instead. The empty question ("" — the "ask nothing"
case) is just as deterministic.

The deck is non-empty, so an index is always valid: a draw is ALWAYS a real
card, never an empty/placeholder fortune (no soft fallback, CLAUDE.md §7).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    """One fortune and its oracle sign (a thematic label, not a secret)."""

    fortune: str
    sign: str


# Twelve cards — curated, stable order. The order is part of the contract:
# changing it changes which question maps to which card (and the UI test's
# cited string), so treat reordering as a behavior change.
DECK: list[Card] = [
    Card("A door you stopped knocking on is about to open.", "The Open Gate"),
    Card("The patience you spent will be repaid with interest.", "The Slow Tide"),
    Card("Say the quiet thing out loud; it has waited long enough.", "The Bell"),
    Card(
        "What feels like an ending is the soil for the next thing.",
        "The Fallow Field",
    ),
    Card("A small, honest choice today outshines a grand one tomorrow.", "The Lantern"),
    Card("The person you keep avoiding holds the missing half.", "The Mirror"),
    Card(
        "Rest is not retreat — the strong stream pauses before the fall.",
        "The Still Pool",
    ),
    Card("You already know the answer; you are negotiating with it.", "The Crossroads"),
    Card("Luck favors the one who ships the unfinished thing.", "The Rising Kite"),
    Card(
        "Let the old grudge go; it is heavier than the wrong it marks.",
        "The Loosened Knot",
    ),
    Card(
        "A stranger's kindness this week is a debt you'll gladly carry.",
        "The Warm Hearth",
    ),
    Card("Trust the work done in the dark; dawn keeps no secrets.", "The First Light"),
]


def _stable_index(question: str) -> int:
    """Map any question text to a fixed deck index via a stable hash."""
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    return int(digest, 16) % len(DECK)


def draw_fortune(question: str) -> Card:
    """Draw the (deterministic) card for this question. Always a real card."""
    return DECK[_stable_index(question)]
