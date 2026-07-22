"""NB306 (repeated word) and NB307 (uncomparable) — classic usage slips.

NB306 catches the lexical illusion: the same word typed twice in a row ("the
the"), usually across a line break where the eye misses it. Doubles that are
grammatical English ("had had", "that that") are skipped, as are proper-noun
pairs ("Duran Duran", "Pago Pago") and runs of three or more, which read as
deliberate emphasis ("no no no").

NB307 catches a degree word on an absolute adjective — "very unique", "most
perfect". An uncomparable either holds or it doesn't; the intensifier weakens
the claim instead of strengthening it. Approximators ("almost impossible",
"nearly universal") are correct usage and not flagged.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..issue import Issue, Severity
from .base import CheckContext, Rule
from .clarity import _span_issue

# Grammatical or idiomatic doubles that are not typos.
_LEGIT_DOUBLES = frozenset({"had", "that"})

# Degree words that grade a quality. Approximators (almost, nearly, virtually)
# are deliberately absent — "almost impossible" is correct.
_COMPARATIVES = frozenset({"more", "most", "less", "least"})
_INTENSIFIERS = frozenset(
    {
        "very",
        "quite",
        "extremely",
        "somewhat",
        "rather",
        "really",
        "incredibly",
        "remarkably",
        "fairly",
        "pretty",
        "hugely",
        "tremendously",
    }
)

# Hard absolutes: any degree word is an error ("very unique", "more perfect").
_ABSOLUTES = frozenset(
    {
        "unique",
        "perfect",
        "impossible",
        "infinite",
        "eternal",
        "unanimous",
        "identical",
        "inevitable",
        "irrevocable",
        "unprecedented",
    }
)

# Soft absolutes: comparison is ordinary edited prose ("the most essential
# feature", "a more universal solution"), so only intensifiers fire.
_SOFT_ABSOLUTES = frozenset({"essential", "universal", "ideal", "ultimate", "absolute"})


class RepeatedWordRule(Rule):
    code = "NB306"
    name = "repeated-word"
    category = "word"
    codes = ("NB306",)

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        # spaCy emits standalone space tokens for newlines — exactly where the
        # illusion hides ("Paris in the / the spring") — so walk word tokens.
        words = [t for t in ctx.doc if not t.is_space]
        i = 0
        while i < len(words) - 1:
            tok, nxt = words[i], words[i + 1]
            if not (tok.is_alpha and nxt.is_alpha and tok.lower_ == nxt.lower_):
                i += 1
                continue
            # measure the whole run of the same word
            j = i + 1
            while (
                j + 1 < len(words) and words[j + 1].lower_ == tok.lower_ and words[j + 1].is_alpha
            ):
                j += 1
            run = j - i + 1
            if (
                run == 2
                and tok.lower_ not in _LEGIT_DOUBLES
                and not (tok.pos_ == "PROPN" and nxt.pos_ == "PROPN")
            ):
                start, end = tok.idx, nxt.idx + len(nxt.text)
                text = ctx.doc.text[start:end]
                flat = " ".join(text.split())
                yield _span_issue(
                    ctx,
                    "NB306",
                    self.name,
                    f"repeated word '{flat}' — delete one",
                    start,
                    end,
                    text,
                    Severity.WARNING,
                )
            i = j + 1


class UncomparableRule(Rule):
    code = "NB307"
    name = "uncomparable"
    category = "word"
    codes = ("NB307",)

    def __init__(self) -> None:
        self._matcher: Any = None

    def _build(self, nlp):
        from spacy.matcher import Matcher

        matcher = Matcher(nlp.vocab)
        matcher.add(
            self.code,
            [
                [
                    {"LOWER": {"IN": sorted(_COMPARATIVES | _INTENSIFIERS)}},
                    {"LEMMA": {"IN": sorted(_ABSOLUTES)}, "POS": "ADJ"},
                ],
                [
                    {"LOWER": {"IN": sorted(_INTENSIFIERS)}},
                    {"LEMMA": {"IN": sorted(_SOFT_ABSOLUTES)}, "POS": "ADJ"},
                ],
            ],
        )
        return matcher

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        if self._matcher is None:
            self._matcher = self._build(ctx.nlp)
        for _mid, start, end in self._matcher(ctx.doc):
            span = ctx.doc[start:end]
            degree, adj = span[0], span[-1]
            yield _span_issue(
                ctx,
                "NB307",
                self.name,
                f"uncomparable: '{adj.text}' is absolute — drop '{degree.text}'",
                span.start_char,
                span.end_char,
                span.text,
                Severity.WARNING,
            )
