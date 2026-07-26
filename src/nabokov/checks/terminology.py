"""NB315 — exclusionary terms that have a settled replacement.

Off by default, and that is the design rather than caution. Every other rule in
nabokov points at something that makes prose harder to read; this one points at a
choice a project makes about its own language. Asserting it by default would be
the linter taking a position on the user's behalf, so it waits to be asked
(``--terminology``).

What earns an entry is an *agreed* replacement, not an objection. `whitelist` →
`allowlist` is settled across the IETF drafts, the kernel, and every major cloud
vendor. `crazy` → `surprising` is not settled, and entries like it are what get a
whole rule switched off — so they are absent, and the data file says so.

`master` on its own is absent for the same reason: it is a master's degree, a
master copy, mastering an API, and a branch name hard-coded in a million scripts.
Only the slave-paired sense is listed, because only that sense is unambiguous.

The fixes are the cleanest REPLACE tier in the ruleset — single tokens, same part
of speech, no reordering — so the inflected forms are listed separately
(`whitelisted`, `whitelisting`) rather than stemmed. A substitution that has to
guess at morphology is not a substitution.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data_loader import terminology
from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule, match_case
from .phrases import _resolve_overlaps


class TerminologyRule(Rule):
    code = "NB315"
    name = "exclusionary-term"
    category = "word"
    codes = ("NB315",)
    default_on = False
    severity = Severity.WARNING

    def __init__(self) -> None:
        self._matcher = None

    def _build(self, nlp):
        from spacy.matcher import PhraseMatcher

        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        matcher.add(self.code, [nlp.make_doc(term) for term in terminology()])
        return matcher

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        if self._matcher is None:
            self._matcher = self._build(ctx.nlp)
        terms = terminology()
        raw = [(start, end) for _mid, start, end in self._matcher(ctx.doc)]
        for start, end in _resolve_overlaps(raw):
            span = ctx.doc[start:end]
            key = " ".join(span.text.lower().split())
            alternatives = terms.get(key)
            if not alternatives:
                continue
            suggestion = ", ".join(match_case(a, span) for a in alternatives)
            line, col = ctx.source.linecol(span.start_char)
            end_line, end_col = ctx.source.linecol(span.end_char)
            yield Issue(
                code=self.code,
                name=self.name,
                message=f"exclusionary term '{span.text}'",
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                suggestion=suggestion,
                # Same part of speech, same shape, no reordering — the term comes
                # out and the replacement goes in.
                applicability=Applicability.REPLACE,
                text=span.text,
            )
