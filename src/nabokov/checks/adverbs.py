"""NB301 — adverbs (spaCy POS + `-ly`, minus the exception list).

spaCy-primary: a token is flagged when spaCy tags it ADV *and* it ends in ``-ly``
*and* it is not in the bundled exception list. Set ``adverbs_all_pos`` to
flag every ADV regardless of the ``-ly`` suffix.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data_loader import adverb_exceptions
from ..issue import Issue, Severity
from .base import CheckContext, Rule


class AdverbRule(Rule):
    code = "NB301"
    name = "adverb"
    category = "word"
    codes = ("NB301",)

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        exceptions = adverb_exceptions()
        all_pos = ctx.config.adverbs_all_pos
        for tok in ctx.doc:
            if tok.pos_ != "ADV":
                continue
            low = tok.text.lower()
            if not all_pos and not low.endswith("ly"):
                continue
            if len(tok.text) <= 3 or low in exceptions:
                continue
            start = tok.idx
            end = tok.idx + len(tok.text)
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(end)
            # "a stronger verb" only makes sense for adverbs that modify a real verb;
            # sentence adverbs and copula modifiers ("probably", "merely a label")
            # get an honest message instead.
            if tok.head.pos_ == "VERB":  # noqa: SIM108 - parallel branches read clearer
                hint = "consider a stronger verb"
            else:
                hint = "consider cutting it"
            yield Issue(
                code="NB301",
                name="adverb",
                message=f"adverb '{tok.text}' — {hint}",
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=Severity.WARNING,
                text=tok.text,
            )
