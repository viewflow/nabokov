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


# Punctuation that breaks a sentence into breath-length segments. Coordinating
# conjunctions are NOT breaks: a human run-on ("...and we don't have it then we
# tell ourselves...") must stay one long segment — that length IS the signal.
_SEGMENT_PUNCT = {",", ";", ":", "—", "–", "--", "(", ")"}  # noqa: RUF001 - en dash is a real break char


def segment_lengths(doc) -> list[int]:
    """Word count per punctuation-delimited segment within each sentence.

    LLM prose punctuates on a metronome — a comma or dash every clause, so
    segment lengths cluster tightly. Human prose under- and over-punctuates:
    a 25-word unpunctuated run beside a two-word aside. The CV of these
    lengths (via :func:`burstiness`) separates texts that sentence-level CV
    ties, because a balanced LLM sentence and a human run-on can be the same
    length while their internal punctuation differs completely.
    """
    out = []
    for sent in doc.sents:
        n = 0
        for t in sent:
            if t.is_space:
                continue
            if t.is_punct:
                if t.text in _SEGMENT_PUNCT and n:
                    out.append(n)
                    n = 0
            else:
                n += 1
        if n:
            out.append(n)
    return out


def content_tokens(doc) -> list[str]:
    """Lowercased alphabetic tokens — the input for the lexical-diversity metrics.

    The doc is built from the analysis text, so code fences and markup are
    already blanked and never reach this list.
    """
    return [t.lower_ for t in doc if t.is_alpha]


def mattr(tokens: list[str], window: int = 100) -> float:
    """Moving-average type-token ratio (MATTR).

    Plain TTR falls as a text grows (every "the" repeats), so it can't be
    compared across lengths. MATTR slides a fixed window over the text and
    averages the per-window TTR, which stays stable from a paragraph to a book.
    Texts shorter than the window fall back to plain TTR; empty input is 0.0.
    """
    n = len(tokens)
    if n == 0:
        return 0.0
    if n < window:
        return len(set(tokens)) / n
    counts: dict[str, int] = {}
    distinct = 0
    total = 0.0
    for i, tok in enumerate(tokens):
        counts[tok] = counts.get(tok, 0) + 1
        if counts[tok] == 1:
            distinct += 1
        if i >= window:
            old = tokens[i - window]
            counts[old] -= 1
            if counts[old] == 0:
                distinct -= 1
        if i >= window - 1:
            total += distinct / window
    return total / (n - window + 1)


# --- register metrics ---------------------------------------------------------
#
# Three numbers reported next to burstiness and diversity, and deliberately NOT
# scored. They come out of a 2025 synthesis on AI prose (see docs/rule-research.md)
# that gives directions without thresholds — "AI text is noun-heavier", "AI text
# under-uses anaphoric reference", "AI text skews to temporal connectives" — and the
# one effect size it does quote is an ARI difference of 19 vs 18, inside the noise
# of the grade metric nabokov already computes. A direction with no threshold is a
# number worth showing a writer and a terrible thing to build a finding on, so none
# of these three feeds --score or emits a code.

# Connectives that order events in time. Aimen et al. report AI essays leaning on
# these; a human writer more often links back to what was just said instead.
_TEMPORAL_CONNECTIVES = frozenset(
    {
        "then",
        "next",
        "afterwards",
        "afterward",
        "subsequently",
        "later",
        "finally",
        "eventually",
        "meanwhile",
        "thereafter",
        "previously",
        "initially",
        "first",
        "second",
        "third",
        "lastly",
        "before",
        "after",
        "until",
        "when",
        "while",
        "once",
    }
)

# Connectives that add, contrast, or explain rather than sequence.
_ADDITIVE_CONNECTIVES = frozenset(
    {
        "and",
        "also",
        "besides",
        "moreover",
        "furthermore",
        "additionally",
        "but",
        "however",
        "yet",
        "though",
        "although",
        "whereas",
        "nevertheless",
        "nonetheless",
        "instead",
        "rather",
        "because",
        "so",
        "therefore",
        "thus",
        "hence",
        "or",
        "nor",
    }
)

# The two sets must stay disjoint; test_the_connective_sets_are_disjoint pins it.
# "since" was briefly in both — it is genuinely causal ("since it failed, retry") and
# temporal ("since 2020") — and counting it on both sides does NOT cancel out of the
# ratio, as an earlier comment here claimed. With B words in both lists the value
# becomes (T+B)/(T+A+2B), which drags every document toward 0.5. A word that needs
# disambiguation before it can be classified is left out of both lists instead.


def nominal_density(doc) -> float:
    """Share of content words that are nouns (NOUN + PROPN), 0.0-1.0.

    A proxy for the "information density" claim: prose that packs meaning into noun
    phrases instead of verbs reads as denser and flatter. Related to NB304, which
    catches the specific lexical shape (a nominalization behind a light verb) but says
    nothing about the overall balance.
    """
    content = [t for t in doc if t.pos_ in ("NOUN", "PROPN", "VERB", "ADJ", "ADV")]
    if not content:
        return 0.0
    nouns = sum(1 for t in content if t.pos_ in ("NOUN", "PROPN"))
    return nouns / len(content)


def pronoun_density(doc) -> float:
    """Pronouns per 100 words — a rough anaphora proxy.

    A pronoun usually points back at something already named, so a low rate means the
    text keeps re-naming its subjects instead of referring to them. Rough on purpose:
    real anaphora resolution needs coreference, which the small spaCy model has not
    got, and this counts every pronoun including the "I" and "you" that carry voice
    rather than reference.
    """
    words = [t for t in doc if not (t.is_punct or t.is_space)]
    if not words:
        return 0.0
    return sum(1 for t in words if t.pos_ == "PRON") / len(words) * 100


def temporal_ratio(doc) -> float:
    """Temporal connectives as a share of temporal + additive ones, 0.0-1.0.

    High means the text mostly sequences ("then", "next", "finally"); low means it
    mostly relates ideas ("however", "because", "instead"). Returns 0.0 when the text
    has no connectives at all, which is indistinguishable here from a purely additive
    one — with nothing to divide, there is no ratio to report.

    The weakest of the three register metrics, and worth knowing why: "and", "but",
    "so" and "or" dominate the additive side by sheer frequency, so real documents
    cluster in a narrow band (every sample in this repo, technical docs and essays
    alike, lands between 0.14 and 0.20). It has far less spread than nominal or
    pronoun density, which makes it the least informative to diff.
    """
    lowered = [t.lower_ for t in doc if t.is_alpha]
    temporal = sum(1 for w in lowered if w in _TEMPORAL_CONNECTIVES)
    additive = sum(1 for w in lowered if w in _ADDITIVE_CONNECTIVES)
    total = temporal + additive
    if not total:
        return 0.0
    return temporal / total


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
