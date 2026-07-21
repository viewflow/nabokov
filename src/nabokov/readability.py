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


def target_config(target: str) -> dict[str, int]:
    targets = thresholds()["readability_targets"]
    return targets.get(target.upper(), targets["NORMAL"])


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
