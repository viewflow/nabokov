"""NB308 — condescending ease-claims and presuppositions.

Every word this rule matches has an ordinary correct sense, so the must-not-fire
cases carry more weight here than the positives. A rule that flags "the function
simply returns null" is worse than no rule at all.
"""

from __future__ import annotations

import pytest

from nabokov.config import Config
from nabokov.issue import Applicability, Severity

AI = Config(extend_select=("NB5",))


def _found(result, code):
    return [i for i in result.issues if i.code == code]


# --- fires: the word is aimed at the reader ----------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Simply run the migration and you are done.",
        "You can easily add a plugin to the pipeline.",
        "Obviously, you need Docker installed first.",
        "Of course the daemon must be running.",
        "Installation is easy.",
        "It is trivial to add a new backend.",
        "Merely restart the service to pick it up.",
        "As you know, the token expires after an hour.",
    ],
)
def test_condescension_flagged(analyze, text):
    assert _found(analyze(text), "NB308"), text


# --- must not fire: the ordinary sense ---------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # "simply" = merely, describing behavior rather than effort
        "The function simply returns null when the cache misses.",
        # manner adverb, not a presupposition
        "The error message clearly states which field failed.",
        # attributive: describes a thing, not the reader's work
        "The API returns a simple object with two fields.",
        # fixed discourse marker
        "Simply put, the parser is a state machine.",
        # the subject is the software, not the reader
        "It handles ten thousand requests easily under load.",
        # attributive again
        "The migration is a straightforward mapping of columns.",
        # third-person description of a user, not an instruction
        "The operator simply confirms the prompt and the job starts.",
    ],
)
def test_ordinary_sense_not_flagged(analyze, text):
    assert not _found(analyze(text), "NB308"), text


# --- fix tiers ---------------------------------------------------------------


def test_mid_sentence_adverb_is_a_clean_deletion(analyze):
    issue = _found(analyze("You can easily add a plugin to the pipeline."), "NB308")[0]
    assert issue.applicability is Applicability.REPLACE
    assert issue.suggestion == ""


def test_sentence_initial_adverb_drops_to_rewrite(analyze):
    """Cutting "Simply" takes the sentence's capital with it."""
    issue = _found(analyze("Simply run the migration now."), "NB308")[0]
    assert issue.applicability is Applicability.REWRITE


def test_ease_adjective_is_never_a_deletion(analyze):
    """"Installation is easy" minus "easy" is "Installation is" — a rewrite."""
    issue = _found(analyze("Installation is easy."), "NB308")[0]
    assert issue.applicability is Applicability.REWRITE
    assert "what the task actually takes" in issue.suggestion


def test_severity_is_warning(analyze):
    """Not budgeted: one "simply" is one too many for a reader who is stuck."""
    issue = _found(analyze("Simply run the migration now."), "NB308")[0]
    assert issue.severity is Severity.WARNING


# --- span precedence over NB301 / NB510 --------------------------------------


def test_wins_over_the_intensifier_rule(analyze):
    """"simply" is on NB510's list too; the instructional reading is more specific."""
    result = analyze("Simply run the migration now.", config=AI)
    assert _found(result, "NB308")
    assert not _found(result, "NB510")


def test_wins_over_the_adverb_rule(analyze):
    result = analyze("You can easily add a plugin to the pipeline.")
    assert _found(result, "NB308")
    assert not _found(result, "NB301")


def test_intensifier_rule_still_fires_where_this_one_declines(analyze):
    """Precedence must not blind NB510 to the descriptive sense."""
    result = analyze("The function simply returns null here.", config=AI)
    assert not _found(result, "NB308")
    assert _found(result, "NB510")


# --- genre suppression -------------------------------------------------------


@pytest.mark.parametrize("target", ["ESSAY", "SOCIAL"])
def test_off_where_the_writer_owns_the_voice(analyze, target):
    """An essayist's "Obviously" is a rhetorical move, not condescension."""
    result = analyze("Obviously, you need Docker installed.", config=Config(target=target))
    assert not _found(result, "NB308")


def test_on_for_technical(analyze):
    result = analyze("Obviously, you need Docker installed.", config=Config(target="TECHNICAL"))
    assert _found(result, "NB308")
