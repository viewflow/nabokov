"""NB317 — invisible and look-alike characters.

Moved out of NB519 (AI artifacts) and turned on by default. The reason is in the
module docstring and in docs/detection-research.md: a detector normalizes these
away before scoring, so they are not evidence of authorship — just a defect that
breaks search and copy-paste for every reader.
"""

from __future__ import annotations

from nabokov.issue import Applicability, Severity

ZWSP = "​"
WORD_JOINER = "⁠"
BOM = "﻿"
CYRILLIC_E = "е"


def _found(result, code="NB317"):
    return [i for i in result.issues if i.code == code]


# --- invisible characters -----------------------------------------------------


def test_invisible_characters_flagged(analyze):
    result = analyze(f"The plan{ZWSP} works fine and ships{WORD_JOINER} this week.")
    assert len(_found(result)) == 2


def test_bom_mid_text_flagged(analyze):
    assert _found(analyze(f"The parser{BOM} handles nesting."))


def test_deleting_an_invisible_character_is_a_replace(analyze):
    """It carries no meaning and no width, so nothing around it changes."""
    issue = _found(analyze(f"The plan{ZWSP} works fine."))[0]
    assert issue.applicability is Applicability.REPLACE
    assert issue.suggestion == ""
    assert issue.severity is Severity.WARNING


def test_the_codepoint_is_named(analyze):
    """An invisible defect the message cannot show has to be named instead."""
    issue = _found(analyze(f"The plan{ZWSP} works."))[0]
    assert "U+200B" in issue.message


def test_nbsp_is_not_flagged(analyze):
    """Russian and French typography use it. Firing here would hit correct writing."""
    assert not _found(analyze("Nous avons 5 km to go."))


# --- homoglyphs ---------------------------------------------------------------


def test_homoglyph_swap_flagged(analyze):
    result = analyze(f"Our d{CYRILLIC_E}tection rate improved this quarter.")
    issues = _found(result)
    assert issues and "look-alike" in issues[0].message


def test_homoglyph_is_a_rewrite_not_a_replace(analyze):
    """The tool cannot know which alphabet was meant; guessing would change a word."""
    issue = _found(analyze(f"Our d{CYRILLIC_E}tection rate improved."))[0]
    assert issue.applicability is Applicability.REWRITE


def test_legit_mixed_language_not_flagged(analyze):
    """Whole-script words, a Cyrillic suffix on a Latin brand, and unit prefixes.

    The sandwich shape is what protects these — none has an interior mixed letter.
    """
    result = analyze("Мы пишем в Slackе каждый день. The delay was 5 μs overall.")
    assert not _found(result)


# --- scope --------------------------------------------------------------------


def test_on_by_default(analyze):
    """The whole point of the split: this needs no --ai.

    A zero-width space breaks search and copy-paste whoever typed it, and the
    detection research shows its presence says nothing about authorship.
    """
    from nabokov.checks import DEFAULT_CODES

    assert "NB317" in DEFAULT_CODES
    assert "NB519" not in DEFAULT_CODES


def test_scans_the_original_text_including_code(analyze):
    """Blanking would hide the case that does the most damage.

    A zero-width space pasted into a code fence is a syntax error nobody can see.
    """
    text = f"Run it:\n\n```python\nx = fo{ZWSP}o(1)\n```\n"
    assert _found(analyze(text, is_markdown=True, name="doc.md"))


def test_nb519_no_longer_reports_characters(analyze):
    """They moved. A duplicate would report the same span twice."""
    from nabokov.config import Config

    ai = Config(extend_select=("NB5",))
    result = analyze(f"The plan{ZWSP} works fine.", config=ai)
    assert not _found(result, "NB519")
    assert _found(result)
