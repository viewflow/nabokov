"""NB316 — a claim attributed to nobody.

The rule's whole precision story is the determiner test and the source-markup
guard, so most of these tests are negatives.
"""

from __future__ import annotations

import pytest

from nabokov.issue import Applicability, Severity


def _found(result, code="NB316"):
    return [i for i in result.issues if i.code == code]


def _md(analyze, text):
    return analyze(text, is_markdown=True, name="doc.md")


# --- shape 1: generic subject + reporting verb ---------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Studies show that adoption grew.",
        "Research suggests a different cause.",
        "Recent studies indicate the opposite.",
        "Experts agree the approach works.",
        "Scientists have long argued the opposite.",
        "Surveys found that most teams disagree.",
        "Analysts estimate the market will shrink.",
    ],
)
def test_generic_subject_is_flagged(analyze, text):
    assert _found(analyze(text)), text


@pytest.mark.parametrize(
    "text",
    [
        "The study shows that adoption grew.",
        "This survey found the opposite.",
        "Our research shows a different cause.",
        "Smith's experiments confirmed it.",
        "That experiment proved nothing.",
    ],
)
def test_a_determiner_or_possessive_silences_it(analyze, text):
    """The one test the rule stands on: a reference the reader can follow.

    "The study" points at something specific under discussion; "studies" points
    outside the document at a source that is never named.
    """
    assert not _found(analyze(text)), text


def test_no_study_found_is_not_an_appeal_to_one(analyze):
    """Found by dogfooding docs/rule-research.md: "convention; no study found".

    An earlier draft carved "no", "any" and "such" out of the determiner test as
    "generic anyway". All three were wrong, and this line is the proof — the writer
    is saying a source does NOT exist, the opposite of appealing to one.
    """
    assert not _found(analyze("Every README needs an example: convention, no study found."))


def test_an_adjective_is_not_a_reference(analyze):
    """"Recent studies" names nobody, so amod children must not count as specific."""
    assert _found(analyze("Recent studies show a decline."))


def test_evidence_is_not_a_subject(analyze):
    """Paul Graham: "exonerated after new evidence proved he was not at the scene".

    Narrative, legal and incident-report prose use "evidence" for specific concrete
    evidence in the story being told. Dropped for the same reason "data" never went in.
    """
    assert not _found(analyze("He was exonerated after new evidence proved he was elsewhere."))


# --- shape 2: impersonal passive belief ---------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "It is widely believed that scale matters.",
        "It has been argued that caching is free.",
        "It is well known that DNS is hard.",
        "It is generally accepted that the format is dead.",
    ],
)
def test_impersonal_belief_is_flagged(analyze, text):
    assert _found(analyze(text)), text


def test_belief_needs_the_that_complement(analyze):
    """Without it the same words describe behaviour, not opinion."""
    assert not _found(analyze("It is known to fail on Windows."))
    assert not _found(analyze("It is understood by the parser."))


def test_both_parses_of_the_participle_are_handled(analyze):
    """spaCy reads this as a passive or as a predicate adjective, unpredictably.

    "It is well known that DNS is hard" parses as nsubjpass + participle-head inside
    a document, and as nsubj + copula with the participle as ``acomp`` when it stands
    alone. The rule found this the embarrassing way: it passed on a multi-sentence
    fixture and failed on the same sentence by itself.
    """
    assert _found(analyze("It is well known that DNS is hard."))
    assert _found(analyze("Caching helps. It is well known that DNS is hard. Ship it."))


def test_that_is_found_by_adjacency_not_the_parse(analyze):
    """spaCy attaches this "that" inconsistently, so position decides.

    In "it is widely believed that scale matters" it parses as ``det`` of *scale*'s
    head; in "it has been argued that caching is free" as ``mark`` of the complement
    clause. In neither is it a child of the reporting verb.
    """
    assert _found(analyze("It is widely believed that scale matters."))
    assert _found(analyze("It has been argued that caching is free."))


# --- shape 3: a bare quantifier as the subject --------------------------------


@pytest.mark.parametrize(
    "text",
    ["Many argue that the tradeoff is wrong.", "Some say the API is slow.", "Most would agree."],
)
def test_bare_quantifier_is_flagged(analyze, text):
    assert _found(analyze(text)), text


def test_naming_the_group_silences_it(analyze):
    """"Many developers argue" is loose, but it names who. That is already more
    than this rule asks for, and separating it from a weasel needs judgment."""
    assert not _found(analyze("Many developers argue that the tradeoff is wrong."))


# --- shape 4: fixed phrases ---------------------------------------------------


def test_fixed_phrase_is_flagged(analyze):
    assert _found(analyze("Conventional wisdom holds that caching is free."))


# --- the source-markup guard --------------------------------------------------


def test_a_link_in_the_paragraph_silences_the_paragraph(analyze):
    """Firing next to a citation would be the linter failing to read."""
    text = "Studies show that adoption grew ([Smith 2020](https://example.com/s)).\n"
    assert not _found(_md(analyze, text))


def test_a_bare_url_counts_as_a_source(analyze):
    text = "Surveys found the opposite. See https://example.com/survey for the data.\n"
    assert not _found(_md(analyze, text))


def test_the_guard_is_per_paragraph_not_per_document(analyze):
    """A sourced paragraph must not excuse an unsourced one elsewhere."""
    text = (
        "Studies show that adoption grew ([Smith 2020](https://example.com/s)).\n\n"
        "Experts agree the approach works.\n"
    )
    found = _found(_md(analyze, text))
    assert len(found) == 1
    assert found[0].line == 3


# --- shape of the finding -----------------------------------------------------


def test_always_a_rewrite_never_a_replace(analyze):
    """No string a tool can supply — only the author knows which source they meant."""
    for issue in _found(analyze("Studies show that adoption grew.")):
        assert issue.applicability is Applicability.REWRITE
        assert issue.suggestion


def test_research_and_experts_warn_but_the_crowd_is_advisory(analyze):
    """"Some say X, but ..." is common rhetorical setup even outside an essay."""
    assert _found(analyze("Studies show that adoption grew."))[0].severity is Severity.WARNING
    assert _found(analyze("Some say the API is slow."))[0].severity is Severity.INFO


def test_on_by_default(analyze):
    """People have written this forever, so it must not need --ai.

    That default-on requirement is why the rule sits in the NB3xx band rather than
    with the NB5xx AI tells, where NB503 owns the promotional reading.
    """
    from nabokov.checks import DEFAULT_CODES

    assert "NB316" in DEFAULT_CODES


def test_the_migrated_phrases_are_not_still_in_nb503(analyze):
    """They moved out of the editorializing list; a duplicate would double-report."""
    from nabokov.data_loader import ai_writing

    editorializing = ai_writing()["editorializing"]
    for phrase in ("studies show", "research suggests", "experts argue", "observers note"):
        assert phrase not in editorializing


def test_wins_over_the_passive_and_adverb_readings(analyze):
    """"It is widely believed that" is also a passive with an adverb in it.

    All three readings are true and only NB316's is useful: the defect is the
    missing source, not the voice. See ``_SPAN_PRECEDENCE``.
    """
    result = analyze("It is widely believed that scale matters.")
    assert _found(result)
    assert not _found(result, "NB302")
    assert not _found(result, "NB301")
