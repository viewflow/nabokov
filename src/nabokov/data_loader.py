"""Load the bundled data files that calibrate nabokov's checks.

The lists implement the classic prose checks and extend them: plain-language
phrase alternatives, extra hedges, and a fuller set of irregular participles.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


def _load(name: str) -> Any:
    with resources.files("nabokov.data").joinpath(name).open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def adverb_exceptions() -> frozenset[str]:
    """`-ly` words that are NOT flagged as adverbs (lowercased)."""
    return frozenset(w.lower() for w in _load("adverb_exceptions.json"))


@lru_cache(maxsize=1)
def qualifiers() -> frozenset[str]:
    """Weakening phrases (lowercased), 1-4 words each."""
    return frozenset(w.lower() for w in _load("qualifiers.json"))


@lru_cache(maxsize=1)
def passive_irregulars() -> frozenset[str]:
    """Irregular past participles used by the passive heuristic (membership only)."""
    return frozenset(k.lower() for k in _load("passive_irregulars.json"))


@lru_cache(maxsize=1)
def complex_phrases() -> dict[str, list[str]]:
    """Complex phrase (lowercased) -> list of simpler suggestions."""
    return {k.lower(): v for k, v in _load("complex_phrases.json").items()}


@lru_cache(maxsize=1)
def thresholds() -> dict[str, Any]:
    """ARI constants + hard/very-hard reading-level thresholds per target."""
    return _load("thresholds.json")


@lru_cache(maxsize=1)
def ai_writing() -> dict[str, list[str]]:
    """Signal lists for the NB5xx 'signs of AI writing' rules (from Wikipedia)."""
    data = _load("ai_writing.json")
    return {k: v for k, v in data.items() if not k.startswith("_")}
