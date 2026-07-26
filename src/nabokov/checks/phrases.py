"""NB401 (complex/wordy phrases) and NB303 (qualifiers) via spaCy PhraseMatcher.

Both consume the bundled dictionaries. Matching is case-insensitive
(``attr="LOWER"``) and longest-phrase-wins per position: a match is
dropped if its tokens are already covered by a longer accepted match.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data_loader import complex_phrases, qualifier_fixes, qualifiers
from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule, deletion_is_safe, match_case


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
            if not self._keep(span):
                continue
            # Flatten the key: a span can wrap a line, and the dictionaries are
            # written with single spaces.
            yield self._issue_for(ctx, " ".join(span.text.lower().split()), span)

    def _keep(self, span) -> bool:
        """Hook for subclasses to veto a dictionary match from its context."""
        return True


class ComplexPhraseRule(_PhraseDictRule):
    code = "NB401"
    name = "complex-phrase"
    category = "phrase"
    codes = ("NB401",)

    def _phrase_keys(self) -> Iterable[str]:
        return complex_phrases().keys()

    def _issue_for(self, ctx: CheckContext, phrase: str, span) -> Issue:
        suggestions = complex_phrases().get(phrase, [])
        suggestion = ", ".join(match_case(s, span) for s in suggestions)
        start = span.start_char
        end = span.end_char
        line, col = ctx.source.linecol(start)
        end_line, end_col = ctx.source.linecol(end)
        return Issue(
            code="NB401",
            name="complex-phrase",
            message=f"wordy: '{' '.join(span.text.split())}'",
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
            severity=Severity.WARNING,
            suggestion=suggestion or None,
            # The dictionary alternatives are drop-in substitutions for the whole
            # phrase; where it lists several, the first is the default pick.
            applicability=Applicability.REPLACE if suggestion else Applicability.ADVISORY,
            text=span.text,
        )


def _prev_word(tok):
    for i in range(tok.i - 1, -1, -1):
        t = tok.doc[i]
        if not (t.is_space or t.is_punct):
            return t
    return None


def _next_word(tok):
    for i in range(tok.i + 1, len(tok.doc)):
        t = tok.doc[i]
        if not (t.is_space or t.is_punct):
            return t
    return None


class QualifierRule(_PhraseDictRule):
    code = "NB303"
    name = "qualifier"
    category = "word"
    codes = ("NB303",)

    def _phrase_keys(self) -> Iterable[str]:
        return qualifiers()

    def _keep(self, span) -> bool:
        # "just" is only a hedge in some positions. Restrictive "just one useful
        # insight" (= only), the imperative opener "Just tell me what to do", and
        # temporal "I'd just read it" (= recently) are precision devices — skip
        # them. The minimizer after a copula ("it's just a way to…") stays flagged.
        if len(span) != 1 or span.text.lower() != "just":
            return True
        tok = span[0]
        prev, nxt = _prev_word(tok), _next_word(tok)
        if prev is not None and prev.lemma_.lower() == "be":
            return True
        if nxt is None:
            return True
        restrictive = nxt.pos_ in ("DET", "NUM", "NOUN", "PROPN")
        imperative = tok.is_sent_start and nxt.tag_ == "VB"
        temporal = prev is not None and prev.pos_ == "AUX" and nxt.tag_ in ("VBN", "VBD")
        return not (restrictive or imperative or temporal)

    @staticmethod
    def _fix(phrase: str, span) -> tuple[str, Applicability]:
        """The fix for one hedge: what replaces it, and how safely.

        The negated hedges are the reason this is not a lookup. Cutting "I don't
        think" out of "I don't think we should ship" does not remove a hedge, it
        flips the claim — so those carry written guidance and never a
        substitution. Everything else is a cut or a shorter form, downgraded to
        REWRITE where the position makes the edit non-mechanical.
        """
        fixes = qualifier_fixes()
        guidance = fixes["rewrite"].get(phrase)
        if guidance is not None:
            return guidance, Applicability.REWRITE
        replacement = fixes["replace"].get(phrase)
        if replacement is not None:
            # Something takes the hedge's place, so only the capital is at stake.
            return match_case(replacement, span), Applicability.REPLACE
        if deletion_is_safe(span):
            return "", Applicability.REPLACE
        return "cut the hedge and keep the claim", Applicability.REWRITE

    def _issue_for(self, ctx: CheckContext, phrase: str, span) -> Issue:
        start = span.start_char
        end = span.end_char
        line, col = ctx.source.linecol(start)
        end_line, end_col = ctx.source.linecol(end)
        suggestion, applicability = self._fix(phrase, span)
        return Issue(
            code="NB303",
            name="qualifier",
            message=f"qualifier '{' '.join(span.text.split())}' — weakens the statement",
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
            severity=Severity.WARNING,
            suggestion=suggestion,
            applicability=applicability,
            text=span.text,
        )
