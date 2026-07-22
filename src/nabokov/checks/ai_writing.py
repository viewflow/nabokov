"""NB5xx — signs of AI writing.

Tells drawn from the Wikipedia "Signs of AI writing" reference (see
``data/ai_writing.json``). These are *tells, not proof*, and are
a separate concern from the core readability checks, so the whole NB5xx range is
**off by default** — enable it with ``--select NB5`` (AI checks only) or
``--extend-select NB5`` (alongside the core checks).

Rules (all off by default, all category "ai"):
  NB501 negation-contrast   NB502 puffery          NB503 editorializing (info)
  NB504 filler              NB505 transitions (info)  NB506 em-dash overuse
  NB507 rule-of-three (info)  NB508 emoji overuse  NB509 monotonous rhythm (info)
  NB510 intensifiers (info) NB511 participial closer (info)  NB512 repeated opener (info)
  NB513 curly quotes (info) NB514 title-case heading (info)  NB515 predicate hyphen (info)
  NB516 bold-label listicle (info)
"""

from __future__ import annotations

import bisect
import re
import statistics
from collections import Counter
from collections.abc import Iterable
from typing import Any

from ..data_loader import ai_writing
from ..issue import Issue, Severity
from .base import CheckContext, Rule
from .phrases import _resolve_overlaps

_NEGATION_PATTERNS = [
    re.compile(r"\bnot only\b[^.?!\n]{1,80}?\bbut\b", re.IGNORECASE),
    re.compile(r"\bnot just\b[^.?!\n]{1,80}?\bbut\b", re.IGNORECASE),
    re.compile(
        r"\b(?:it'?s|that'?s|this is|it is|there'?s)\s+not\b[^.?!\n]{1,60}?"
        r"[,—–-]\s*(?:it'?s|that'?s|it is|they'?re|but)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:isn'?t|aren'?t|wasn'?t|weren'?t)\b[^.?!\n]{1,60}?"
        r"[,—–-]\s*(?:it'?s|that'?s|it is|they'?re|but)\b",
        re.IGNORECASE,
    ),
    # "No fluff, no filler, just results." — the AI/marketing list-negation
    re.compile(
        r"\bno\b[^.?!\n,]{1,30},\s*no\b[^.?!\n,]{1,30},\s*(?:no|just)\b",
        re.IGNORECASE,
    ),
]

_EM_DASH = re.compile(r"—|(?<=\s)–(?=\s)")
# Human essayists reach ~11 em-dashes per 1000 words (measured on a corpus of Orwell,
# PG, Housel, SSC…), so overuse is a *density* above that, not an absolute count.
_EM_DASH_MIN = 3  # never flag fewer than a few
_EM_DASH_RATE = 12.0  # per 1000 words

# Common emoji blocks (pictographs, emoticons, transport, symbols, dingbats,
# regional indicators, and the ✅/❌/✔ marks that pepper AI-style READMEs).
_EMOJI = re.compile(
    "[\U0001f300-\U0001f5ff\U0001f600-\U0001f64f\U0001f680-\U0001f6ff"
    "\U0001f900-\U0001f9ff\U0001fa70-\U0001faff\U00002600-\U000026ff"
    "\U00002700-\U000027bf\U0001f1e6-\U0001f1ff]|[✅❌✔✖✨✳✴]"
)
_EMOJI_THRESHOLD = 3

# ", highlighting the importance" — the empty present-participle "significance" closer.
_PARTICIPIAL_CLOSER = re.compile(
    r",\s+(?:highlighting|underscoring|emphasi[sz]ing|reflecting|showcasing|"
    r"symboli[sz]ing|demonstrating|illustrating|signal(?:l)?ing|marking|cementing|"
    r"solidifying|reinforcing|showing|cementing|affirming)\b[^.?!\n]*",
    re.IGNORECASE,
)

# --- formatting tells (from blader/humanizer & unslop) ---
_CURLY_QUOTE = re.compile("[‘’“”]")
_STRAIGHT_QUOTE = re.compile(r"[\"']")
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*$", re.MULTILINE)
_HEADING_FUNCTION_WORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "nor",
        "of",
        "to",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "vs",
        "per",
        "via",
        "into",
        "onto",
        "over",
    ]
)
_PREDICATE_HYPHEN = re.compile(
    r"\b(?:is|are|was|were|be|been|being|seems?|seemed|looks?|looked|feels?|felt|"
    r"stays?|stayed|remains?|remained|becomes?|became)\s+"
    r"((?:cross|client|data|decision|well|high|real|long|end|cutting|state|full|"
    r"self|user|feature|first|second|third|multi|non|open|closed)-[a-z][a-z-]*)\b",
    re.IGNORECASE,
)
# "**Label:**" or "**Label**:" at the start of a line or bullet
_BOLD_LABEL = re.compile(
    r"^[ \t]*(?:[-*+]|\d+[.)])?[ \t]*(\*\*[^*\n]+?\*\*[ \t]*:|\*\*[^*\n]+?:[ \t]*\*\*)",
    re.MULTILINE,
)


def _issue(
    ctx: CheckContext,
    code: str,
    name: str,
    message: str,
    start: int,
    end: int,
    text: str,
    severity: Severity = Severity.WARNING,
):
    line, col = ctx.source.linecol(start)
    end_line, end_col = ctx.source.linecol(end)
    return Issue(
        code=code,
        name=name,
        message=message,
        line=line,
        col=col,
        end_line=end_line,
        end_col=end_col,
        severity=severity,
        text=text,
    )


class NegationContrastRule(Rule):
    code = "NB501"
    name = "ai-negation-contrast"
    category = "ai"
    codes = ("NB501",)
    default_on = False

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        seen: set[int] = set()
        for pattern in _NEGATION_PATTERNS:
            for m in pattern.finditer(text):
                if m.start() in seen:
                    continue
                seen.add(m.start())
                phrase = m.group(0)
                yield _issue(
                    ctx,
                    "NB501",
                    "ai-negation-contrast",
                    f"AI tell: negation-contrast '{phrase.strip()}'",
                    m.start(),
                    m.end(),
                    phrase.strip(),
                )


class EmDashRule(Rule):
    code = "NB506"
    name = "ai-em-dash"
    category = "ai"
    codes = ("NB506",)
    default_on = False

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        hits = list(_EM_DASH.finditer(text))
        words = sum(1 for t in ctx.doc if not (t.is_punct or t.is_space))
        if len(hits) < _EM_DASH_MIN or not words:
            return
        rate = len(hits) / words * 1000
        if rate < _EM_DASH_RATE:  # within the human range — not overuse
            return
        for m in hits:
            yield _issue(
                ctx,
                "NB506",
                "ai-em-dash",
                f"AI tell: em-dash overuse ({len(hits)} in {words} words, {rate:.0f}/1k)",
                m.start(),
                m.end(),
                m.group(0),
            )


class EmojiRule(Rule):
    code = "NB508"
    name = "ai-emoji"
    category = "ai"
    codes = ("NB508",)
    default_on = False

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        hits = list(_EMOJI.finditer(text))
        if len(hits) < _EMOJI_THRESHOLD:
            return
        for m in hits:
            yield _issue(
                ctx,
                "NB508",
                "ai-emoji",
                f"AI tell: emoji as formatting ({len(hits)} in this document)",
                m.start(),
                m.end(),
                m.group(0),
            )


class RuleOfThreeRule(Rule):
    """NB507 — three or more consecutive short sentence fragments on one line.

    The staccato "The jokes. The wins. The team." emphasis pattern the Reddit thread
    repeatedly named. Kept conservative: fragments must be <= 4 words, *verbless*,
    end in sentence punctuation, and sit on the same physical line. Short sentences
    with a verb ("Stop the orchestra. Solo that motif. Repeat it.") are deliberate
    human staccato, not the AI listicle tell — only noun fragments count.
    """

    code = "NB507"
    name = "ai-rule-of-three"
    category = "ai"
    codes = ("NB507",)
    default_on = False
    # The AI listicle staccato and the human anaphora ("No iPhone. No podcasts.
    # No music.") are formally identical — only intent separates them — so this
    # stays advisory for the judgment layer to decide.
    severity = Severity.INFO

    _MAX_WORDS = 4

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        sents = list(ctx.doc.sents)
        run: list = []
        results: list[list] = []

        def flush() -> None:
            if len(run) >= 3:
                results.append(run.copy())
            run.clear()

        newlines = [i for i, ch in enumerate(text) if ch == "\n"]

        def line_of(pos: int) -> int:
            return bisect.bisect_left(newlines, pos)

        for sent in sents:
            words = [t for t in sent if not (t.is_punct or t.is_space)]
            stripped = sent.text.strip()
            is_fragment = (
                1 <= len(words) <= self._MAX_WORDS
                and stripped[-1:] in ".!?"
                and not any(t.pos_ in ("VERB", "AUX") for t in sent)
            )
            # a run must sit on ONE physical line (staccato emphasis), so a bulleted
            # list of short items on separate lines is not flagged.
            same_line = bool(run) and line_of(run[-1].start_char) == line_of(sent.start_char)
            if is_fragment and (not run or same_line):
                run.append(sent)
            else:
                flush()
                if is_fragment:
                    run.append(sent)
        flush()

        for group in results:
            start = group[0].start_char
            end = group[-1].start_char + len(group[-1].text.rstrip())
            snippet = text[start:end]
            yield _issue(
                ctx,
                "NB507",
                "ai-rule-of-three",
                f"AI tell: rule-of-three staccato fragments ({len(group)} in a row)",
                start,
                end,
                snippet,
                severity=self.severity,
            )


def _in_code(ctx: CheckContext, pos: int) -> bool:
    """True if the original char at pos was blanked in the analysis text (code/markup).

    Lets rules that read the *original* markdown (headings, bold) skip matches inside
    code fences, which the analysis text blanks out.
    """
    original = ctx.source.original_text
    analysis = ctx.source.analysis_text
    return (
        pos < len(original)
        and not original[pos].isspace()
        and pos < len(analysis)
        and analysis[pos] == " "
    )


class CurlyQuoteRule(Rule):
    """NB513 — curly quotes intruding into mostly-straight text (inconsistency).

    Curly quotes alone are normal typography, so this fires only when they are the
    *minority* against straight quotes — the signature of an LLM snippet pasted into
    text the author typed with straight quotes.
    """

    code = "NB513"
    name = "ai-curly-quote"
    category = "ai"
    codes = ("NB513",)
    default_on = False
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        curly = list(_CURLY_QUOTE.finditer(text))
        if not curly:
            return
        straight = len(_STRAIGHT_QUOTE.findall(text))
        if len(curly) >= straight:  # consistent curly typography — not a tell
            return
        for m in curly:
            yield _issue(
                ctx,
                "NB513",
                "ai-curly-quote",
                f"AI tell: curly quote {m.group(0)!r} in mostly-straight text (inconsistent)",
                m.start(),
                m.end(),
                m.group(0),
                severity=self.severity,
            )


class TitleCaseHeadingRule(Rule):
    """NB514 — Title Case headings (a function word capitalized mid-heading gives it away)."""

    code = "NB514"
    name = "ai-title-case-heading"
    category = "ai"
    codes = ("NB514",)
    default_on = False
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.source.original_text
        for m in _HEADING.finditer(text):
            if _in_code(ctx, m.start(2)):
                continue
            words = m.group(2).split()
            if any(w.lower() in _HEADING_FUNCTION_WORDS and w[:1].isupper() for w in words[1:]):
                yield _issue(
                    ctx,
                    "NB514",
                    "ai-title-case-heading",
                    f"AI tell: Title Case heading '{m.group(2)}' (use sentence case)",
                    m.start(2),
                    m.end(2),
                    m.group(2),
                    severity=self.severity,
                )


class PredicateHyphenRule(Rule):
    """NB515 — a hyphenated compound used predicatively should drop the hyphen."""

    code = "NB515"
    name = "ai-predicate-hyphen"
    category = "ai"
    codes = ("NB515",)
    default_on = False
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        for m in _PREDICATE_HYPHEN.finditer(ctx.doc.text):
            compound = m.group(1)
            yield _issue(
                ctx,
                "NB515",
                "ai-predicate-hyphen",
                f"drop the hyphen in predicate position: '{compound}' → "
                f"'{compound.replace('-', ' ')}'",
                m.start(1),
                m.end(1),
                compound,
                severity=self.severity,
            )


class BoldListicleRule(Rule):
    """NB516 — a stack of "**Label:**" bold-header bullets (AI listicle formatting)."""

    code = "NB516"
    name = "ai-bold-listicle"
    category = "ai"
    codes = ("NB516",)
    default_on = False
    severity = Severity.INFO

    _THRESHOLD = 3

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.source.original_text
        hits = [m for m in _BOLD_LABEL.finditer(text) if not _in_code(ctx, m.start(1) + 2)]
        if len(hits) < self._THRESHOLD:
            return
        for m in hits:
            yield _issue(
                ctx,
                "NB516",
                "ai-bold-listicle",
                f"AI tell: bold-label listicle ({len(hits)} in this document)",
                m.start(1),
                m.end(1),
                m.group(1),
                severity=self.severity,
            )


class MonotonousRhythmRule(Rule):
    """NB509 — flat sentence rhythm (low burstiness).

    Humans vary sentence length; AI prose tends to be uniform. Measures the
    coefficient of variation (stdev / mean) of sentence word-counts. A low value on a
    long-enough document reads as machine-flat. Document-level, so it has no span.
    """

    code = "NB509"
    name = "ai-monotonous-rhythm"
    category = "ai"
    codes = ("NB509",)
    default_on = False
    severity = Severity.INFO

    _MIN_SENTENCES = 6
    _MIN_CV = 0.40

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        lengths = []
        for sent in ctx.doc.sents:
            words = [t for t in sent if not (t.is_punct or t.is_space)]
            if words:
                lengths.append(len(words))
        if len(lengths) < self._MIN_SENTENCES:
            return
        mean = sum(lengths) / len(lengths)
        if mean == 0:
            return
        cv = statistics.pstdev(lengths) / mean
        if cv < self._MIN_CV:
            yield Issue(
                code="NB509",
                name="ai-monotonous-rhythm",
                message=(
                    f"AI tell: monotonous sentence rhythm "
                    f"(burstiness {cv:.2f}, aim for >= {self._MIN_CV:.2f} by varying length)"
                ),
                line=1,
                col=1,
                end_line=1,
                end_col=1,
                severity=self.severity,
            )


class ParticipialCloserRule(Rule):
    """NB511 — empty present-participle "significance" closer."""

    code = "NB511"
    name = "ai-participial-closer"
    category = "ai"
    codes = ("NB511",)
    default_on = False
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        for m in _PARTICIPIAL_CLOSER.finditer(text):
            phrase = m.group(0).strip()
            yield _issue(
                ctx,
                "NB511",
                "ai-participial-closer",
                f"AI tell: participial 'significance' closer '{phrase}'",
                m.start(),
                m.end(),
                phrase,
                severity=self.severity,
            )


class RepeatedOpenerRule(Rule):
    """NB512 — three or more consecutive sentences that open with the same word."""

    code = "NB512"
    name = "ai-repeated-opener"
    category = "ai"
    codes = ("NB512",)
    default_on = False
    severity = Severity.INFO

    _MIN_RUN = 3

    @staticmethod
    def _opener(sent) -> str | None:
        for tok in sent:
            if not (tok.is_punct or tok.is_space):
                return tok.text.lower()
        return None

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        sents = list(ctx.doc.sents)
        openers = [self._opener(s) for s in sents]
        n = len(sents)
        i = 0
        while i < n:
            if openers[i] is None:
                i += 1
                continue
            j = i + 1
            while j < n and openers[j] == openers[i]:
                j += 1
            if j - i >= self._MIN_RUN:
                group = sents[i:j]
                start = group[0].start_char
                end = group[-1].start_char + len(group[-1].text.rstrip())
                word = next((t.text for t in group[0] if not (t.is_punct or t.is_space)), "")
                yield _issue(
                    ctx,
                    "NB512",
                    "ai-repeated-opener",
                    f"AI tell: {j - i} sentences in a row open with '{word}'",
                    start,
                    end,
                    text[start:end][:80],
                    severity=self.severity,
                )
            i = j


class _ListRule(Rule):
    """A rule backed by a list of terms (single words matched by lemma, phrases exact)."""

    default_on = False

    def __init__(self) -> None:
        self._phrase_matcher: Any = None
        self._word_matcher: Any = None

    def _terms(self) -> list[str]:  # pragma: no cover - overridden
        raise NotImplementedError

    def _message(self, text: str) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def _build(self, nlp):
        from spacy.matcher import Matcher, PhraseMatcher

        terms = self._terms()
        phrases = [t for t in terms if " " in t]
        singles = [t for t in terms if " " not in t]
        pm = PhraseMatcher(nlp.vocab, attr="LOWER")
        if phrases:
            pm.add(self.code, [nlp.make_doc(p) for p in phrases])
        wm = Matcher(nlp.vocab)
        for word in singles:
            wm.add(self.code, [[{"LEMMA": word.lower()}], [{"LOWER": word.lower()}]])
        return pm, wm

    def _spans(self, ctx: CheckContext):
        if self._phrase_matcher is None:
            self._phrase_matcher, self._word_matcher = self._build(ctx.nlp)
        raw: list[tuple[int, int]] = []
        if len(self._phrase_matcher):
            raw += [(s, e) for _mid, s, e in self._phrase_matcher(ctx.doc)]
        if len(self._word_matcher):
            raw += [(s, e) for _mid, s, e in self._word_matcher(ctx.doc)]
        return [ctx.doc[start:end] for start, end in _resolve_overlaps(raw)]

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        for span in self._spans(ctx):
            yield _issue(
                ctx,
                self.code,
                self.name,
                self._message(span.text),
                span.start_char,
                span.end_char,
                span.text,
                severity=self.severity,
            )


class PufferyRule(_ListRule):
    code = "NB502"
    name = "ai-puffery"
    category = "ai"
    codes = ("NB502",)

    # Puffery is decoration, and decoration is rare. A lemma the document keeps
    # repeating ("optimize" in an essay about optimization) is its topic vocabulary,
    # so those findings drop to info for the author to judge. Short documents reach
    # topical at 2 uses — twice in a few hundred words is a subject, not garnish.
    _TOPICAL_USES = 3
    _SHORT_DOC_WORDS = 1000

    def _terms(self) -> list[str]:
        return ai_writing()["puffery"]

    def _message(self, text: str) -> str:
        return f"AI tell: puffery '{text}'"

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        spans = self._spans(ctx)
        lemma_counts = Counter(self._lemma_key(span) for span in spans)
        doc_words = sum(1 for t in ctx.doc if not (t.is_punct or t.is_space))
        threshold = self._TOPICAL_USES if doc_words >= self._SHORT_DOC_WORDS else 2
        for span in spans:
            count = lemma_counts[self._lemma_key(span)]
            topical = count >= threshold
            message = self._message(span.text)
            if topical:
                message += f" (used {count}× — likely topic vocabulary)"
            yield _issue(
                ctx,
                self.code,
                self.name,
                message,
                span.start_char,
                span.end_char,
                span.text,
                severity=Severity.INFO if topical else self.severity,
            )

    @staticmethod
    def _lemma_key(span) -> str:
        return " ".join(tok.lemma_.lower() for tok in span)


class EditorializingRule(_ListRule):
    code = "NB503"
    name = "ai-editorializing"
    category = "ai"
    codes = ("NB503",)
    severity = Severity.INFO

    def _terms(self) -> list[str]:
        return ai_writing()["editorializing"]

    def _message(self, text: str) -> str:
        return f"AI tell: editorializing '{text}'"


class FillerRule(_ListRule):
    code = "NB504"
    name = "ai-filler"
    category = "ai"
    codes = ("NB504",)

    def _terms(self) -> list[str]:
        return ai_writing()["filler"]

    def _message(self, text: str) -> str:
        return f"AI tell: conversational filler '{text}'"


class TransitionRule(_ListRule):
    code = "NB505"
    name = "ai-transition"
    category = "ai"
    codes = ("NB505",)
    severity = Severity.INFO

    def _terms(self) -> list[str]:
        return ai_writing()["transitions"]

    def _message(self, text: str) -> str:
        return f"AI tell: overused transition '{text}'"


class VocabClusterRule(_ListRule):
    """NB517 — clustered generic-praise vocabulary.

    Tier-2 of the AI-vocabulary taxonomy: words that are perfectly normal alone
    ("significant", "effective") but that LLMs sprinkle in clusters. A single
    use is never flagged; two or more *distinct* words from the list inside one
    paragraph is the tell. Advisory — dense human academic prose clusters too.
    """

    code = "NB517"
    name = "ai-vocab-cluster"
    category = "ai"
    codes = ("NB517",)
    severity = Severity.INFO

    _MIN_DISTINCT = 2

    def _terms(self) -> list[str]:
        return ai_writing()["vocab_tier2"]

    def _message(self, text: str) -> str:
        return f"AI tell: generic-praise cluster '{text}' (2+ in this paragraph)"

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        from .base import paragraph_ranges

        spans = self._spans(ctx)
        if not spans:
            return
        paragraphs = paragraph_ranges(ctx.doc.text)

        def para_of(span) -> int:
            for idx, (start, end) in enumerate(paragraphs):
                if start <= span.start_char < end:
                    return idx
            return -1

        by_para: dict[int, list] = {}
        for span in spans:
            by_para.setdefault(para_of(span), []).append(span)
        for group in by_para.values():
            distinct = {span.lemma_.lower() for span in group}
            if len(distinct) < self._MIN_DISTINCT:
                continue
            for span in group:
                yield _issue(
                    ctx,
                    self.code,
                    self.name,
                    self._message(span.text),
                    span.start_char,
                    span.end_char,
                    span.text,
                    severity=self.severity,
                )


class IntensifierRule(_ListRule):
    code = "NB510"
    name = "ai-intensifier"
    category = "ai"
    codes = ("NB510",)
    severity = Severity.INFO

    def _terms(self) -> list[str]:
        return ai_writing()["intensifiers"]

    def _message(self, text: str) -> str:
        return f"AI tell: weak intensifier '{text}' — cut it or be specific"
