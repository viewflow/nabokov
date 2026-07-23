"""NB304 nominalizations, NB305 dummy subjects, NB203 periodic sentences,
NB517 vocab clusters, NB601 low concreteness."""

from __future__ import annotations

from nabokov.config import Config

AI = Config(extend_select=("NB5",))


def _found(result, code):
    return [i for i in result.issues if i.code == code]


# --- NB304 nominalization ----------------------------------------------------


def test_light_verb_nominalization_flagged(analyze):
    result = analyze("The committee came to an agreement that we should wait.")
    issue = _found(result, "NB304")[0]
    assert "agree" in issue.message
    assert "came" in issue.text and "agreement" in issue.text


def test_nominalization_with_adjective_flagged(analyze):
    result = analyze("We conducted a thorough investigation of the incident.")
    issue = _found(result, "NB304")[0]
    assert "investigate" in issue.message


def test_plain_verb_not_flagged(analyze):
    result = analyze("The committee agreed that the consultants should study it.")
    assert not _found(result, "NB304")


def test_standalone_nominalization_not_flagged(analyze):
    # the noun without a light verb is legitimate usage
    result = analyze("Their agreement surprised everyone at the table.")
    assert not _found(result, "NB304")


# --- NB305 dummy subject -----------------------------------------------------


def test_there_are_flagged(analyze):
    result = analyze("There are many great skiing resorts in Colorado.")
    issue = _found(result, "NB305")[0]
    assert "There are" in issue.text


def test_locative_there_not_flagged(analyze):
    result = analyze("We drove for hours and finally got there before dark.")
    assert not _found(result, "NB305")


# --- NB203 periodic sentence -------------------------------------------------


def test_buried_main_clause_flagged(analyze):
    result = analyze(
        "Although the committee, having reviewed every submission from all twelve "
        "regional offices over the course of the preceding fiscal year and weighed "
        "each objection carefully, ultimately approved the plan."
    )
    found = _found(result, "NB203")
    assert found and found[0].severity == "info"


def test_front_loaded_sentence_not_flagged(analyze):
    result = analyze(
        "The committee approved the plan after reviewing every submission from "
        "all twelve regional offices over the course of the preceding fiscal year."
    )
    assert not _found(result, "NB203")


# --- NB517 vocab cluster -----------------------------------------------------


def test_clustered_generic_praise_flagged(analyze):
    result = analyze(
        "Our significant and innovative platform delivers effective results.",
        config=AI,
    )
    found = _found(result, "NB517")
    assert len(found) >= 2
    assert all(i.severity == "info" for i in found)


def test_single_generic_word_not_flagged(analyze):
    result = analyze("The results were significant for the whole field.", config=AI)
    assert not _found(result, "NB517")


# --- NB518 adjective triads --------------------------------------------------


def test_repeated_adjective_triads_flagged(analyze):
    text = (
        "The plan was innovative, transformative, and groundbreaking. "
        "The team felt confident, prepared, and unstoppable after the launch."
    )
    result = analyze(text, config=AI)
    found = _found(result, "NB518")
    assert len(found) == 2
    assert all(i.severity == "info" for i in found)


def test_single_adjective_triad_not_flagged(analyze):
    result = analyze(
        "The plan was clear, focused, and practical. Everyone approved it quickly.",
        config=AI,
    )
    assert not _found(result, "NB518")


def test_adjective_pair_not_flagged(analyze):
    result = analyze(
        "The plan was clear and practical. The team was calm and ready. "
        "The launch was quick and clean.",
        config=AI,
    )
    assert not _found(result, "NB518")


# --- article-era hedges and clichés ------------------------------------------


def test_impersonal_hedge_flagged(analyze):
    result = analyze("It could be argued that the plan needs far more time.")
    assert _found(result, "NB303")


def test_intersection_cliche_flagged(analyze):
    result = analyze(
        "The framework sits at the intersection of design and complexity science.",
        config=AI,
    )
    assert _found(result, "NB503")


# --- NB519 AI artifacts ------------------------------------------------------


def test_citation_markup_flagged(analyze):
    result = analyze("The results were strong citeturn0search0 across all runs.", config=AI)
    issue = _found(result, "NB519")[0]
    assert issue.severity == "warning"
    assert "citeturn0search0" in issue.text


def test_ai_utm_parameter_flagged(analyze):
    result = analyze(
        "See https://example.com/post?utm_source=chatgpt.com for details.",
        config=AI,
        is_markdown=True,
    )
    assert _found(result, "NB519")


def test_placeholder_flagged(analyze):
    result = analyze("Best regards, [Your Name Here] and the whole team.", config=AI)
    assert _found(result, "NB519")


def test_cutoff_disclaimer_flagged(analyze):
    result = analyze("As of my last update, the library supported three backends.", config=AI)
    assert _found(result, "NB519")


def test_ordinary_brackets_not_flagged(analyze):
    result = analyze("The results [see Table 2] were consistent with the model.", config=AI)
    assert not _found(result, "NB519")


def test_gemini_span_markers_flagged(analyze):
    result = analyze(
        "The market grew by 40% last year [span_1][start_span] according to reports.",
        config=AI,
    )
    assert len(_found(result, "NB519")) >= 2


def test_perplexity_upload_marker_flagged(analyze):
    result = analyze("The chart (ppl-ai-file-upload) shows the trend clearly.", config=AI)
    assert _found(result, "NB519")


def test_invisible_characters_flagged(analyze):
    # zero-width space and word joiner ride along in AI-tool copy-paste
    result = analyze("The plan​ works fine and ships⁠ this week.", config=AI)
    assert len(_found(result, "NB519")) == 2


def test_homoglyph_swap_flagged(analyze):
    # Cyrillic е sandwiched inside a Latin word is a laundering swap
    result = analyze("Our dеtection rate improved a lot this quarter.", config=AI)
    issues = _found(result, "NB519")
    assert issues and "homoglyph" in issues[0].message


def test_legit_mixed_language_not_flagged(analyze):
    # whole-script words, Cyrillic suffix on a Latin brand, and unit prefixes
    # are ordinary multilingual text, not homoglyph swaps
    result = analyze(
        "Мы пишем в Slackе каждый день. The delay was 5 μs overall.",
        config=AI,
    )
    assert not _found(result, "NB519")


# --- chat-residue filler --------------------------------------------------


def test_certainly_exclamation_flagged(analyze):
    result = analyze("Certainly! Here is the revised paragraph you asked about.", config=AI)
    assert _found(result, "NB504")


def test_plain_certainly_not_flagged(analyze):
    result = analyze("The plan will certainly need another month of work.", config=AI)
    assert not _found(result, "NB504")


# --- circumlocution harvest ---------------------------------------------


def test_despite_the_fact_that_flagged(analyze):
    result = analyze("Despite the fact that sales fell, the team stayed calm.")
    issue = _found(result, "NB401")[0]
    assert "although" in issue.message


# --- NB520 hedge stacks ------------------------------------------------------


def test_hedge_stack_flagged(analyze):
    result = analyze("The change could potentially create a new failure mode.", config=AI)
    issue = _found(result, "NB520")[0]
    assert "could potentially" in issue.text


def test_single_modal_not_flagged(analyze):
    result = analyze("The change could create a new failure mode.", config=AI)
    assert not _found(result, "NB520")


# --- NB501 split-sentence contrast -------------------------------------------


def test_split_sentence_negation_flagged(analyze):
    result = analyze("The headline isn't the speed. The real story is the price.", config=AI)
    assert _found(result, "NB501")


def test_multi_negation_countdown_flagged(analyze):
    result = analyze("It's not the price. It's not the features. It's the trust.", config=AI)
    assert _found(result, "NB501")


# --- NB516 label-period ------------------------------------------------------


def test_bold_label_period_flagged(analyze):
    md = "- **Intros.** Years of conferences and operator network.\n"
    result = analyze(md, is_markdown=True, config=AI)
    assert _found(result, "NB516")


def test_bold_label_colon_not_flagged(analyze):
    md = "- **Intros:** years of conferences and operator network.\n"
    result = analyze(md, is_markdown=True, config=AI)
    assert not _found(result, "NB516")


# --- SOCIAL / EMAIL targets --------------------------------------------------


def test_social_target_drops_staccato_tell(analyze):
    text = "The jokes. The wins. The team."
    normal = analyze(text, config=Config(extend_select=("NB5",)))
    social = analyze(text, config=Config(target="SOCIAL", extend_select=("NB5",)))
    assert any(i.code == "NB507" for i in normal.issues)
    assert not any(i.code == "NB507" for i in social.issues)


def test_email_target_accepted():
    assert Config(target="EMAIL").target == "EMAIL"


# --- NB601 low concreteness --------------------------------------------------

SLOP = (
    "The strategic integration of innovative paradigms requires the optimization "
    "of dynamic synergies across organizational frameworks, and the facilitation "
    "of transformational alignment remains a considerable component of the "
    "implementation of governance. The realization of value necessitates the "
    "prioritization of capabilities and the utilization of resources across all "
    "functions of the enterprise."
)


def test_abstract_paragraph_flagged(analyze):
    result = analyze(SLOP)
    found = _found(result, "NB601")
    assert found and found[0].severity == "info"
    assert "concreteness" in found[0].message


def test_concrete_paragraph_not_flagged(analyze):
    result = analyze(
        "The dog dragged the sled across the frozen lake while the children threw "
        "snowballs at the fence. Their mother carried hot pizza and lemonade from "
        "the car, and the smell of woodsmoke drifted over the garden from the "
        "neighbor's stone chimney."
    )
    assert not _found(result, "NB601")


def test_short_snippet_never_scored(analyze):
    # under the minimum rated-token sample, no judgment is made
    result = analyze("The belief in progress requires patience.")
    assert not _found(result, "NB601")
