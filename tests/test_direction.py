"""NB310 — orienting the reader by position ("the diagram above")."""

from __future__ import annotations

import pytest

from nabokov.config import Config
from nabokov.issue import Applicability, Severity


def _found(result, code="NB310"):
    return [i for i in result.issues if i.code == code]


# --- fires --------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "In the diagram above, clients run jobs on clusters.",
        "The diagram above shows the topology.",
        "Check the table below.",
        "See above for the full list of options.",
        "As shown below, the parser handles nesting.",
        "Read the first example above before you start.",
        "The screenshots above cover both cases.",
    ],
)
def test_directional_language_flagged(analyze, text):
    assert _found(analyze(text)), text


# --- must not fire ------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # a real preposition with a real object — ordinary English about the world
        "Values above 50 percent are rejected by the validator.",
        "The sensor sits above the intake manifold.",
        "Temperatures below freezing stop the reaction.",
        "The cache layer below the API absorbs the load.",
        # bare postmodifier, but the noun is a shelf, not a document element
        "Put the spare key on the shelf above.",
        # already the fix
        "Read the preceding section before you start.",
        "The following table lists every flag.",
    ],
)
def test_not_flagged(analyze, text):
    assert not _found(analyze(text)), text


def test_left_and_right_are_not_flagged(analyze):
    """Deliberate: "the right-hand side" is usually describing a UI, where the
    position is the content rather than a way of navigating the page."""
    assert not _found(analyze("The controls sit on the right-hand side of the screen."))


# --- fix tiers ----------------------------------------------------------------


def test_determiner_phrase_earns_replace(analyze):
    """The whole phrase is the span, so moving the word stays a substitution."""
    issue = _found(analyze("Check the table below."))[0]
    assert issue.applicability is Applicability.REPLACE
    assert issue.text == "the table below"
    assert issue.suggestion == "the following table"


def test_replace_actually_substitutes(analyze):
    text = "In the diagram above, clients run jobs."
    result = analyze(text)
    issue = _found(result)[0]
    start = result.source.offset(issue.line, issue.col)
    end = result.source.offset(issue.end_line, issue.end_col)
    assert text[:start] + issue.suggestion + text[end:] == (
        "In the preceding diagram, clients run jobs."
    )


def test_sentence_initial_replacement_keeps_the_capital(analyze):
    issue = _found(analyze("The diagram above shows the topology."))[0]
    assert issue.suggestion == "The preceding diagram"


def test_adjective_between_drops_to_rewrite(analyze):
    """ "the first example above" needs reordering judgment, not a substitution."""
    issue = _found(analyze("Read the first example above before you start."))[0]
    assert issue.applicability is Applicability.REWRITE
    assert issue.suggestion == "the preceding example"


def test_bare_idiom_asks_for_a_link(analyze):
    """ "See above" has no noun to reposition, so the fix is a cross-reference."""
    issue = _found(analyze("See above for the full list."))[0]
    assert issue.applicability is Applicability.REWRITE
    assert "link to it" in issue.suggestion


def test_severity_is_info(analyze):
    assert _found(analyze("Check the table below."))[0].severity is Severity.INFO


def test_off_for_social(analyze):
    result = analyze("Check the table below.", config=Config(target="SOCIAL"))
    assert not _found(result)


# --- known limitation ---------------------------------------------------------


def test_known_limitation_verbless_parse(analyze):
    """ "The table below lists every flag." is missed, and the cause is upstream.

    spaCy tags "lists" as a plural NOUN and makes it the object of "below",
    finding no verb in the sentence at all. A real prepositional object is what
    separates "above 50 percent" from a bare postmodifier, so the guard is right
    to decline — loosening it to recover this sentence would cost precision on
    every genuine preposition.

    Pinned rather than xfailed: if a future model parses this correctly the test
    fails, which is the signal to delete it. The neighbouring shapes ("Check the
    table below", "The diagram above shows …") are covered above.
    """
    assert not _found(analyze("The table below lists every flag."))
