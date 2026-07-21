"""NB401 (complex/wordy phrases) and NB303 (qualifiers) via spaCy PhraseMatcher.

Both consume the bundled dictionaries. Matching is case-insensitive
(``attr="LOWER"``) and longest-phrase-wins per position: a match is
dropped if its tokens are already covered by a longer accepted match.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data_loader import complex_phrases, qualifiers
from ..issue import Issue, Severity
from .base import CheckContext, Rule


def _resolve_overlaps(matches: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Greedy longest-first: keep the longest match at each covered span."""
    used: set[int] = set()
    kept: list[tuple[int, int]] = []
    for start, end in sorted(matches, key=lambda m: (-(m[1] - m[0]), m[0])):
        if any(i in used for i in range(start, end)):
            continue
        used.update(range(start, end))
        kept.append((start, end))
    return sorted(kept)


class _PhraseDictRule(Rule):
    """Shared machinery for dictionary phrase rules."""

    def __init__(self) -> None:
        self._matcher = None

    def _phrase_keys(self) -> Iterable[str]:  # pragma: no cover - overridden
        raise NotImplementedError

    def _build_matcher(self, nlp):
        from spacy.matcher import PhraseMatcher

        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        patterns = [nlp.make_doc(p) for p in self._phrase_keys()]
        matcher.add(self.code, patterns)
        return matcher

    def _issue_for(self, ctx: CheckContext, phrase: str, span) -> Issue:
        raise NotImplementedError

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        if self._matcher is None:
            self._matcher = self._build_matcher(ctx.nlp)
        raw = [(start, end) for _mid, start, end in self._matcher(ctx.doc)]
        for start, end in _resolve_overlaps(raw):
            span = ctx.doc[start:end]
            yield self._issue_for(ctx, span.text.lower(), span)


class ComplexPhraseRule(_PhraseDictRule):
    code = "NB401"
    name = "complex-phrase"
    category = "phrase"
    codes = ("NB401",)

    def _phrase_keys(self) -> Iterable[str]:
        return complex_phrases().keys()

    def _issue_for(self, ctx: CheckContext, phrase: str, span) -> Issue:
        suggestions = complex_phrases().get(phrase, [])
        suggestion = ", ".join(suggestions)
        start = span.start_char
        end = span.end_char
        line, col = ctx.source.linecol(start)
        end_line, end_col = ctx.source.linecol(end)
        msg = f"wordy: '{' '.join(span.text.split())}'"
        if suggestion:
            msg += f" → {suggestion}"
        return Issue(
            code="NB401",
            name="complex-phrase",
            message=msg,
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
            severity=Severity.WARNING,
            suggestion=suggestion or None,
            text=span.text,
        )


class QualifierRule(_PhraseDictRule):
    code = "NB303"
    name = "qualifier"
    category = "word"
    codes = ("NB303",)

    def _phrase_keys(self) -> Iterable[str]:
        return qualifiers()

    def _issue_for(self, ctx: CheckContext, phrase: str, span) -> Issue:
        start = span.start_char
        end = span.end_char
        line, col = ctx.source.linecol(start)
        end_line, end_col = ctx.source.linecol(end)
        return Issue(
            code="NB303",
            name="qualifier",
            message=f"qualifier '{' '.join(span.text.split())}' — weakens the statement",
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
            severity=Severity.WARNING,
            text=span.text,
        )
