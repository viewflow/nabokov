"""A dependency-free implementation of the classic regex-and-dictionaries prose checks.

Implements the classic regex-and-dictionaries baseline — the bundled word lists,
no NLP. The calibration test compares nabokov against it:

* data-driven rules (complex phrases, qualifiers) must match it exactly;
* the spaCy rules (adverbs, passive) diverge in documented, bounded ways.
"""

from __future__ import annotations

import re

from nabokov.data_loader import (
    adverb_exceptions,
    complex_phrases,
    passive_irregulars,
    qualifiers,
)

_WORD = re.compile(r"\b[\w'-]+\b", re.IGNORECASE)
_PASSIVE = re.compile(r"\s(is|are|was|were|be|been|being)\s([a-z]{2,30})\b(\sby\b)?", re.IGNORECASE)


def adverbs(text: str) -> list[str]:
    """Words ending in -ly, minus the exception list (the classic rule)."""
    exc = adverb_exceptions()
    return [
        m.group(0)
        for m in _WORD.finditer(text)
        if m.group(0).lower().endswith("ly") and m.group(0).lower() not in exc
    ]


def passive(text: str) -> list[str]:
    """`(is|are|was|were|be|been|being) + word(ed|irregular)` — the classic rule."""
    irr = passive_irregulars()
    out = []
    for m in _PASSIVE.finditer(text):
        second = m.group(2).lower()
        if second.endswith("ed") or second in irr:
            out.append(m.group(0).lstrip())
    return out


def _phrase_matches(text: str, table) -> list[str]:
    tokens = [(m.group(0), m.start()) for m in _WORD.finditer(text)]
    used: set[int] = set()
    found: list[str] = []
    for i, (word, start) in enumerate(tokens):
        # build 1..4 word candidates requiring single-space adjacency
        cands = [word]
        pos = start
        prev = word
        for k in range(1, 4):
            j = i + k
            if j >= len(tokens):
                break
            nxt, nstart = tokens[j]
            if nstart == pos + len(prev) + 1:
                cands.append(f"{cands[-1]} {nxt}")
                pos = nstart
                prev = nxt
            else:
                break
        for cand in reversed(cands):  # longest first
            span = range(i, i + cand.count(" ") + 1)
            if cand.lower() in table and not any(t in used for t in span):
                used.update(span)
                found.append(cand)
                break
    return found


def complex_words(text: str) -> list[str]:
    return _phrase_matches(text, complex_phrases())


def qualifier_words(text: str) -> list[str]:
    return _phrase_matches(text, qualifiers())


def counts(text: str) -> dict[str, int]:
    return {
        "adverbs": len(adverbs(text)),
        "passive": len(passive(text)),
        "complex": len(complex_words(text)),
        "qualifiers": len(qualifier_words(text)),
    }
