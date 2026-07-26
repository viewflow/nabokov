"""Fix suggestions: the applicability tiers, and the invariant tying them to data.

The tiers are a promise to consumers — a REPLACE suggestion substitutes for the
flagged span verbatim, a REWRITE one does not. These tests pin the promise,
because the consumers act on it: the cost of breaking it is an agent pasting a
tense error into someone's draft, or the bot proposing an edit that inverts a
claim. nabokov never applies a fix itself — the tier is how it hands that
decision over.
"""

from __future__ import annotations

import pytest

from nabokov.config import Config
from nabokov.issue import Applicability

AI = Config(extend_select=("NB5",))


def _one(result, code):
    found = [i for i in result.issues if i.code == code]
    assert found, f"expected {code}, got {sorted({i.code for i in result.issues})}"
    return found[0]


# --- the invariant -----------------------------------------------------------


def test_a_suggestion_is_never_advisory(analyze):
    """ADVISORY means "no fix exists", so it must never carry one, and vice versa.

    Checked over a text that trips a wide spread of rules rather than one rule at
    a time — a new rule that sets one field and forgets the other fails here.
    """
    text = (
        "Moreover, the platform leverages a robust tapestry of very innovative\n"
        "paradigms. The report was written by the whole team in order to reach\n"
        "an agreement. There are the the cases that could potentially be very\n"
        "unique, and the team is cross-functional.\n"
    )
    result = analyze(text, config=AI)
    assert result.issues
    for issue in result.issues:
        if issue.applicability is Applicability.ADVISORY:
            assert issue.suggestion is None, f"{issue.code} is advisory but suggests"
        else:
            assert issue.suggestion is not None, f"{issue.code} has a tier but no fix"


def test_has_fix_tracks_the_suggestion(analyze):
    result = analyze("We came to an agreement.")
    issue = _one(result, "NB304")
    assert issue.has_fix


# --- REPLACE: the suggestion substitutes for the span ------------------------


@pytest.mark.parametrize(
    ("text", "code", "expected"),
    [
        ("We should use it in order to win.", "NB401", "to"),
        ("Paris in the the spring is lovely.", "NB306", "the"),
        ("These are very unique cases here.", "NB307", "unique"),
        ("The team is cross-functional now.", "NB515", "cross functional"),
    ],
)
def test_replace_suggestions_are_substitutions(analyze, text, code, expected):
    issue = _one(analyze(text, config=AI), code)
    assert issue.applicability is Applicability.REPLACE
    assert issue.suggestion == expected


def test_replace_suggestion_actually_substitutes(analyze):
    """Splice a REPLACE fix into the source and check the result reads right.

    Markup blanking preserves length, so an issue's offsets address the real
    file. That is what makes a REPLACE suggestion usable by a caller: splice it
    in at the span and the result reads correctly.
    """
    text = "We should use it in order to win."
    source_result = analyze(text, config=AI)
    issue = _one(source_result, "NB401")
    start = source_result.source.offset(issue.line, issue.col)
    end = source_result.source.offset(issue.end_line, issue.end_col)
    patched = text[:start] + issue.suggestion + text[end:]
    assert patched == "We should use it to win."


def test_empty_replace_suggestion_means_delete(analyze):
    issue = _one(analyze("This is very fast today.", config=AI), "NB510")
    assert issue.applicability is Applicability.REPLACE
    assert issue.suggestion == ""


# --- case and position: where a mechanical fix stops being mechanical --------


def test_sentence_initial_replacement_keeps_the_capital(analyze):
    issue = _one(analyze("Despite the fact that sales fell, we held on."), "NB401")
    assert issue.suggestion == "Although"


def test_sentence_initial_deletion_drops_to_rewrite(analyze):
    """ "Moreover, ..." cannot just be cut — the comma and the capital remain."""
    issue = _one(analyze("Moreover, the team shipped it.", config=AI), "NB505")
    assert issue.applicability is Applicability.REWRITE


def test_comma_bracketed_hedge_drops_to_rewrite(analyze):
    issue = _one(analyze("We should, in my opinion, wait for it.", config=AI), "NB303")
    assert issue.applicability is Applicability.REWRITE


def test_mid_sentence_hedge_is_a_clean_deletion(analyze):
    issue = _one(analyze("We should probably wait for the review.", config=AI), "NB303")
    assert issue.applicability is Applicability.REPLACE
    assert issue.suggestion == ""


# --- NB303: the negated hedges must never be offered as a deletion -----------


def test_negated_hedge_is_guidance_not_a_cut(analyze):
    """Cutting "I don't think" out of a claim inverts it, so it is never a cut."""
    issue = _one(analyze("I don't think we should ship it today.", config=AI), "NB303")
    assert issue.applicability is Applicability.REWRITE
    assert "negation" in issue.suggestion


# --- NB502: lemma matching vs. the uninflected alternatives ------------------


def test_base_form_puffery_is_a_substitution(analyze):
    issue = _one(analyze("We delve into the data every week.", config=AI), "NB502")
    assert issue.applicability is Applicability.REPLACE
    assert issue.suggestion == "examine, dig into"


def test_inflected_puffery_drops_to_rewrite(analyze):
    """ "delved" matches the lemma, but "examine" is the wrong tense to splice in."""
    issue = _one(analyze("She delved into the data last week.", config=AI), "NB502")
    assert issue.applicability is Applicability.REWRITE


def test_every_puffery_alternative_names_a_flagged_term():
    """The map may not widen what gets flagged — it only annotates it."""
    from nabokov.data_loader import ai_writing

    data = ai_writing()
    assert set(data["puffery_alternatives"]) <= set(data["puffery"])


def test_qualifier_groups_cover_every_matched_phrase():
    from nabokov.data_loader import qualifier_fixes, qualifiers

    groups = qualifier_fixes()
    combined = set(groups["cut"]) | set(groups["replace"]) | set(groups["rewrite"])
    assert combined == set(qualifiers())


# --- NB302: the active-voice draft -------------------------------------------


def test_passive_with_agent_drafts_the_active_voice(analyze):
    issue = _one(analyze("The report was written by the whole team."), "NB302")
    assert issue.applicability is Applicability.REWRITE
    assert issue.suggestion == "The whole team wrote the report"


def test_regular_verb_reuses_the_participle(analyze):
    issue = _one(analyze("The release was celebrated by everyone."), "NB302")
    assert issue.suggestion == "Everyone celebrated the release"


def test_proper_noun_agent_keeps_its_capital(analyze):
    issue = _one(analyze("The bug was found by Alice last night."), "NB302")
    assert issue.suggestion.startswith("Alice found")


def test_agentless_passive_offers_nothing(analyze):
    """No "by" phrase means the actor is absent; no rearrangement invents one."""
    issue = _one(analyze("Mistakes were made on the project."), "NB302")
    assert issue.suggestion is None
    assert issue.applicability is Applicability.ADVISORY


def test_present_tense_passive_offers_nothing(analyze):
    """Tense lives in the auxiliary, and the map only yields past forms."""
    issue = _one(analyze("Bugs are found by Alice every single week."), "NB302")
    assert issue.suggestion is None


def test_relative_clause_passive_offers_nothing(analyze):
    """The thing acted on is the antecedent, outside the clause."""
    result = analyze("These are the synergies which were unlocked by the team.")
    for issue in [i for i in result.issues if i.code == "NB302"]:
        assert issue.suggestion is None
