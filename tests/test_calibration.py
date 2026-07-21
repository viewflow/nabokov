"""Calibration against the classic regex baseline (see classic_ref).

The baseline implements the classic regex-and-dictionaries checks, so this
pins nabokov's fidelity:

* data-driven rules (complex phrases, qualifiers) must match the baseline exactly;
* the spaCy rules diverge in a bounded, documented direction — adverbs are a subset
  (spaCy's POS gate drops some -ly words the baseline flags), and passive agrees on
  canonical constructions.

Phrases here are all <= 4 words, the length the classic matcher actually reaches;
nabokov's PhraseMatcher additionally catches the handful of 5-word dictionary keys
(e.g. "due to the fact that") that the classic 4-word cap never matches — a
deliberate improvement, excluded from the exact-match passages.
"""

from __future__ import annotations

import pytest

import classic_ref as ref

PASSAGES = [
    "We should utilize the tool in order to win the annual game.",
    "A number of people gave feedback with respect to the new design.",
    "In my opinion we should ask first, and I think we can wait.",
    "The committee will endeavor to ascertain the facts by tomorrow.",
    "He was accompanied by a friend who could facilitate the whole meeting.",
    "This is a numerous and frequently cited list of possible improvements.",
    "Maybe we can utilize the results, but perhaps it is sort of risky.",
    "The plan was implemented quickly and the report was reviewed carefully.",
]


def _count(result, code: str) -> int:
    return sum(1 for i in result.issues if i.code == code)


@pytest.mark.parametrize("text", PASSAGES)
def test_complex_phrases_match_baseline_exactly(text, analyze):
    result = analyze(text)
    assert _count(result, "NB401") == len(ref.complex_words(text)), text


@pytest.mark.parametrize("text", PASSAGES)
def test_qualifiers_match_baseline_exactly(text, analyze):
    result = analyze(text)
    assert _count(result, "NB303") == len(ref.qualifier_words(text)), text


@pytest.mark.parametrize("text", PASSAGES)
def test_adverbs_are_subset_of_baseline(text, analyze):
    result = analyze(text)
    nabokov_adv = {i.text.lower() for i in result.issues if i.code == "NB301"}
    baseline_adv = {a.lower() for a in ref.adverbs(text)}
    assert nabokov_adv <= baseline_adv, (nabokov_adv, baseline_adv, text)


def test_passive_agreement_on_canonical_passives(analyze):
    # simple "(was|were) + participle" passives — both nabokov and the baseline catch these
    for text in [
        "The cake was eaten by the dog.",
        "The report was reviewed by the board.",
        "The results were shared with everyone.",
    ]:
        result = analyze(text)
        assert any(i.code == "NB302" for i in result.issues), text
        assert ref.passive(text), text


def test_passive_progressive_is_a_documented_improvement(analyze):
    # "is being painted": the baseline regex consumes "is being" and never re-checks
    # "being painted", so it misses this passive; spaCy's auxpass catches it.
    text = "The house is being painted this week by the crew."
    result = analyze(text)
    assert any(i.code == "NB302" for i in result.issues)
    assert ref.passive(text) == []  # the baseline misses it


def test_five_word_key_is_a_documented_improvement(analyze):
    # the classic 4-word matcher never reaches this 5-word key; nabokov does.
    text = "We delayed it due to the fact that funding was late."
    result = analyze(text)
    assert _count(result, "NB401") >= 1
    assert ref.complex_words(text) == []  # the baseline misses it
