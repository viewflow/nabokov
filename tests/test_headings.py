"""NB313 — terminal punctuation on a heading."""

from __future__ import annotations

import pytest

from nabokov.issue import Applicability, Severity


def _found(result, code="NB313"):
    return [i for i in result.issues if i.code == code]


def _md(analyze, text):
    return analyze(text, is_markdown=True, name="t.md")


@pytest.mark.parametrize(
    "heading",
    [
        "# Title.",
        "## Requirements:",
        "### Install, configure,",
        "#### One thing;",
        "###### Trailing spaces.   ",
    ],
)
def test_terminal_punctuation_flagged(analyze, heading):
    assert _found(_md(analyze, heading + "\n\nBody.\n")), heading


@pytest.mark.parametrize(
    "heading",
    [
        "### Is it ready?",  # a question heading is legitimate
        "#### Coming soon...",  # ellipsis is a device, not a slip
        "#### Coming soon…",  # the single-character form too
        "## Step 1: Install",  # internal colon, not trailing
        "##### Using `array.map()`",  # ends in a backtick
        "## Version 1.2",
        "# nabokov",
    ],
)
def test_legitimate_headings_not_flagged(analyze, heading):
    assert not _found(_md(analyze, heading + "\n\nBody.\n")), heading


def test_body_prose_is_untouched(analyze):
    """Only headings. Ordinary sentences end in full stops for a living."""
    assert not _found(_md(analyze, "# Title\n\nThis is a sentence. So is this.\n"))


def test_plain_text_never_fires(analyze):
    assert not _found(analyze("# Title.\n\nBody.\n"))


# --- the fix ------------------------------------------------------------------


def test_fix_is_a_clean_deletion(analyze):
    issue = _found(_md(analyze, "# Title.\n\nBody.\n"))[0]
    assert issue.applicability is Applicability.REPLACE
    assert issue.suggestion == ""
    assert issue.text == "."
    assert issue.severity is Severity.INFO


def test_deleting_the_span_repairs_the_heading(analyze):
    text = "## Requirements:\n\nBody.\n"
    result = _md(analyze, text)
    issue = _found(result)[0]
    start = result.source.offset(issue.line, issue.col)
    end = result.source.offset(issue.end_line, issue.end_col)
    assert text[:start] + text[end:] == "## Requirements\n\nBody.\n"


def test_column_is_right_after_trailing_whitespace(analyze):
    """The mark is found after rstrip, so the offset must not include the spaces."""
    text = "## Setup.   \n\nBody.\n"
    result = _md(analyze, text)
    issue = _found(result)[0]
    start = result.source.offset(issue.line, issue.col)
    assert text[start] == "."


def test_several_headings_each_reported(analyze):
    text = "# One.\n\nBody.\n\n## Two:\n\nMore body.\n\n### Three\n\nEnd.\n"
    assert len(_found(_md(analyze, text))) == 2
