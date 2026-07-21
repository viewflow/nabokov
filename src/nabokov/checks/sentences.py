"""NB201 / NB202 — hard and very-hard-to-read sentences (per-sentence ARI)."""

from __future__ import annotations

from collections.abc import Iterable

from ..issue import Issue, Severity
from ..readability import HARD, VERY_HARD, classify, letters_in, reading_level
from .base import CheckContext, Rule


class SentenceRule(Rule):
    code = "NB201"
    name = "hard-sentence"
    category = "readability"
    codes = ("NB201", "NB202")

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        target = ctx.config.target
        for sent in ctx.doc.sents:
            words = [t for t in sent if not (t.is_punct or t.is_space)]
            n_words = len(words)
            if n_words == 0:
                continue
            letters = sum(letters_in(t.text) for t in words)
            level = reading_level(letters, n_words, 1)
            bucket = classify(level, n_words, target)
            if bucket == VERY_HARD:
                code, name = "NB201", "very-hard-sentence"
                message = f"very hard to read (grade {level})"
                # A long sentence in a readable document is rhythm, not failure —
                # the document-level gate is NB101 (--max-grade), which stays an error.
                severity = Severity.WARNING
            elif bucket == HARD:
                code, name = "NB202", "hard-sentence"
                message = f"hard to read (grade {level})"
                severity = Severity.WARNING
            else:
                continue

            start = sent.start_char
            # trim trailing whitespace so the highlight ends on real text
            end = start + len(sent.text.rstrip())
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(end)
            yield Issue(
                code=code,
                name=name,
                message=message,
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=severity,
                text=sent.text.strip(),
            )
