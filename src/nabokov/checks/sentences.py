"""NB201 / NB202 — hard and very-hard sentences (ARI); NB203 — buried main clause."""

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


class PeriodicSentenceRule(Rule):
    """NB203 — the main clause arrives only after a long periodic build-up.

    A cumulative sentence fronts its point and trails detail; a periodic one
    makes the reader hold every subordinate clause in working memory until the
    root verb finally lands. Advisory: periodicity is a legitimate suspense
    device — the finding tells the editor *where* a hard sentence can be split.
    """

    code = "NB203"
    name = "periodic-sentence"
    category = "readability"
    codes = ("NB203",)
    severity = Severity.INFO

    _MAX_LEAD = 20  # words allowed before the root verb

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        for sent in ctx.doc.sents:
            root = sent.root
            if root.pos_ not in ("VERB", "AUX"):
                continue
            lead = sum(1 for t in sent if t.i < root.i and not (t.is_punct or t.is_space))
            if lead <= self._MAX_LEAD:
                continue
            start = sent.start_char
            end = start + len(sent.text.rstrip())
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(end)
            yield Issue(
                code="NB203",
                name="periodic-sentence",
                message=(
                    f"main clause arrives after {lead} words — "
                    "put the point first, or split the sentence there"
                ),
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                text=sent.text.strip(),
            )
