"""Readability scoring — the Automated Readability Index (ARI).

The formula:

    readingLevel = max(round(letters/words*4.71 + words/sentences*0.5 - 21.43), 0)

where ``letters`` is the count of word characters. A sentence is classified against
the active reading-level target (default NORMAL): it must have at least
``tooFewWordCount`` words to be eligible, then ``hard`` at ``hardReadabilityLevel``
and ``veryHard`` at ``veryHardReadabilityLevel``.
"""

from __future__ import annotations

import math
import re
import statistics

from .data_loader import thresholds

_WORD_CHAR = re.compile(r"[A-Za-z0-9_]")  # JS /\w/ is ASCII

NORMAL = "normal"
HARD = "hard"
VERY_HARD = "veryHard"


def letters_in(text: str) -> int:
    """Count word characters (the ``letters`` in the ARI formula)."""
    return len(_WORD_CHAR.findall(text))


def _js_round(x: float) -> int:
    # JS Math.round rounds .5 up; Python round() is banker's rounding. Match JS.
    return math.floor(x + 0.5)


def reading_level(letters: int, words: int, sentences: int) -> int:
    """The ARI grade level, floored at 0."""
    if words == 0 or sentences == 0:
        return 0
    ari = letters / words * 4.71 + words / sentences * 0.5 - 21.43
    return max(_js_round(ari), 0)


def sentence_lengths(doc) -> list[int]:
    """Word count per sentence (ignoring punctuation and whitespace).

    The single source of truth for sentence-length metrics — both the NB509
    rhythm rule and the document stats read burstiness from these counts.
    """
    out = []
    for sent in doc.sents:
        n = sum(1 for t in sent if not (t.is_punct or t.is_space))
        if n:
            out.append(n)
    return out


def burstiness(lengths: list[int]) -> float:
    """Coefficient of variation (stdev / mean) of sentence lengths.

    High = varied, human rhythm; low = flat, machine-uniform. 0.0 when there is
    too little to measure (fewer than two sentences, or an empty document).
    """
    if len(lengths) < 2:
        return 0.0
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    return statistics.pstdev(lengths) / mean


def target_config(target: str) -> dict[str, int]:
    targets = thresholds()["readability_targets"]
    return targets.get(target.upper(), targets["NORMAL"])


def burstiness_thresholds(target: str) -> tuple[float, float]:
    """(min, flat) sentence-length CV cutoffs for a target.

    A CV below ``min`` is advisory (flat rhythm); below ``flat`` it is a
    confident tell. Short-form targets tolerate flatter rhythm.
    """
    table = thresholds().get("burstiness", {})
    cfg = table.get(target.upper()) or table.get("NORMAL") or {"min": 0.40, "flat": 0.28}
    return float(cfg["min"]), float(cfg["flat"])


def classify(level: int, words: int, target: str) -> str:
    """Bucket a reading level into normal / hard / veryHard for a target."""
    cfg = target_config(target)
    if words < cfg["tooFewWordCount"]:
        return NORMAL
    if cfg["hardReadabilityLevel"] <= level < cfg["veryHardReadabilityLevel"]:
        return HARD
    if level >= cfg["veryHardReadabilityLevel"]:
        return VERY_HARD
    return NORMAL
