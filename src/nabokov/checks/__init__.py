"""The rule registry — the single place every check is declared and toggled.

To add a rule: implement a Rule subclass, append an instance to ``ALL_RULES``, add its
code(s) to ``RULE_META``, and set ``default_on`` (the NB5xx AI-writing checks set it
False so they stay opt-in). ``DEFAULT_CODES`` is derived from ``default_on``.
"""

from __future__ import annotations

from .adverbs import AdverbRule
from .ai_writing import (
    AdjectiveTriadRule,
    AiArtifactRule,
    BoldListicleRule,
    CurlyQuoteRule,
    EditorializingRule,
    EmDashRule,
    EmojiRule,
    FillerRule,
    HedgeStackRule,
    IntensifierRule,
    MonotonousRhythmRule,
    NegationContrastRule,
    ParticipialCloserRule,
    PredicateHyphenRule,
    PufferyRule,
    RepeatedOpenerRule,
    RuleOfThreeRule,
    TitleCaseHeadingRule,
    TransitionRule,
    VocabClusterRule,
)
from .base import CheckContext, Rule
from .clarity import DummySubjectRule, NominalizationRule
from .concreteness import ConcretenessRule
from .passive import PassiveRule
from .phrases import ComplexPhraseRule, QualifierRule
from .sentences import PeriodicSentenceRule, SentenceRule

ALL_RULES: list[Rule] = [
    SentenceRule(),
    PeriodicSentenceRule(),
    AdverbRule(),
    PassiveRule(),
    ComplexPhraseRule(),
    QualifierRule(),
    NominalizationRule(),
    DummySubjectRule(),
    ConcretenessRule(),
    # NB5xx — signs of AI writing (off by default; enable with --select/--extend-select NB5)
    NegationContrastRule(),
    PufferyRule(),
    EditorializingRule(),
    FillerRule(),
    TransitionRule(),
    EmDashRule(),
    RuleOfThreeRule(),
    EmojiRule(),
    # NB5xx de-slop checks (from open-source humanizer/unslop skills)
    IntensifierRule(),
    ParticipialCloserRule(),
    MonotonousRhythmRule(),
    RepeatedOpenerRule(),
    CurlyQuoteRule(),
    TitleCaseHeadingRule(),
    PredicateHyphenRule(),
    BoldListicleRule(),
    VocabClusterRule(),
    AdjectiveTriadRule(),
    AiArtifactRule(),
    HedgeStackRule(),
]

# code -> (name, human description)
RULE_META: dict[str, tuple[str, str]] = {
    "NB101": ("readability", "Document readability grade (emitted with --max-grade)"),
    "NB201": ("very-hard-sentence", "Very hard to read sentence"),
    "NB202": ("hard-sentence", "Hard to read sentence"),
    "NB203": ("periodic-sentence", "Main clause buried after a long build-up (advisory)"),
    "NB301": ("adverb", "Adverb"),
    "NB302": ("passive-voice", "Passive voice"),
    "NB303": ("qualifier", "Qualifier / weakening phrase"),
    "NB304": ("nominalization", "Action hidden in a noun behind a light verb"),
    "NB305": ("dummy-subject", "Dummy subject 'there is/are'"),
    "NB401": ("complex-phrase", "Complex / wordy phrase with a simpler alternative"),
    "NB501": ("ai-negation-contrast", "AI tell: 'it's not X, it's Y' negation-contrast"),
    "NB502": ("ai-puffery", "AI tell: puffery / buzzword vocabulary"),
    "NB503": ("ai-editorializing", "AI tell: editorializing / promotional phrase"),
    "NB504": ("ai-filler", "AI tell: conversational / chatbot filler"),
    "NB505": ("ai-transition", "AI tell: overused transition word"),
    "NB506": ("ai-em-dash", "AI tell: em-dash overuse"),
    "NB507": ("ai-rule-of-three", "AI tell: rule-of-three staccato fragments"),
    "NB508": ("ai-emoji", "AI tell: emoji used as formatting"),
    "NB509": ("ai-monotonous-rhythm", "AI tell: flat sentence rhythm (low burstiness)"),
    "NB510": ("ai-intensifier", "AI tell: weak intensifier / weasel word"),
    "NB511": ("ai-participial-closer", "AI tell: empty participial 'significance' closer"),
    "NB512": ("ai-repeated-opener", "AI tell: repeated sentence opener"),
    "NB513": ("ai-curly-quote", "AI tell: curly / smart quotes"),
    "NB514": ("ai-title-case-heading", "AI tell: Title Case heading"),
    "NB515": ("ai-predicate-hyphen", "AI tell: hyphen in predicate position"),
    "NB516": ("ai-bold-listicle", "AI tell: bold-label listicle formatting"),
    "NB517": ("ai-vocab-cluster", "AI tell: clustered generic-praise vocabulary"),
    "NB518": ("ai-adjective-triad", "AI tell: repeated coordinated adjective triads"),
    "NB519": ("ai-artifact", "AI artifact: citation markup, tool URLs, placeholders (near-proof)"),
    "NB520": ("ai-hedge-stack", "AI tell: modal stacked with hedge adverb ('could potentially')"),
    "NB601": ("low-concreteness", "Abstract paragraph — no lived detail (advisory)"),
}

ALL_CODES: tuple[str, ...] = tuple(RULE_META)
# Derived from each rule's default_on flag. NB101 is a summary gate (emitted only with
# --max-grade) and NB5xx (AI writing) is opt-in, so both stay out of the default set.
DEFAULT_CODES: tuple[str, ...] = tuple(
    code for rule in ALL_RULES if rule.default_on for code in rule.codes
)

__all__ = [
    "ALL_CODES",
    "ALL_RULES",
    "DEFAULT_CODES",
    "RULE_META",
    "CheckContext",
    "Rule",
]
