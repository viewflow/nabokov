"""The three register metrics: nominal density, pronoun density, temporal ratio.

Reported next to burstiness and diversity, and deliberately not scored — the research
behind them gives directions without thresholds. These tests pin the arithmetic, the
genre separation the numbers are actually good for, and the fact that nothing acts on
them.
"""

from __future__ import annotations

import spacy

from nabokov.readability import nominal_density, pronoun_density, temporal_ratio

TECHNICAL = (
    "The parser resolves the import graph before compilation. Module registration "
    "happens in the loader. Configuration values override the defaults from the "
    "environment file. The build step emits a manifest."
)

PERSONAL = (
    "I tried it and it broke. She told me why, and I still did not believe her until "
    "I read the log myself. We fixed it together, though he thought we were wrong."
)


def _doc(text):
    return spacy.load("en_core_web_sm")(text)


# --- nominal density ----------------------------------------------------------


def test_nominal_density_separates_technical_from_personal():
    """The metric's real use: it tracks register, and the gap is large."""
    assert nominal_density(_doc(TECHNICAL)) > nominal_density(_doc(PERSONAL)) + 0.15


def test_nominal_density_is_a_share():
    value = nominal_density(_doc(TECHNICAL))
    assert 0.0 <= value <= 1.0


def test_nominal_density_of_empty_text_is_zero():
    assert nominal_density(_doc("")) == 0.0


# --- pronoun density ----------------------------------------------------------


def test_pronoun_density_separates_personal_from_technical():
    assert pronoun_density(_doc(PERSONAL)) > pronoun_density(_doc(TECHNICAL))


def test_pronoun_density_is_per_hundred_words():
    """Ten words, one pronoun -> 10 per 100."""
    assert pronoun_density(_doc("It resolves the import graph before the build step ends")) == 10.0


def test_pronoun_density_of_empty_text_is_zero():
    assert pronoun_density(_doc("")) == 0.0


# --- temporal ratio -----------------------------------------------------------


def test_all_temporal_connectives_is_one():
    assert temporal_ratio(_doc("First run it. Then build. Next deploy. Finally verify.")) == 1.0


def test_all_additive_connectives_is_zero():
    assert temporal_ratio(_doc("It builds and deploys, but the cache is stale, so retry.")) == 0.0


def test_a_mix_lands_between():
    value = temporal_ratio(_doc("First build it, but the cache is stale, so then retry."))
    assert 0.0 < value < 1.0


def test_no_connectives_at_all_is_zero():
    """Nothing to divide, so there is no ratio — indistinguishable from additive."""
    assert temporal_ratio(_doc("The parser emits a manifest.")) == 0.0


def test_the_connective_sets_are_disjoint():
    """A word in both lists does not cancel — it drags the ratio toward 0.5.

    With B words counted on both sides the value is (T+B)/(T+A+2B). "since" was in
    both lists (causal "since it failed" and temporal "since 2020") and made
    "since since since" measure exactly 0.5, which an earlier comment mistook for
    cancellation. A word needing disambiguation is now in neither list.
    """
    from nabokov.readability import _ADDITIVE_CONNECTIVES, _TEMPORAL_CONNECTIVES

    assert not (_TEMPORAL_CONNECTIVES & _ADDITIVE_CONNECTIVES)
    assert temporal_ratio(_doc("since since since")) == 0.0


# --- wiring -------------------------------------------------------------------


def test_reported_in_document_stats(analyze):
    stats = analyze(TECHNICAL).stats
    assert stats.nominal_density > 0
    assert stats.temporal_ratio >= 0


def test_reported_in_the_stats_line(analyze):
    from nabokov.reporters.common import format_document_stats

    out = format_document_stats([analyze(TECHNICAL)])
    assert "register:" in out
    assert "nominal=" in out
    assert "pronouns=" in out
    assert "temporal_connectives=" in out


def test_reported_in_json(analyze):
    from nabokov.reporters.json_reporter import result_payload

    summary = result_payload(analyze(TECHNICAL))["summary"]
    for key in ("nominal_density", "pronoun_density", "temporal_ratio"):
        assert key in summary


def test_no_rule_reports_them_and_no_score_key_exposes_them(analyze):
    """A direction without a threshold is not a finding, so nothing acts on these.

    Scope, stated honestly: this guards the emitted findings and the ``--score``
    payload *keys*. It cannot detect a change that folded nominal density into an
    existing score component's arithmetic without naming it — only calibration
    review catches that.
    """
    from nabokov.score import compute

    result = analyze("The configuration file registration process documentation.")
    metrics = {"nominal_density", "pronoun_density", "temporal_ratio"}
    assert not [i for i in result.issues if "nominal" in i.message.lower()]
    assert set(compute(result)) & metrics == set()
