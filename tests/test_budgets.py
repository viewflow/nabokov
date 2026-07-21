"""Density-based severity (style budgets), same-span dedup, and the ESSAY target.

The style checks (NB301 adverbs, NB302 passive, NB303 qualifiers) flag *signals*,
not defects — the defect is overuse. Within the target's per-1000-word budget the
findings stay advisory (info); over it they escalate to warnings. Calibrated so the
Paul Graham corpus produces no style-layer warnings under NORMAL.
"""

from __future__ import annotations

import pytest

from nabokov.config import Config, ConfigError, _coerce

ADVERB_STUFFED = (
    "He quickly and quietly walked slowly to the badly built door. "
    "She happily sang loudly and proudly, dancing wildly and freely. "
    "They eagerly waited patiently, breathing heavily and deeply."
)


def _sevs(result, code):
    return [i.severity for i in result.issues if i.code == code]


# --- budget demotion ---------------------------------------------------------


def test_sparse_adverb_is_info(analyze):
    result = analyze("He walked to the door. She sang. They waited quietly for the answer.")
    assert _sevs(result, "NB301") == ["info"]


def test_adverb_overuse_escalates_to_warning(analyze):
    result = analyze(ADVERB_STUFFED)
    sevs = _sevs(result, "NB301")
    assert len(sevs) > 2
    assert set(sevs) == {"warning"}


def test_sparse_qualifier_and_passive_are_info(analyze):
    result = analyze(
        "I think the plan is fine. The cake was eaten by the dog. We should go home now."
    )
    assert _sevs(result, "NB303") == ["info"]
    assert _sevs(result, "NB302") == ["info"]


def test_config_budget_override_relaxes(analyze):
    result = analyze(ADVERB_STUFFED, config=Config(budgets={"NB301": 1000.0}))
    assert set(_sevs(result, "NB301")) == {"info"}


def test_short_text_grace_never_escalates_two_findings(analyze):
    # Two adverbs in a tiny snippet: over any per-1000w rate, but under the flat grace of 2.
    result = analyze("He ran quickly to the well.", config=Config(budgets={"NB301": 0}))
    sevs = _sevs(result, "NB301")
    assert sevs and set(sevs) == {"info"}


# --- same-span dedup ---------------------------------------------------------


def test_epistemic_adverb_reports_qualifier_only(analyze):
    result = analyze("We will probably win the game against them tomorrow.")
    assert _sevs(result, "NB303")
    assert not _sevs(result, "NB301")


def test_intensifier_suppresses_adverb_under_ai(analyze):
    result = analyze("The fix was really simple to ship.", config=Config(extend_select=("NB5",)))
    assert _sevs(result, "NB510")
    assert not _sevs(result, "NB301")


def test_manner_adverb_still_reported(analyze):
    result = analyze("He quickly ran to the door.")
    issue = next(i for i in result.issues if i.code == "NB301")
    assert "stronger verb" in issue.message


def test_sentence_adverb_message_says_cut(analyze):
    # "merely" modifies a noun predicate, not a verb — no "stronger verb" advice.
    result = analyze("The word is merely a label for the idea.")
    issue = next((i for i in result.issues if i.code == "NB301"), None)
    assert issue is not None
    assert "cutting" in issue.message


# --- NB201 severity ----------------------------------------------------------


def test_very_hard_sentence_is_warning_not_error(analyze):
    text = (
        "The multifaceted organizational restructuring initiative, notwithstanding "
        "considerable stakeholder apprehension regarding implementation complexities, "
        "fundamentally transformed interdepartmental communication paradigms."
    )
    result = analyze(text)
    issue = next(i for i in result.issues if i.code == "NB201")
    assert issue.severity == "warning"


# --- ESSAY target ------------------------------------------------------------


def test_essay_target_accepted():
    assert Config(target="ESSAY").target == "ESSAY"


def test_essay_target_tolerates_longer_sentences(analyze):
    # Grade ~13: flagged as hard under NORMAL, clean under ESSAY (thresholds 14/18).
    text = (
        "Great writers earn their long sentences by keeping every clause pulling "
        "the same way, and readers follow them happily across the page."
    )
    normal = analyze(text, config=Config(target="NORMAL"))
    essay = analyze(text, config=Config(target="ESSAY"))
    assert any(i.code in ("NB201", "NB202") for i in normal.issues)
    assert not any(i.code in ("NB201", "NB202") for i in essay.issues)


# --- quoted material ---------------------------------------------------------

AI = Config(extend_select=("NB5",))


def test_blockquote_findings_suppressed(analyze):
    md = (
        "Ginsberg wrote about the city.\n\n"
        "> Moloch! Solitude! Filth! Ugliness!\n"
        "> Visions! Omens! Hallucinations! Miracles!\n\n"
        "That is the poem.\n"
    )
    result = analyze(md, is_markdown=True, config=AI)
    assert not any(i.code == "NB507" for i in result.issues)


def test_unquoted_staccato_still_flagged(analyze):
    result = analyze("Moloch! Solitude! Filth! Ugliness!", config=AI)
    assert any(i.code == "NB507" for i in result.issues)


def test_long_quoted_span_suppresses_findings(analyze):
    text = (
        "He said “I think we should probably wait and see what happens to "
        "everyone next year” and left the room."
    )
    result = analyze(text)
    assert not any(i.code == "NB303" for i in result.issues)


def test_quoted_phrase_is_mention_not_usage(analyze):
    # a multi-word quoted phrase is a mention — the author isn't hedging
    result = analyze('The phrase "I think" weakens the whole statement a lot.')
    assert not any(i.code == "NB303" for i in result.issues)


def test_single_quoted_word_keeps_findings(analyze):
    # one quoted word is below the mention threshold; the hedge outside is real
    result = analyze('Maybe the word "delve" belongs in the final draft after all.')
    assert any(i.code == "NB303" and i.text.lower() == "maybe" for i in result.issues)


def test_curly_single_quote_mention_suppressed(analyze):
    result = analyze(
        "He mocked phrases like ‘objective considerations of contemporary "
        "phenomena’ throughout the whole essay."
    )
    assert not any(i.code == "NB401" for i in result.issues)


def test_apostrophes_do_not_form_mention_regions(analyze):
    # don’t/it’s use the same char as the closing curly single quote
    result = analyze("I think we don’t need it’s extra hedging in Bob’s draft.")
    assert any(i.code == "NB303" and i.text.lower() == "i think" for i in result.issues)


# --- puffery topical demotion ------------------------------------------------


def test_puffery_topical_lemma_demoted(analyze):
    text = (
        "Everyone tries to optimize the system for speed. When you optimize one "
        "part, another part degrades. Optimizing is the whole game here."
    )
    result = analyze(text, config=AI)
    found = [i for i in result.issues if i.code == "NB502"]
    assert len(found) == 3
    assert all(i.severity == "info" for i in found)
    assert "topic vocabulary" in found[0].message


def test_puffery_single_use_stays_warning(analyze):
    result = analyze("We delve into the details of the plan.", config=AI)
    issue = next(i for i in result.issues if i.code == "NB502")
    assert issue.severity == "warning"


# --- NB401 in the budget system ----------------------------------------------


def test_sparse_wordy_phrase_is_info(analyze):
    result = analyze("We should utilize the new tool when it finally arrives.")
    assert _sevs(result, "NB401") == ["info"]


# --- NB202 document-aware demotion -------------------------------------------

HARD_SENTENCE = (
    "Great writers earn their long sentences by keeping every clause pulling "
    "the same way, and readers follow them happily across the page."
)


def test_hard_sentence_info_when_document_reads_normal(analyze):
    text = HARD_SENTENCE + " We like that. It works. Read it twice. Keep it short. Go now."
    result = analyze(text)
    assert result.stats.readability == "normal"
    assert _sevs(result, "NB202") == ["info"]


def test_hard_sentence_warns_when_document_is_hard(analyze):
    result = analyze(" ".join([HARD_SENTENCE] * 3))
    assert result.stats.readability != "normal"
    assert set(_sevs(result, "NB202")) == {"warning"}


# --- "just" polysemy gate ----------------------------------------------------


def test_restrictive_just_not_flagged(analyze):
    # "just" = only, before a numeral/noun phrase
    result = analyze("Even if a book had just one useful insight, it was worth it.")
    assert not any(i.code == "NB303" for i in result.issues)


def test_imperative_just_not_flagged(analyze):
    result = analyze("Just tell me what to do next time.")
    assert not any(i.code == "NB303" for i in result.issues)


def test_temporal_just_not_flagged(analyze):
    # "just" = recently, between auxiliary and participle
    result = analyze("I had just read the book before our meeting started.")
    assert not any(i.code == "NB303" for i in result.issues)


def test_minimizer_just_still_flagged(analyze):
    # after a copula "just" hedges the claim (= merely)
    result = analyze("It is just a way to communicate the idea to them.")
    assert any(i.code == "NB303" and i.text.lower() == "just" for i in result.issues)


# --- NB507 verbless gate -----------------------------------------------------


def test_staccato_with_verbs_not_flagged(analyze):
    result = analyze("Stop the orchestra. Solo that motif. Repeat it.", config=AI)
    assert not any(i.code == "NB507" for i in result.issues)


def test_verbless_fragments_still_flagged(analyze):
    result = analyze("The jokes. The wins. The team.", config=AI)
    found = [i for i in result.issues if i.code == "NB507"]
    # advisory: the human anaphora and the AI listicle are formally identical
    assert found and all(i.severity == "info" for i in found)


# --- tight lists are not one mega-sentence -----------------------------------

TIGHT_LIST = (
    "The work it takes to present the idea clearly is rewarded, because it is:\n"
    "- much easier to communicate to all the other people\n"
    "- much easier to explain to everyone else in the room\n"
    "- much easier to remember over a very long time\n"
)


def test_tight_list_plaintext_not_glued(analyze):
    result = analyze(TIGHT_LIST)
    assert not any(i.code == "NB201" for i in result.issues)
    assert result.stats.sentences >= 4


def test_tight_list_markdown_not_glued(analyze):
    result = analyze(TIGHT_LIST, is_markdown=True)
    assert not any(i.code == "NB201" for i in result.issues)
    assert result.stats.sentences >= 4


# --- line-oriented documents -------------------------------------------------

LINE_ORIENTED = (
    "The first rule matters a lot to everyone in this room.\n"
    "The second rule is much more subtle than it first looks.\n"
    "The third rule takes a whole career to learn properly.\n"
    "The fourth rule is the one that nobody wants to hear.\n"
    "#1 — Remain objective and realistic about your expectations\n"
    "Parents have wrestled with this hard challenge for many generations, "
    "and likely always will, wanting only the very best.\n"
)

HARD_WRAPPED = (
    "The lectures were composed for a course on drama that he gave at\n"
    "Stanford during the summer, and except for some brief guest\n"
    "appearances this was his first engagement at an American university.\n"
    "The course also included a discussion of some American plays that\n"
    "he admired a great deal, and the students responded to the material\n"
    "with an enthusiasm that surprised him throughout that whole summer.\n"
)


def test_heading_not_glued_in_line_oriented_doc(analyze):
    result = analyze(LINE_ORIENTED)
    assert not any(i.code == "NB201" for i in result.issues)
    assert result.stats.sentences >= 6


def test_hard_wrapped_prose_not_split_at_newlines(analyze):
    result = analyze(HARD_WRAPPED)
    assert result.stats.sentences == 2


# --- mostly-quoted hard sentences --------------------------------------------


def test_hard_sentence_mostly_quote_demoted(analyze):
    text = (
        "He wrote: “The multifaceted organizational restructuring initiative "
        "fundamentally transformed interdepartmental communication paradigms "
        "across administrative divisions everywhere.”"
    )
    result = analyze(text)
    hard = [i for i in result.issues if i.code in ("NB201", "NB202")]
    assert hard and all(i.severity == "info" for i in hard)


# --- NB502 short-document threshold ------------------------------------------


def test_puffery_twice_in_short_doc_is_topical(analyze):
    text = "We empower the whole team. They feel empowered every single day."
    result = analyze(text, config=AI)
    found = [i for i in result.issues if i.code == "NB502"]
    assert len(found) == 2
    assert all(i.severity == "info" for i in found)


# --- config validation -------------------------------------------------------


def test_budgets_unknown_code_rejected():
    with pytest.raises(ConfigError, match="unknown code"):
        _coerce({"budgets": {"NB999": 5}})


def test_budgets_negative_rate_rejected():
    with pytest.raises(ConfigError, match="non-negative"):
        _coerce({"budgets": {"NB301": -1}})


def test_budgets_non_table_rejected():
    with pytest.raises(ConfigError, match="table"):
        _coerce({"budgets": 5})


def test_budgets_lowercase_code_normalized():
    assert _coerce({"budgets": {"nb301": 20}})["budgets"] == {"NB301": 20.0}
