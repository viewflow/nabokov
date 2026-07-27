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
from itertools import pairwise

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


# --- quality metrics ----------------------------------------------------------
#
# Four numbers out of the automated essay scoring literature (see
# docs/text-quality-research.md). Reported, never scored — same rule as the register
# block above, and for a sharper reason. Every correlation behind them was measured
# on student or L2 exam essays, where the variance being explained is basic writing
# competence; nabokov edits prose by people who already write fluently. Nothing in
# that literature tests whether the relationships survive the shift, so a threshold
# here would be an extrapolation wearing a citation. The numbers are worth showing a
# writer and a bad thing to fail a build on.

_CONTENT_POS = frozenset({"NOUN", "PROPN", "VERB", "ADJ", "ADV"})


def _content_lemmas(span) -> set[str]:
    """Content lemmas of a span — the vocabulary a paragraph can share with its neighbour."""
    return {
        t.lemma_.lower() for t in span if t.pos_ in _CONTENT_POS and t.is_alpha and not t.is_stop
    }


# Below this many content words a paragraph has no vocabulary to share. Headings,
# one-line asides and code captions would otherwise read as cohesion gaps and drag
# the mean toward a failure the writer cannot fix.
_MIN_PARA_CONTENT = 5


def paragraph_cohesion(doc, ranges) -> float:
    """Mean content-lemma overlap between adjacent paragraphs, 0.0-1.0.

    The highest-correlating quality feature that a dependency parse alone can reach:
    Crossley, Kyle & McNamara (2016) measure adjacent-paragraph overlap at r=.40
    against expert quality ratings and r=.42 against coherence — while the *same*
    study's sentence-level overlap runs negative (all-lemma TTR r=-.29). Global
    cohesion predicts quality; local cohesion does not. Their conclusion: "coherence
    for expert raters is a property of global cohesion and not of local cohesion."

    Normalised by the smaller of the two paragraphs, not by their union. Jaccard was
    tried first and rejected: it divides by total vocabulary, so a long paragraph
    scores badly for being long, and every document in this repo collapsed into
    0.04-0.05 with no room to tell them apart.

    Calibration, and how it was checked. Repo prose measures 0.07-0.40 per file.
    Shuffling a document's paragraphs — same vocabulary, destroyed adjacency — drops
    the score on every file tried (0.116 to 0.065 on this repo's longest doc,
    consistently in that direction across four files). That is the evidence it reads
    order rather than word choice, which is the only claim being made for it.

    Two honest limits. TAACO normalises differently and reports a family of indices,
    so this number is comparable to itself across drafts, never to a published
    figure. And the negative local result is confounded: the companion study that
    *manipulated* cohesion found adding it raised quality. So this tracks the signal
    that survived both designs — global beats local — and nothing finer.

    Returns 0.0 when fewer than two paragraphs clear ``_MIN_PARA_CONTENT``, which is
    indistinguishable here from paragraphs that genuinely share nothing.
    """
    sets: list[set[str]] = []
    for start, end in ranges:
        span = doc.char_span(start, end, alignment_mode="expand")
        if span is None:
            continue
        lemmas = _content_lemmas(span)
        if len(lemmas) >= _MIN_PARA_CONTENT:
            sets.append(lemmas)
    if len(sets) < 2:
        return 0.0
    scores = [
        len(first & second) / min(len(first), len(second)) for first, second in pairwise(sets)
    ]
    return sum(scores) / len(scores) if scores else 0.0


def dependency_distance(doc) -> float:
    """Mean dependency distance — average head-to-dependent token gap.

    Yannakoudakis, Briscoe & Medlock (2011) added grammatical-relation distance to a
    model that already knew sentence length and watched score prediction rise from
    r=.692 to r=.714; ablating it cost more than any feature except error rate. So it
    carries signal that length alone does not.

    Read it as structural spread, not as difficulty. That study predicts *exam
    score*, which is a different construct from reading effort, and the
    dependency-locality work that would license the difficulty reading is not in
    evidence here. It is reported next to the grade for contrast, and deliberately
    does not feed NB201/NB202.
    """
    gaps = [
        abs(t.i - t.head.i) for t in doc if t.head is not t and not (t.is_punct or t.is_space)
    ]
    return sum(gaps) / len(gaps) if gaps else 0.0


# The Heylighen & Dewaele deictic split: context-independent classes score up,
# context-dependent ones score down. spaCy splits auxiliaries out of VERB, so AUX is
# counted with the verbs — the original formula predates the distinction and treats
# every verb alike.
_FORMAL_POS = frozenset({"NOUN", "PROPN", "ADJ", "ADP"})
_DEICTIC_POS = frozenset({"PRON", "VERB", "AUX", "ADV", "INTJ"})
_ARTICLES = frozenset({"a", "an", "the"})


def formality(doc) -> float:
    """Heylighen & Dewaele F-score, 0-100. Higher = more formal and informational.

    F = (noun% + adjective% + preposition% + article%
         - pronoun% - verb% - adverb% - interjection% + 100) / 2

    The published, validated combination of exactly the part-of-speech ratios the
    register block above computes ad hoc. Reported values: written 62 vs spoken 42;
    scientific 66, newspapers 68, novels 52. On matched material from the same
    speakers, informal conversation 44 against a written exam essay 56.

    Caveat worth carrying: those figures come from Dutch word-frequency lists and
    French interlanguage. No English validation was retrieved. The formula is
    language-general in construction, which is an argument rather than evidence.
    """
    words = [t for t in doc if not (t.is_punct or t.is_space)]
    if not words:
        return 0.0
    total = len(words)
    formal = sum(1 for t in words if t.pos_ in _FORMAL_POS)
    formal += sum(1 for t in words if t.pos_ == "DET" and t.lower_ in _ARTICLES)
    deictic = sum(1 for t in words if t.pos_ in _DEICTIC_POS)
    return ((formal - deictic) / total * 100 + 100) / 2


# Dependents that elaborate a noun. Both the pre-modifiers Coh-Metrix counts and the
# post-modifying phrases Biber's compression argument turns on, since the interesting
# claim is about noun phrases growing heavier, not about where the weight sits.
_NP_MODIFIER_DEPS = frozenset(
    {"amod", "det", "poss", "compound", "nummod", "nmod", "prep", "acl", "relcl", "appos"}
)


def modifier_density(doc) -> float:
    """Modifiers per noun phrase head.

    Replicated three times at modest strength: Crossley & McNamara (2014) report
    r=.213 with quality, Guo, Crossley & McNamara (2013) r=.264 on integrated and
    r=.377 on independent TOEFL essays. All three numbers were read inside a later
    literature review rather than the underlying papers, and all three come from L2
    writing.

    It is the one survivor of the syntactic-complexity family. Biber, Gray & Poonpon
    (2011) put complex noun phrases — not subordination — at the centre of mature
    academic prose, and traditional T-unit complexity indices explain under 6% of
    quality variance (Kyle & Crossley 2017), which is why nabokov computes this and
    not L2SCA.

    Compound children are excluded as heads so "machine learning model" counts once.
    """
    heads = [t for t in doc if t.pos_ in ("NOUN", "PROPN") and t.dep_ != "compound"]
    if not heads:
        return 0.0
    mods = sum(1 for h in heads for c in h.children if c.dep_ in _NP_MODIFIER_DEPS)
    return mods / len(heads)


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
