"""NB314 — a list step that names the reader instead of using the imperative."""

from __future__ import annotations

import pytest

from nabokov.config import Config
from nabokov.issue import Applicability, Severity

STEPS = "## Setup\n\n"


def _found(result, code="NB314"):
    return [i for i in result.issues if i.code == code]


def _md(analyze, body, name="t.md"):
    return analyze(STEPS + body, is_markdown=True, name=name)


@pytest.mark.parametrize(
    ("item", "draft"),
    [
        ("1. You should click Save.\n", "Click Save"),
        ("1. The user clicks Continue.\n", "Click Continue"),
        ("1. You need to run the migration.\n", "Run the migration"),
        ("1. You can add a plugin here.\n", "Add a plugin here"),
        ("- You must accept the terms.\n", "Accept the terms"),
    ],
)
def test_reader_subject_flagged_with_a_draft(analyze, item, draft):
    issue = _found(_md(analyze, item))[0]
    assert issue.suggestion == draft


@pytest.mark.parametrize(
    "item",
    [
        # already imperative
        "1. Click Save to continue.\n",
        "- Run the migration first.\n",
        # a fact list, which is what made the obvious framing of this rule hard
        "- Requires Python 3.12 or newer.\n",
        "- The parser handles nested lists.\n",
        "- MIT licensed.\n",
        "- Fast: it parses ten thousand lines a second.\n",
    ],
)
def test_imperatives_and_facts_not_flagged(analyze, item):
    assert not _found(_md(analyze, item)), item


def test_body_prose_is_untouched(analyze):
    """Outside a list the second person is Google's own recommended phrasing."""
    text = "You can create a website with it. You should read the guide first.\n"
    assert not _found(analyze(text, is_markdown=True))


def test_a_paragraph_after_a_list_is_untouched(analyze):
    body = "1. Click Save.\n\nYou can also edit the file by hand.\n"
    assert not _found(_md(analyze, body))


def test_plain_text_never_fires(analyze):
    """No list markers are indexed, so there are no steps to judge."""
    assert not _found(analyze("1. You should click Save.\n"))


# --- the off-by-one that made two of three items invisible --------------------


def test_first_item_after_a_blank_line_is_seen(analyze):
    """_LIST_MARKER's leading \\s* swallows the blank line's newline, so the
    marker span starts a line early. The rule keys off span.end instead."""
    body = "1. You should click Save.\n2. You should click Next.\n3. You should stop.\n"
    assert len(_found(_md(analyze, body))) == 3


# --- shape --------------------------------------------------------------------


def test_is_info_and_a_rewrite(analyze):
    """Dropping the subject can drop an adverb that sat before the verb, so the
    draft is a direction rather than a substitution."""
    issue = _found(_md(analyze, "1. You should click Save.\n"))[0]
    assert issue.severity is Severity.INFO
    assert issue.applicability is Applicability.REWRITE


@pytest.mark.parametrize("target", ["ESSAY", "SOCIAL"])
def test_off_where_the_writer_owns_the_voice(analyze, target):
    result = analyze(
        STEPS + "1. You should click Save.\n",
        is_markdown=True,
        config=Config(target=target),
    )
    assert not _found(result)
