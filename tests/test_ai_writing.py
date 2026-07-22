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


def test_intensifier_skips_adjectival_very(analyze):
    # "very" modifying a noun is the idiom (= "exact"), not a degree word
    text = (
        "From the very beginning, I knew who I wanted my co-founder to be. "
        "His very existence proves the point. It happened at that very moment."
    )
    r = analyze(text, config=Config(select=("NB510",)))
    assert not r.issues


def test_intensifier_skips_very_before_superlative_or_ordinal(analyze):
    # degree "very" is ungrammatical before superlatives/ordinals ("*very
    # biggest"), so these are always the emphatic idiom
    text = (
        "At the very least, we should test it. The very same bug came back. "
        "It was the very first time. The very next day she left. "
        "That is the very last thing I need. He is the very best."
    )
    r = analyze(text, config=Config(select=("NB510",)))
    assert not r.issues


def test_intensifier_skips_quantity_idioms(analyze):
    text = "Quite a few users waited quite a while. Simply put, it works."
    r = analyze(text, config=Config(select=("NB510",)))
    assert not r.issues


def test_puffery_skips_noun_sense_and_fixed_phrases(analyze):
    text = (
        "The test harness runs every check. Foster carers get an allowance. "
        "Navigate to the Settings page. The leverage ratio doubled. "
        "Print in landscape orientation. She has a keen eye for detail."
    )
    r = analyze(text, config=Config(select=("NB502",)))
    assert not r.issues


def test_puffery_still_flags_verb_sense(analyze):
    # the imperative tags PROPN in context — must still be caught
    text = "Great tool. Harness the power of AI to foster innovation."
    r = analyze(text, config=Config(select=("NB502",)))
    assert len([i for i in r.issues if i.code == "NB502"]) == 2


def test_filler_skips_reported_speech_and_punctuation(analyze):
    text = "She asked a great question during the seminar. End every sentence with a full stop."
    r = analyze(text, config=Config(select=("NB504",)))
    assert not r.issues


def test_filler_still_flags_chatbot_openers(analyze):
    text = "Great question! Let me explain. Full stop."
    r = analyze(text, config=Config(select=("NB504",)))
    codes = [i.code for i in r.issues]
    assert codes.count("NB504") == 3


def test_quoted_text_exempt(analyze):
    # mention, not use: quoting tell-words or chatbot speech is not writing it
    text = (
        'Words like "delve" and "tapestry" mark AI text. '
        '"Great question!" said the interviewer. '
        "Curly too: “Let me explain the tapestry.”"
    )
    r = analyze(text, config=Config(select=("NB502", "NB504")))
    assert not r.issues


def test_quoted_exemption_stays_inside_the_quotes(analyze):
    # the same sentence still flags tells OUTSIDE the quote pair
    text = 'He said "delve" is overused, then embarked on a tapestry of excuses.'
    r = analyze(text, config=Config(select=("NB502",)))
    flagged = {i.text.lower() for i in r.issues}
    assert flagged == {"embarked", "tapestry"}


def test_unpaired_quote_does_not_exempt(analyze):
    # a stray quote (inch mark) must not silently swallow the paragraph
    text = 'The shelf is 15" wide, a testament to seamless synergy.'
    r = analyze(text, config=Config(select=("NB502",)))
    assert len(r.issues) == 3


def test_straight_quote_does_not_span_lines(analyze):
    # an unbalanced straight quote on one line can't pair across a newline
    text = 'She wrote 15" on the tag.\nA tapestry of synergy followed."\n'
    r = analyze(text, config=Config(select=("NB502",)))
    assert len(r.issues) == 2


def test_intensifier_still_flags_degree_very(analyze):
    # the exception must not gut the rule: adverbial "very" stays a tell,
    # including before -est-shaped plain adjectives ("honest" is JJ, not JJS)
    text = "From the very beginning it was very important, very clear, and very honest."
    r = analyze(text, config=Config(select=("NB510",)))
    assert len([i for i in r.issues if i.code == "NB510"]) == 3


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


def test_paragraph_opener_flags_repeated_and(analyze):
    text = (
        "We shipped the beta in March after two rounds of testing.\n\n"
        "And all that time the team kept talking to early users.\n\n"
        "And it feels especially meaningful now that adoption doubled.\n\n"
        "And we have already tested the flow with real customers.\n\n"
        "The next milestone is the public launch in June."
    )
    r = analyze(text, config=Config(select=("NB521",)))
    hits = [i for i in r.issues if i.code == "NB521"]
    assert len(hits) == 3  # one per offending "And" paragraph
    assert "'And'" in hits[0].message


def test_paragraph_opener_tolerates_varied_coordinators(analyze):
    # DHH-style: coordinators open paragraphs, but different ones each time
    text = (
        "Workaholism trickles down from the top of the org chart.\n\n"
        "And the leaders rarely notice what their hours signal.\n\n"
        "But the team notices every late-night commit and reply.\n\n"
        "So the calendar becomes the culture, whatever the handbook says."
    )
    r = analyze(text, config=Config(select=("NB521",)))
    assert not any(i.code == "NB521" for i in r.issues)


def test_paragraph_opener_ignores_mid_paragraph_and(analyze):
    text = (
        "We shipped the beta and kept iterating. And then we rested.\n\n"
        "The users liked it and said so. And they told their friends.\n\n"
        "The launch went well and the numbers held. And we celebrated."
    )
    r = analyze(text, config=Config(select=("NB521",)))
    assert not any(i.code == "NB521" for i in r.issues)


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


# A near-perfectly uniform passage (every sentence six words): CV well below the
# 'flat' cutoff, so it escalates from advisory to a warning.
_ROBOTIC = (
    "The system processes the data. The system stores the data. "
    "The system returns the data. The team maintains the system. "
    "The team updates the system. The team monitors the system. "
    "Managers review the weekly reports. Managers approve the annual budgets."
)


def test_monotonous_rhythm_warns_when_robotic(analyze):
    from nabokov.issue import Severity

    issues = [i for i in analyze(_ROBOTIC, config=Config(select=("NB509",))).issues if i.code == "NB509"]
    assert issues and issues[0].severity is Severity.WARNING


def test_monotonous_rhythm_threshold_is_per_target(analyze):
    # post_final-style rhythm (CV ~0.35): flagged under NORMAL, tolerated under SOCIAL,
    # where flatter rhythm is native to the register.
    text = (
        "The first time I asked, he said no. I knew who I wanted from the start. "
        "So I looked at other people and weighed the options for a while. "
        "But I never let the idea go completely. We kept trading ideas as before. "
        "We had been friends for three years by then. Our first project was a small one. "
        "It showed me what the two of us could build together if we tried. "
        "Then, after all of that back and forth, he finally said yes to me."
    )
    normal = analyze(text, config=Config(select=("NB509",), target="NORMAL"))
    social = analyze(text, config=Config(select=("NB509",), target="SOCIAL"))
    assert any(i.code == "NB509" for i in normal.issues)
    assert not any(i.code == "NB509" for i in social.issues)


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


def test_no_longer_reframe(analyze):
    text = "They're no longer entertainment or background noise. They're part of my market research."
    issues = [i for i in analyze(text, config=AI).issues if i.code == "NB501"]
    assert issues and issues[0].severity.value == "info"  # advisory — human rhetoric too


def test_no_longer_first_person_ok(analyze):
    # "I'm no longer X. I'm Y" is ordinary autobiography, not the reframe tell
    text = "I'm no longer working at the bank. I'm building a startup in Berlin now."
    assert "NB501" not in _codes(analyze, text)


def test_no_longer_without_copula_ok(analyze):
    # plain reporting: the second sentence doesn't rename the subject
    text = "It's no longer maintained by the original author. It gets no updates at all."
    assert "NB501" not in _codes(analyze, text)


def test_doesnt_mean_reframe(analyze):
    text = (
        "Market research doesn't have to mean spreadsheets and surveys.\n\n"
        "Sometimes it means putting in your earbuds and listening."
    )
    issues = [i for i in analyze(text, config=AI).issues if i.code == "NB501"]
    assert issues and issues[0].severity.value == "info"
    assert "'doesn't mean' reframe" in issues[0].message


def test_doesnt_mean_without_reveal_ok(analyze):
    # PG, "How to Do What You Love" register: the bare negation with no
    # "it means Y" reveal is ordinary human prose
    text = "Writing essays doesn't have to mean publishing them. That may seem strange now."
    assert "NB501" not in _codes(analyze, text)


def test_appearance_verdict_couplet(analyze):
    text = "This feels pointless. It is not. But the check still has to run each time."
    issues = [i for i in analyze(text, config=AI).issues if i.code == "NB501"]
    assert issues and issues[0].severity.value == "info"
    assert "appearance-verdict couplet" in issues[0].message


def test_appearance_question_followup_ok(analyze):
    # V. Nabokov: a question after the appearance sentence is inquiry, not verdict
    text = "This seems perfect. But is it? The play has hardly started at this point."
    assert "NB501" not in _codes(analyze, text)


def test_appearance_inspection_sense_ok(analyze):
    # "looks at" is inspection, not appearance
    text = "It looks at the manifest first. Then it resolves every pinned version."
    assert "NB501" not in _codes(analyze, text)


def test_appearance_spoken_reply_ok(analyze):
    # patio11's negotiation dialogue: a comma marks the spoken reply register
    text = "That sounds about right, yeah. Great, I cannot wait to get started."
    assert "NB501" not in _codes(analyze, text)


def test_colon_reveal_triad_fires_alone(analyze):
    # a single triad normally needs the density gate, but copula-colon bypasses it
    text = "That's where the real signal is: spontaneous, unfiltered, and impossible to fake."
    issues = [i for i in analyze(text, config=AI).issues if i.code == "NB518"]
    assert issues and "colon-reveal" in issues[0].message


def test_colon_reveal_needs_copula(analyze):
    # the human colon-list rides behind a noun ("three things:"), not a copula — no bypass
    text = "Everyone wants the same three things: respect, autonomy, and control over their time."
    assert "NB518" not in _codes(analyze, text)


def test_engagement_bait_closer(analyze):
    text = (
        "Podcasts turned into my market research this year.\n\n"
        "What's the most unexpected place you've found genuine customer insight?"
    )
    issues = [i for i in analyze(text, config=AI).issues if i.code == "NB522"]
    assert issues and issues[0].severity.value == "info"


def test_engagement_bait_needs_verb_after_you(analyze):
    # an ordinary sign-off question is not bait — no verb follows "you"
    text = "Thanks for reading the notes.\n\nWhat's the best way to reach you?"
    assert "NB522" not in _codes(analyze, text)


def test_engagement_bait_only_at_document_end(analyze):
    # the same question mid-document is a real question, not a closer
    text = (
        "What's the most unexpected place you've found genuine customer insight?\n\n"
        "For me it was a podcast about logistics, of all things."
    )
    assert "NB522" not in _codes(analyze, text)
