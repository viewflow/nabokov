"""Per-rule detection tests (require the spaCy pipeline)."""

from __future__ import annotations

from nabokov.config import Config


def _issue(result, code):
    return next((i for i in result.issues if i.code == code), None)


# --- passive voice (NB302) ---------------------------------------------------


def test_passive_flagged(codes):
    assert "NB302" in codes("The cake was eaten by the dog at the party.")


def test_active_not_flagged(codes):
    assert "NB302" not in codes("The dog ate the cake at the party.")


def test_passive_span_includes_participle(analyze):
    issue = _issue(analyze("The house was built last year."), "NB302")
    assert issue is not None
    assert "built" in issue.text


# --- adverbs (NB301) ---------------------------------------------------------


def test_adverb_flagged(analyze):
    issue = _issue(analyze("He quickly ran to the door."), "NB301")
    assert issue is not None
    assert issue.text == "quickly"


def test_adverb_exception_not_flagged(codes):
    # "only" is in the -ly exception list
    assert "NB301" not in codes("I only wanted to help you today.")


# --- complex phrases (NB401) -------------------------------------------------


def test_complex_phrase_with_suggestion(analyze):
    issue = _issue(analyze("We should utilize the new tool."), "NB401")
    assert issue is not None
    assert "use" in (issue.suggestion or "")


def test_multiword_complex_phrase(codes):
    assert "NB401" in codes("He did it in order to win the prize.")


# --- qualifiers (NB303) ------------------------------------------------------


def test_qualifier_flagged(codes):
    assert "NB303" in codes("I think we should probably go now.")


# --- sentences (NB201/NB202) -------------------------------------------------


def test_short_sentence_not_flagged(codes):
    assert "NB201" not in codes("The cat sat.")
    assert "NB202" not in codes("The cat sat.")


def test_very_long_sentence_flagged(codes):
    text = (
        "The comprehensive quarterly organizational restructuring initiative "
        "necessitated substantial reallocation of departmental resources across "
        "numerous interdependent operational divisions throughout the entire "
        "multinational corporate enterprise structure."
    )
    result_codes = codes(text)
    assert "NB201" in result_codes or "NB202" in result_codes


# --- suppression + selection -------------------------------------------------


def test_noqa_suppresses_code(codes):
    text = "He quickly ran away.  <!-- nabokov: ignore NB301 -->"
    assert "NB301" not in codes(text)


def test_noqa_blanket_suppression(codes):
    text = "He quickly ran and it was written by him.  # nabokov: ignore"
    assert codes(text) == []


def test_select_limits_output(codes):
    text = "The cake was quickly eaten by the dog in order to celebrate."
    only_passive = codes(text, config=Config(select=("NB302",)))
    assert set(only_passive) == {"NB302"}


def test_max_grade_emits_nb101(analyze):
    text = (
        "The comprehensive quarterly organizational restructuring initiative "
        "necessitated substantial reallocation of departmental resources across "
        "numerous interdependent operational divisions."
    )
    result = analyze(text, config=Config(max_grade=5))
    assert any(i.code == "NB101" for i in result.issues)
