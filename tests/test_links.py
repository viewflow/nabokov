"""NB312 — link text that does not say where it goes.

The rule the markup index was worth building for: the distinction between words
inside brackets and the same words in running prose.
"""

from __future__ import annotations

import pytest

from nabokov.issue import Applicability, Severity


def _found(result, code="NB312"):
    return [i for i in result.issues if i.code == code]


def _md(analyze, text):
    return analyze(text, is_markdown=True, name="t.md")


@pytest.mark.parametrize(
    "text",
    [
        "For the options, [click here](/config).\n",
        "See [here](/install) to install it.\n",
        "Read [this](/api) for details.\n",
        "[Learn more](/pricing)\n",
        "[read more](/blog/1)\n",
        "[More info](/faq)\n",
        "[**here**](/x)\n",  # emphasis is decoration around the same word
        "[this page](/x)\n",
    ],
)
def test_vague_link_text_flagged(analyze, text):
    assert _found(_md(analyze, text)), text


@pytest.mark.parametrize(
    "text",
    [
        "Read the [configuration guide](/config) before you deploy.\n",
        "The [Python API reference](/api) lists every method.\n",
        "See [docs/RULES.md](docs/RULES.md) for the full catalog.\n",
        # a substring match would wrongly fire on these
        "[Read the installation guide](/install)\n",
        "[More than you wanted to know about parsers](/deep)\n",
    ],
)
def test_descriptive_link_text_not_flagged(analyze, text):
    assert not _found(_md(analyze, text)), text


def test_the_same_words_in_prose_are_not_a_link(analyze):
    """This is the case a phrase match cannot get right."""
    text = "Click here is a phrase about a button, not a link.\n"
    assert not _found(_md(analyze, text))


def test_badge_link_not_flagged(analyze):
    """[![build](badge.svg)](url) — the outer link's text is an image."""
    assert not _found(_md(analyze, "[![build](badge.svg)](https://ci.example.com)\n"))


def test_plain_text_never_fires(analyze):
    assert not _found(analyze("See [here](/x) — but this is a .txt file.\n"))


# --- shape --------------------------------------------------------------------


def test_message_names_the_target(analyze):
    """So the writer can name the destination without going to look it up."""
    issue = _found(_md(analyze, "See [here](/install/linux) to install.\n"))[0]
    assert "/install/linux" in issue.message


def test_is_a_rewrite_not_a_substitution(analyze):
    """Only the author knows what is worth saying about the destination."""
    issue = _found(_md(analyze, "See [here](/x).\n"))[0]
    assert issue.applicability is Applicability.REWRITE
    assert issue.severity is Severity.WARNING


def test_span_covers_only_the_link_text(analyze):
    issue = _found(_md(analyze, "For options, [click here](/config).\n"))[0]
    assert issue.text == "click here"
