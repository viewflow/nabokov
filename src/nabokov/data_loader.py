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
    """Weakening phrases (lowercased), 1-4 words each — every phrase NB303 matches."""
    groups = qualifier_fixes()
    return frozenset(groups["cut"]) | frozenset(groups["replace"]) | frozenset(groups["rewrite"])


@lru_cache(maxsize=1)
def qualifier_fixes() -> dict[str, Any]:
    """NB303 fix data: 'cut' phrase list, 'replace' map, 'rewrite' guidance map."""
    data = _load("qualifiers.json")
    return {
        "cut": [w.lower() for w in data["cut"]],
        "replace": {k.lower(): v for k, v in data["replace"].items()},
        "rewrite": {k.lower(): v for k, v in data["rewrite"].items()},
    }


@lru_cache(maxsize=1)
def passive_irregulars() -> frozenset[str]:
    """Irregular past participles used by the passive heuristic (membership only)."""
    return frozenset(k.lower() for k in _load("passive_irregulars.json"))


@lru_cache(maxsize=1)
def participle_to_past() -> dict[str, str]:
    """Irregular past participle -> simple past ('written' -> 'wrote').

    NB302 drafts the active-voice rewrite with this. Regular verbs are absent
    because the two forms coincide ("celebrated" -> "celebrated"), so a caller
    falls back to the participle itself on a miss.
    """
    return {k.lower(): v.lower() for k, v in _load("passive_irregulars.json").items()}


@lru_cache(maxsize=1)
def complex_phrases() -> dict[str, list[str]]:
    """Complex phrase (lowercased) -> list of simpler suggestions."""
    return {k.lower(): v for k, v in _load("complex_phrases.json").items()}


@lru_cache(maxsize=1)
def thresholds() -> dict[str, Any]:
    """ARI constants + hard/very-hard reading-level thresholds per target."""
    return _load("thresholds.json")


@lru_cache(maxsize=1)
def ai_writing() -> dict[str, Any]:
    """Signal lists for the NB5xx 'signs of AI writing' rules (from Wikipedia).

    Mostly term lists; ``puffery_alternatives`` is a word -> plain-alternatives map.
    """
    data = _load("ai_writing.json")
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=1)
def concreteness() -> dict[str, float]:
    """Brysbaert et al. (2014) concreteness ratings, lemma -> 1.0 (abstract) .. 5.0."""
    data = _load("concreteness.json")
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=1)
def nominalizations() -> dict[str, Any]:
    """NB304 data: 'light_verbs' lemma list + 'nouns' nominalization -> verb map."""
    data = _load("nominalizations.json")
    return {k: v for k, v in data.items() if not k.startswith("_")}
