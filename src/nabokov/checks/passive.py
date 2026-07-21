"""NB302 — passive voice via spaCy dependency parsing.

spaCy-primary: any verb that has an ``auxpass`` child is passive ("was written",
"is being replaced"). We span the passive auxiliaries + the participle, and extend
over the ``agent`` ("by …") phrase when present. This diverges from the classic
regex heuristic on purpose — it catches multi-auxiliary passives and avoids the
false positives the `(is|are|was…) + word` pattern produces.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..issue import Issue, Severity
from .base import CheckContext, Rule


class PassiveRule(Rule):
    code = "NB302"
    name = "passive-voice"
    category = "grammar"
    codes = ("NB302",)

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        doc = ctx.doc
        for verb in doc:
            aux = [c for c in verb.children if c.dep_ == "auxpass"]
            if not aux:
                continue
            parts = [*aux, verb]
            # include the "by <agent>" phrase if spaCy attached one
            for child in verb.children:
                if child.dep_ == "agent":
                    parts.extend(child.subtree)
            start_tok = min(parts, key=lambda t: t.i)
            end_tok = max(parts, key=lambda t: t.i)
            start = start_tok.idx
            end = end_tok.idx + len(end_tok.text)
            text = doc.text[start:end]
            flat = " ".join(text.split())  # spans can wrap a line; keep the message flat
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(end)
            yield Issue(
                code="NB302",
                name="passive-voice",
                message=f"passive voice: '{flat}'",
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=Severity.WARNING,
                text=text,
            )
