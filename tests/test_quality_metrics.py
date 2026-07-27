"""The four quality metrics ported from the essay-scoring literature.

Reported next to burstiness and diversity, and deliberately not scored — every
correlation behind them was measured on student or L2 exam essays, and nothing tests
whether it survives the move to fluent adult prose. See docs/text-quality-research.md.

These tests pin the arithmetic, the separation each number is actually good for, and
the fact that nothing acts on them.
"""

from __future__ import annotations

from nabokov.analyzer import load_nlp
from nabokov.checks.base import paragraph_ranges
from nabokov.readability import (
    dependency_distance,
    formality,
    modifier_density,
    paragraph_cohesion,
)


def _doc(text):
    return load_nlp()(text)


def _cohesion(text):
    return paragraph_cohesion(_doc(text), paragraph_ranges(text))


# Same four paragraphs in both documents. COHERENT carries its subject forward;
# SCATTERED puts unrelated paragraphs side by side. Vocabulary size is comparable, so
# any difference is adjacency, not word choice.
COHERENT = """The parser resolves the import graph before compilation. It walks
each module in turn and records what that module needs.

The import graph feeds the loader. Because the parser has already resolved every
module, the loader can register them without a second pass over the graph.

Loader registration emits a manifest. That manifest lists each registered module
and the compilation order the loader chose for them.

The manifest is what the build step consumes. It reads the compilation order and
compiles each module the loader registered."""

SCATTERED = """The parser resolves the import graph before compilation. It walks
each module in turn and records what that module needs.

Tomatoes ripen faster in a warm greenhouse. Gardeners water them every morning
and prune the lower leaves so the fruit gets more sun.

The orchestra rehearsed the symphony twice. Its conductor asked the strings to
play the second movement more quietly than the brass.

Rainfall last winter broke a local record. Farmers in the valley reported the
wettest planting season anyone there could remember."""


# --- paragraph cohesion ---------------------------------------------------------


def test_cohesion_separates_a_carried_subject_from_unrelated_paragraphs():
    """The metric's whole purpose: it reads whether paragraphs connect."""
    assert _cohesion(COHERENT) > _cohesion(SCATTERED) + 0.15


def test_cohesion_reads_order_not_vocabulary():
    """Reversing the paragraphs keeps every word and changes which ones sit adjacent.

    This is the property that makes the number worth reporting. A measure that only
    counted vocabulary would score both arrangements identically.
    """
    paragraphs = COHERENT.split("\n\n")
    reordered = "\n\n".join([paragraphs[0], paragraphs[3], paragraphs[1], paragraphs[2]])
    assert _cohesion(reordered) < _cohesion(COHERENT)


def test_cohesion_is_a_share():
    assert 0.0 <= _cohesion(COHERENT) <= 1.0


def test_cohesion_zero_without_two_scorable_paragraphs():
    """A heading plus one paragraph has no adjacent pair to measure."""
    assert _cohesion("# Title\n\nOnly one real paragraph of prose sits here.") == 0.0


def test_cohesion_skips_paragraphs_too_short_to_share_vocabulary():
    """A one-line aside between two related paragraphs must not read as a gap.

    Without the content-word floor the aside would score 0 against both neighbours
    and halve the document's number for a break the writer never made.
    """
    aside = COHERENT.split("\n\n")
    with_aside = "\n\n".join([aside[0], "Note.", aside[1]])
    without = "\n\n".join([aside[0], aside[1]])
    assert _cohesion(with_aside) == _cohesion(without)


# --- dependency distance --------------------------------------------------------


def test_dependency_distance_rises_with_nesting():
    """Same clause count, different structural spread."""
    flat = _doc("The cat sat. The dog barked. The bird flew.")
    nested = _doc(
        "The cat that the dog which the child had raised chased sat on the mat "
        "beside the door that the neighbour painted."
    )
    assert dependency_distance(nested) > dependency_distance(flat)


def test_dependency_distance_is_not_just_sentence_length():
    """The reason to report it: it sees something the grade metric cannot.

    Both sentences run to a similar length. One chains left to right, the other
    buries its subject and verb far apart.
    """
    chained = _doc(
        "I walked to the shop and bought some bread and paid the man and left "
        "the shop and went home again."
    )
    buried = _doc(
        "The report that the committee which the board appointed last spring "
        "commissioned was finally published."
    )
    assert dependency_distance(buried) > dependency_distance(chained)


def test_dependency_distance_zero_on_empty():
    assert dependency_distance(_doc("")) == 0.0


# --- formality (Heylighen & Dewaele F-score) ------------------------------------


def test_formality_separates_informational_from_involved():
    """The contrast the F-score was built for, in the published direction."""
    informational = _doc(
        "The resolution of the import graph precedes compilation of the modules "
        "in the registry of the loader."
    )
    involved = _doc("I tried it and it broke, so we fixed it and then I told her about it.")
    assert formality(informational) > formality(involved)


def test_formality_lands_in_the_published_band_for_prose():
    """Written prose should read near the reported written/scientific range, not at an extreme."""
    value = formality(
        _doc(
            "The parser resolves the import graph before compilation. Module "
            "registration happens in the loader. Configuration values override "
            "the defaults from the environment file."
        )
    )
    assert 50.0 < value < 90.0


def test_formality_is_bounded():
    assert 0.0 <= formality(_doc("I am here.")) <= 100.0


def test_formality_zero_on_empty():
    assert formality(_doc("")) == 0.0


# --- modifier density -----------------------------------------------------------


def test_modifier_density_rises_with_noun_phrase_elaboration():
    bare = _doc("Systems fail. Engineers respond. Managers report.")
    elaborated = _doc(
        "The distributed storage systems in the primary region fail. The on-call "
        "engineers of the platform team respond."
    )
    assert modifier_density(elaborated) > modifier_density(bare)


def test_modifier_density_does_not_double_count_compounds():
    """"machine learning model" is one head with modifiers, not three heads."""
    value = modifier_density(_doc("The machine learning model converged."))
    assert value <= 2.0


def test_modifier_density_zero_without_nouns():
    assert modifier_density(_doc("Run quickly.")) == 0.0


# --- nothing acts on them -------------------------------------------------------


def test_quality_metrics_emit_no_findings(analyze):
    """The point of the block: reported, never scored.

    A threshold on any of these would be an extrapolation from learner corpora to
    fluent adult prose, which is exactly what the research does not support. A
    cohesion rule was measured and killed: 21.8% of adjacent paragraph pairs in this
    repo's own hand-written prose share no content lemma at all, so the finding would
    have been noise. See docs/text-quality-research.md.
    """
    result = analyze(SCATTERED, is_markdown=True, name="scattered.md")
    codes = {issue.code for issue in result.issues}
    assert not codes & {"NB602", "NB603", "NB604", "NB605"}
    assert result.stats.paragraph_cohesion >= 0.0
    assert result.stats.dependency_distance > 0.0
    assert result.stats.formality > 0.0
    assert result.stats.modifier_density > 0.0
