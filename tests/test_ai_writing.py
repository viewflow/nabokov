"""Tests for the NB5xx 'signs of AI writing' rules (opt-in)."""

from __future__ import annotations

from nabokov.config import Config

AI = Config(select=("NB5",))


def _codes(analyze, text):
    return [i.code for i in analyze(text, config=AI).issues]


def test_off_by_default(analyze):
    # a passage full of AI tells produces no NB5xx findings in the default config
    text = "Let me delve into this rich tapestry. Moreover, it plays a crucial role."
    assert not any(i.code.startswith("NB5") for i in analyze(text).issues)


def test_puffery(analyze):
    codes = _codes(analyze, "We delve into a robust and seamless landscape.")
    assert codes.count("NB502") >= 3  # delve, robust, seamless, landscape


def test_puffery_lemma_inflection(analyze):
    # lemma matching catches inflected forms
    assert "NB502" in _codes(analyze, "The team is delving into the details.")


def test_editorializing_phrase(analyze):
    assert "NB503" in _codes(analyze, "This site plays a crucial role in the region.")


def test_negation_contrast_its_not(analyze):
    assert "NB501" in _codes(analyze, "It's not a bug, it's a feature of the design.")


def test_negation_contrast_not_only_but(analyze):
    assert "NB501" in _codes(analyze, "We offer not only speed but also real safety.")


def test_negation_contrast_isnt_just(analyze):
    assert "NB501" in _codes(analyze, "This isn't just fast, it's genuinely transformative.")


def test_filler_and_sycophancy(analyze):
    codes = _codes(analyze, "Great question! I hope this helps you a lot.")
    assert codes.count("NB504") >= 2


def test_transition(analyze):
    assert "NB505" in _codes(analyze, "Moreover, the results improved across the board.")


def test_formal_marker_is_transition_not_filler(analyze):
    # "In conclusion" is centuries-old formal prose, not chatbot filler — advisory only
    codes = _codes(analyze, "In conclusion, the plan works well for everyone involved.")
    assert "NB505" in codes
    assert "NB504" not in codes


def test_em_dash_overuse_threshold(analyze):
    # two em dashes: below threshold, not flagged
    assert "NB506" not in _codes(analyze, "A — B and then — C happened.")
    # three or more: flagged
    assert "NB506" in _codes(analyze, "A — B — C — D all happened at once.")


def test_select_nb5_excludes_core_checks(analyze):
    text = "It's not X, it's Y, and he quickly ran away in order to hide."
    codes = _codes(analyze, text)
    assert "NB501" in codes
    assert "NB301" not in codes  # adverb (core check) not selected
    assert "NB401" not in codes  # complex phrase (core check) not selected


def test_expanded_vocabulary(analyze):
    codes = _codes(analyze, "We embark into the labyrinth of an enigma and metamorphosis.")
    assert codes.count("NB502") >= 3  # embark, labyrinth, enigma, metamorphosis


def test_trailing_engagement_phrase(analyze):
    assert "NB504" in _codes(analyze, "That's the plan. Would you like to hear more?")


def test_rule_of_three_fragments(analyze):
    text = "It changed me. The jokes. The wins. The team. That is what mattered."
    assert "NB507" in _codes(analyze, text)


def test_rule_of_three_not_on_normal_prose(analyze):
    text = "This is a perfectly ordinary sentence that simply keeps going for a while."
    assert "NB507" not in _codes(analyze, text)


def test_no_x_no_y_just_z(analyze):
    assert "NB501" in _codes(analyze, "No fluff, no filler, just results you can use.")


def test_signposting_filler(analyze):
    assert "NB504" in _codes(analyze, "And here's the kicker: it runs entirely offline.")


def test_align_with_editorializing(analyze):
    assert "NB503" in _codes(analyze, "The roadmap aligns with our long-term goals.")


def test_emoji_overuse_threshold(analyze):
    assert "NB508" not in _codes(analyze, "Nice work 🌱 on the release.")
    assert "NB508" in _codes(analyze, "Features: ✅ fast ✅ safe ✅ simple 🚀 shipped.")


def test_intensifier(analyze):
    r = analyze("This is very good and really solid work here.", config=Config(select=("NB510",)))
    assert any(i.code == "NB510" for i in r.issues)


def test_participial_significance_closer(analyze):
    r = analyze(
        "The city grew fast, highlighting its importance to the region.",
        config=Config(select=("NB511",)),
    )
    assert any(i.code == "NB511" for i in r.issues)


def test_repeated_opener(analyze):
    text = "The team wrote it. The team tested it. The team shipped it."
    r = analyze(text, config=Config(select=("NB512",)))
    assert any(i.code == "NB512" for i in r.issues)


def test_monotonous_rhythm_flags_uniform(analyze):
    text = (
        "The red car drove down the road. The blue bike rode up the hill. "
        "The green bus went past the shop. The gray van parked near the gate. "
        "The gold train left from the yard. The pink boat crossed the wide lake."
    )
    r = analyze(text, config=Config(select=("NB509",)))
    assert any(i.code == "NB509" for i in r.issues)


def test_monotonous_rhythm_ok_when_varied(analyze):
    text = (
        "Short. This sentence is a good deal longer than the last one, and it "
        "keeps running on for quite a while before it finally stops. Tiny. "
        "Here is another long stretch that wanders across many words without pause. "
        "Mid. Done."
    )
    r = analyze(text, config=Config(select=("NB509",)))
    assert not any(i.code == "NB509" for i in r.issues)


def test_curly_quote_inconsistency_flagged(analyze):
    # mostly straight quotes with an intruding curly pair (pasted-AI signal)
    text = 'She said "hi" and "bye" and "ok", then wrote “oops” once.'
    r = analyze(text, config=Config(select=("NB513",)))
    assert any(i.code == "NB513" for i in r.issues)


def test_curly_quotes_consistent_not_flagged(analyze):
    # all-curly typography is normal, not a tell
    r = analyze("She said “hi” and “bye” and “ok” today.", config=Config(select=("NB513",)))
    assert not any(i.code == "NB513" for i in r.issues)


def test_em_dash_within_human_range_not_flagged(analyze):
    # 3 em dashes in a long passage is a normal human rate (~10/1k), not overuse
    text = ("The plan worked well overall. " * 60) + "Then — later — and finally — done."
    r = analyze(text, config=Config(select=("NB506",)))
    assert not any(i.code == "NB506" for i in r.issues)


def test_em_dash_dense_overuse_flagged(analyze):
    text = "It was fast — clean — simple — robust — done — shipped — great."
    r = analyze(text, config=Config(select=("NB506",)))
    assert any(i.code == "NB506" for i in r.issues)


def test_title_case_heading(analyze):
    r = analyze(
        "# Getting Started With Django\n\nSome text here for the body.\n",
        config=Config(select=("NB514",)),
        is_markdown=True,
        name="d.md",
    )
    assert any(i.code == "NB514" for i in r.issues)


def test_sentence_case_heading_ok(analyze):
    r = analyze(
        "# Getting started with Django\n\nSome text here for the body.\n",
        config=Config(select=("NB514",)),
        is_markdown=True,
        name="d.md",
    )
    assert not any(i.code == "NB514" for i in r.issues)


def test_predicate_hyphen(analyze):
    r = analyze("The whole team is cross-functional these days.", config=Config(select=("NB515",)))
    assert any(i.code == "NB515" for i in r.issues)


def test_bold_listicle(analyze):
    text = "- **First:** one\n- **Second:** two\n- **Third:** three\n"
    r = analyze(text, config=Config(select=("NB516",)), is_markdown=True, name="d.md")
    assert any(i.code == "NB516" for i in r.issues)


def test_severity_split(analyze):
    # confident tell = warning; advisory = info
    text = "We delve into it, highlighting its importance to everyone here today."
    issues = {i.code: i.severity.value for i in analyze(text, config=AI).issues}
    assert issues.get("NB502") == "warning"
    assert issues.get("NB511") == "info"
