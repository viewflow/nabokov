"""NB601 — low-concreteness ("empty prose") paragraphs.

Uses the Brysbaert, Warriner & Kuperman (2014) concreteness norms: ~37k English
lemmas rated 1 (abstract: *belief* 1.19, *paradigm* 1.73) to 5 (concrete: *sled*,
*daisy*, *pizza* 5.0) by thousands of raters. A paragraph whose nouns and verbs
average far toward the abstract end is grammatical prose that names nothing you
can see or touch — corporate mush and LLM filler score here; narrative and
example-driven prose does not.

Advisory only (info): abstract paragraphs are sometimes the honest register of
philosophy or mathematics. The threshold is calibrated on the essayist corpus
(PG, Orwell, Housel, Sivers…) so their most abstract paragraphs stay clean.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data_loader import concreteness
from ..issue import Issue, Severity
from .base import CheckContext, Rule, paragraph_ranges

# Mean rating below this = flag; fewer than _MIN_RATED rated nouns/verbs = skip
# (too small a sample to judge). Calibrated on the essayist corpus: all 810
# paragraphs across PG, Orwell, Housel, Sivers, SSC, V. Nabokov, and patio11
# score >= 2.2, while nominalization-heavy corporate filler lands near 2.1.
_THRESHOLD = 2.2
_MIN_RATED = 12
_CONTENT_POS = {"NOUN", "VERB"}


class ConcretenessRule(Rule):
    code = "NB601"
    name = "low-concreteness"
    category = "semantic"
    codes = ("NB601",)
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        ratings = concreteness()
        text = ctx.doc.text
        for start, end in paragraph_ranges(text):
            scores = [
                ratings[tok.lemma_.lower()]
                for tok in ctx.doc.char_span(start, end, alignment_mode="expand") or ()
                if tok.pos_ in _CONTENT_POS and tok.lemma_.lower() in ratings
            ]
            if len(scores) < _MIN_RATED:
                continue
            mean = sum(scores) / len(scores)
            if mean >= _THRESHOLD:
                continue
            stripped_end = start + len(text[start:end].rstrip())
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(stripped_end)
            yield Issue(
                code="NB601",
                name="low-concreteness",
                message=(
                    f"abstract paragraph (concreteness {mean:.1f}/5) — it names "
                    "nothing you can see or touch; add a real example, number, or image"
                ),
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                text=text[start:stripped_end],
            )
