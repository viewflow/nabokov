"""NB313 — terminal punctuation on a heading.

A heading is a label, not a sentence, so it does not take a full stop. Both
Vale's Google and Microsoft styles ship this check. It is house style rather
than an accessibility requirement, so it is info and its fix is cosmetic — but
it is unambiguous and the fix is exact, which is worth more than a louder rule
that has to guess.

Question marks stay legal: "Is it ready?" is a heading shaped like a question,
and Google's guidance allows it. So do ellipses, which are a deliberate device
rather than a slip.

Only *trailing* punctuation counts. An internal colon is how half the how-to
headings in the world are written ("Step 1: Install"), and Microsoft's separate
rule against it is a house preference this one does not adopt.

Limitation: setext headings — the ones underlined with ``===`` or ``---`` — are
not indexed as headings by ``source``, so they are invisible here. Modern
Markdown docs use ATX almost exclusively.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule

# Sentence punctuation with no business ending a label. "?" is absent on purpose
# (a question heading is legitimate) and so is "!" (a separate concern).
_TERMINAL = frozenset({".", ",", ";", ":"})

# A trailing ellipsis is a device, not a stray full stop.
_ELLIPSES = ("...", "…")


class HeadingPunctuationRule(Rule):
    code = "NB313"
    name = "heading-punctuation"
    category = "markup"
    codes = ("NB313",)
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        source = ctx.source
        for span in source.spans("heading"):
            text = source.span_text(span).rstrip()
            if not text or text.endswith(_ELLIPSES) or text[-1] not in _TERMINAL:
                continue
            mark = text[-1]
            start = span.start + len(text) - 1
            line, col = source.linecol(start)
            end_line, end_col = source.linecol(start + 1)
            yield Issue(
                code=self.code,
                name=self.name,
                message=f"heading ends in '{mark}' — a heading is a label, not a sentence",
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                # Deleting the last character of a heading strands nothing: there
                # is no following clause and no capital to carry.
                suggestion="",
                applicability=Applicability.REPLACE,
                text=mark,
            )
