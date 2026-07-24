"""NB7xx — style drift against an author profile.

These rules compare the draft with a recorded author signature (see
``styleprofile``) and flag what falls outside it. They are inert unless a
profile is active (``--style <name-or-path>`` / ``style`` in config): no
profile, no findings — so the rules can stay enabled by default.

The advice direction is always "come back to the author's distribution",
never "imitate harder": a connector the author doesn't use, a punctuation
mark far above their rate, rhythm flatter than their baseline. Small author
corpora are trusted less — absence-based findings need enough sentences to
make an absence meaningful.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from ..issue import Issue, Severity
from ..readability import burstiness, segment_lengths, sentence_lengths
from ..styleprofile import CONNECTORS, load_profile
from .base import CheckContext, Rule

if TYPE_CHECKING:
    pass


# An author's zero only counts as evidence when the corpus is big enough for
# the connector to have had a fair chance to appear.
_MIN_PROFILE_SENTENCES = 300
_MIN_PROFILE_WORDS = 5000


def _active_profile(ctx: CheckContext) -> dict | None:
    spec = getattr(ctx.config, "style", None)
    if not spec:
        return None
    try:
        return load_profile(spec)
    except ValueError:
        return None  # the CLI validates and reports the bad spec up front


class StyleConnectorRule(Rule):
    """NB701 — a sentence opens with a connector the author (almost) never uses.

    Strict absence is too strict on a large corpus — a versatile author has
    used every connector once somewhere. Below ~1 per 1000 sentences the
    connector is not part of the voice.
    """

    code = "NB701"
    name = "style-connector"
    category = "style"
    codes = ("NB701",)
    default_on = True
    severity = Severity.INFO

    _RARE_RATE = 1.0  # per 1000 sentences

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        profile = _active_profile(ctx)
        if profile is None or profile["corpus"]["sentences"] < _MIN_PROFILE_SENTENCES:
            return
        author = profile["connectors_per_1000_sentences"]
        favorites = ", ".join(list(author)[:3])
        name = profile["name"]
        for sent in ctx.doc.sents:
            tokens = [t for t in sent if not (t.is_punct or t.is_space)]
            if not tokens:
                continue
            two = " ".join(t.lower_ for t in tokens[:2])
            hit = next(
                (c for c in CONNECTORS if tokens[0].lower_ == c or two == c),
                None,
            )
            if hit is None or author.get(hit, 0.0) >= self._RARE_RATE:
                continue
            rarity = "almost never does" if author.get(hit) else "never does"
            span_tokens = tokens[: len(hit.split())]
            start = span_tokens[0].idx
            end = span_tokens[-1].idx + len(span_tokens[-1])
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(end)
            yield Issue(
                code="NB701",
                name="style-connector",
                message=(
                    f"style drift: '{hit}' opens a sentence — {name} {rarity}; "
                    f"their connectors: {favorites}"
                ),
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                text=ctx.doc.text[start:end],
            )


class StyleRhythmRule(Rule):
    """NB702 — rhythm noticeably flatter than the author's baseline.

    Only flatness fires: that is the machine-drift direction. A draft more
    varied than the author is not a defect.
    """

    code = "NB702"
    name = "style-rhythm"
    category = "style"
    codes = ("NB702",)
    default_on = True
    severity = Severity.INFO

    _MIN_SENTENCES = 6
    _FLAT_RATIO = 0.65

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        profile = _active_profile(ctx)
        if profile is None or profile["corpus"]["words"] < _MIN_PROFILE_WORDS:
            return
        lengths = sentence_lengths(ctx.doc)
        if len(lengths) < self._MIN_SENTENCES:
            return
        rhythm = profile["rhythm"]
        drifts = []
        cv = burstiness(lengths)
        if rhythm["sentence_cv"] and cv < self._FLAT_RATIO * rhythm["sentence_cv"]:
            drifts.append(f"sentence variety {cv:.2f} vs their {rhythm['sentence_cv']:.2f}")
        seg = burstiness(segment_lengths(ctx.doc))
        if rhythm["segment_cv"] and seg < self._FLAT_RATIO * rhythm["segment_cv"]:
            drifts.append(f"punctuation looseness {seg:.2f} vs their {rhythm['segment_cv']:.2f}")
        if not drifts:
            return
        yield Issue(
            code="NB702",
            name="style-rhythm",
            message=(
                f"style drift: rhythm flatter than {profile['name']}'s baseline "
                f"({'; '.join(drifts)}) — mix short and long, loosen the commas"
            ),
            line=1,
            col=1,
            end_line=1,
            end_col=1,
            severity=self.severity,
        )


class StylePunctuationRule(Rule):
    """NB703 — a punctuation mark used far above the author's rate."""

    code = "NB703"
    name = "style-punctuation"
    category = "style"
    codes = ("NB703",)
    default_on = True
    severity = Severity.INFO

    _MIN_COUNT = 3  # draft occurrences before a rate is worth comparing
    _RATIO = 3.0
    _MIN_EXCESS = 1.0  # per 1000 words
    _MAX_FINDINGS = 3

    _MARKS = {
        "em_dash": "—",
        "en_dash": "–",  # noqa: RUF001 - the en dash is the mark being counted
        "semicolon": ";",
        "colon": ":",
        "paren_open": "(",
        "question": "?",
        "exclamation": "!",
        "ellipsis": "…",
    }

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        profile = _active_profile(ctx)
        if profile is None or profile["corpus"]["words"] < _MIN_PROFILE_WORDS:
            return
        author = profile["punctuation_per_1000_words"]
        text = ctx.source.analysis_text
        n_words = sum(1 for t in ctx.doc if not (t.is_punct or t.is_space))
        if not n_words:
            return
        emitted = 0
        for mark_name, mark in self._MARKS.items():
            count = text.count(mark)
            if count < self._MIN_COUNT:
                continue
            rate = count * 1000 / n_words
            author_rate = author.get(mark_name, 0.0)
            if rate < self._RATIO * max(author_rate, 0.1) or rate - author_rate < self._MIN_EXCESS:
                continue
            times = f"{rate / author_rate:.0f}x their rate" if author_rate else "they barely use it"
            # document-level rate: anchor at the top so the quoted-material
            # filter can't swallow it when the first occurrence sits in a quote
            yield Issue(
                code="NB703",
                name="style-punctuation",
                message=(
                    f"style drift: {mark_name.replace('_', ' ')} {count}x at {rate:.1f}/1000 "
                    f"words vs {profile['name']}'s {author_rate:.1f} — {times}"
                ),
                line=1,
                col=1,
                end_line=1,
                end_col=1,
                severity=self.severity,
            )
            emitted += 1
            if emitted >= self._MAX_FINDINGS:
                return
