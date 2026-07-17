from __future__ import annotations

from meridian.narratives.base import Narrative

NARRATIVES: dict[str, Narrative] = {}


def register(narrative: Narrative) -> Narrative:
    NARRATIVES[narrative.name] = narrative
    return narrative


def next_account_id(counter: int) -> str:
    return f"A{counter:06d}"
