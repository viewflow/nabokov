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
  NB516 bold-label listicle (info)  NB522 engagement-bait closer (info)
  NB523 anaphora triad (info)  NB524 contrast heading (info)
"""

from __future__ import annotations

import bisect
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

from ..data_loader import ai_writing
from ..issue import Issue, Severity
from ..readability import burstiness, burstiness_thresholds, sentence_lengths
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
    # split-sentence form: the negation and the correction in two sentences —
    # "The headline isn't the speed. The real story is Y."
    re.compile(
        r"\b(?:isn'?t|aren'?t|wasn'?t|weren'?t|is not|are not)\b[^.?!\n]{0,60}[.!]\s+"
        r"(?:The|Its|It'?s)\s+(?:real|actual|true)\b",
        re.IGNORECASE,
    ),
    # multi-negation countdown: "It's not the price. It's not the features.
    # It's the trust."
    re.compile(
        r"\b(?:it|that)(?:'?s| is) not\b[^.?!\n]{1,40}\.\s+"
        r"(?:it|that)(?:'?s| is) not\b[^.?!\n]{1,40}\.\s+"
        r"(?:it|that)(?:'?s| is)\b",
        re.IGNORECASE,
    ),
]

# The "no longer" reframe: the same third-person subject renamed across two
# sentences — "They're no longer entertainment. They're market research." The
# second sentence must reopen with the SAME subject + a copula (the predicate
# swap is the tell); "It's no longer maintained. It gets no updates." is plain
# reporting and does not fire. First person is excluded — "I'm no longer at
# Google. I'm at a startup" is ordinary autobiography. Advisory: the shape is
# also legitimate human rhetoric, so the judgment layer decides.
#
# The "doesn't mean" reframe is the same move on a definition: "Market research
# doesn't have to mean spreadsheets. Sometimes it means listening." Both halves
# are required — negate the expected meaning, then reveal the real one with a
# repeated "mean(s)". The bare negation is ordinary human prose (PG: "Writing
# essays doesn't have to mean publishing them.") and never fires; the completed
# couplet has zero occurrences across the 125k-word calibration corpus.
_NEGATION_PATTERNS_INFO = [
    (
        "'no longer' reframe",
        re.compile(
            r"\b(they|it|that|this|he|she|these|those)(?:['’](?:re|s))?"
            r"(?:\s+(?:is|are|was|were))?\s+no longer\b[^.?!\n]{1,60}[.!]\s+"
            r"\1(?:['’](?:re|s)|\s+(?:is|are|was|were))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "'doesn't mean' reframe",
        re.compile(
            r"\b(?:doesn'?t|does not|don'?t|do not)\s+(?:have to\s+)?mean\b"
            r"[^.?!\n]{1,60}[.!]\s+"
            r"(?:sometimes\s+)?(?:it|that|this)\s+(?:can\s+|often\s+|sometimes\s+)?means?\b",
            re.IGNORECASE,
        ),
    ),
    # The appearance-verdict couplet: a short "how it looks" sentence followed by
    # a short declarative verdict — "This feels pointless. It is not." / "This
    # feels useful. In my experience it backfires." The capitalized opener stands
    # in for a sentence boundary; commas are barred from the appearance half
    # (spoken replies carry them: "That sounds about right, yeah."), a colon from
    # the verdict (dialogue labels), and "looks at/into/through" is inspection,
    # not appearance. A question follow-up is exempt — V. Nabokov's "This seems
    # perfect. But is it?" is the lone near-hit across the 125k-word calibration
    # corpus, and the [.!] terminator excludes it: zero corpus hits.
    (
        "appearance-verdict couplet",
        re.compile(
            r"\b(?:This|That|It)\s+(?:(?:may|might|can|could)\s+)?"
            r"(?i:feels?|seems?|looks?|sounds?)(?!\s+(?:at|into|through)\b)\b"
            r"[^.?!,\n]{0,40}[.!]\s+"
            r"[^.?!:\n]{1,50}[.!]"
        ),
    ),
    # The negation→role-reveal couplet: negate an obligation, then reveal the
    # subject's "real" function in the next sentence — "A skill does not need
    # to teach it. Its job is activation." Anchored on both halves: a negated
    # need/have-to plus a possessive role-noun copula ("Its job is", "Their
    # purpose is"). The bare negation or the bare role sentence is ordinary
    # prose and never fires; the completed couplet has zero occurrences across
    # 361k words of Emerson, Chesterton, Dickens, and Thoreau.
    (
        "negation → role reveal",
        re.compile(
            r"\b(?:doesn['’]?t|does not|don['’]?t|do not)\s+(?:need|have)\s+to\b"
            r"[^.?!\n]{0,50}[.!]\s+"
            r"(?:Its|Their)\s+(?:real\s+)?(?:job|point|role|purpose|task|value)\s+(?:is|was)\b"
        ),
    ),
]

# "could potentially", "may eventually" — a modal stacked with a hedge adverb;
# each cancels the other, leaving a sentence that asserts nothing.
_HEDGE_STACK = re.compile(
    r"\b(?:could|may|might|would)\s+(?:potentially|eventually|ultimately|possibly|"
    r"perhaps|conceivably)\b",
    re.IGNORECASE,
)

# Fingerprints, not tells: chat-UI citation tokens, AI-tool URL parameters,
# unfilled template placeholders, and knowledge-cutoff disclaimers. Their
# presence is near-proof of an unedited paste. (Adapted from
# conorbronsdon/avoid-ai-writing and Aboudjem/humanizer-skill, MIT.)
_AI_ARTIFACTS = [
    (
        "chat citation markup",
        re.compile(
            r"citeturn\d\w*|oai_?cit\w*|contentReference\[oaicite:\d+\]\{index=\d+\}"
            r"|grok_card|grok_render_citation_card_json|\[attached_file:\d+\]"
            r"|ppl-ai-file-upload|\[span_\d+\]|\[(?:start|end)_span\]"
        ),
    ),
    (
        "AI-tool URL parameter",
        re.compile(
            r"(?:utm_source|referrer)=(?:chatgpt\.com|copilot\.com|openai|claude\.ai|perplexity\.ai|grok\.com)"
        ),
    ),
    (
        "unfilled placeholder",
        re.compile(
            r"\[(?:Your|Insert|Add|Enter|Describe|Specify|Choose)\b[^\]\n]{2,60}\]|\b\d{4}-XX-XX\b"
        ),
    ),
    (
        "knowledge-cutoff disclaimer",
        re.compile(
            r"as of my (?:last|latest) (?:update|training)|my knowledge cutoff|i (?:do not|don'?t) have access to real[- ]time",
            re.IGNORECASE,
        ),
    ),
]

# A spaced hyphen ("word - word") is the ASCII spelling of the same dash; the
# "\S " lookbehind keeps list bullets at line starts out of the count.
_EM_DASH = re.compile(r"—|(?<=\s)–(?=\s)|(?<=\S )-(?= )")
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
        # one finding per stretch of text: a match whose span overlaps an
        # earlier one is the same tell caught twice (warning patterns run
        # first, so they win over the advisory reframes)
        seen: list[tuple[int, int]] = []

        def fresh(start: int, end: int) -> bool:
            if any(start < e and s < end for s, e in seen):
                return False
            seen.append((start, end))
            return True

        for pattern in _NEGATION_PATTERNS:
            for m in pattern.finditer(text):
                if not fresh(m.start(), m.end()):
                    continue
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
        for label, pattern in _NEGATION_PATTERNS_INFO:
            for m in pattern.finditer(text):
                if not fresh(m.start(), m.end()):
                    continue
                phrase = m.group(0)
                yield _issue(
                    ctx,
                    "NB501",
                    "ai-negation-contrast",
                    f"AI tell: {label} '{phrase.strip()}'",
                    m.start(),
                    m.end(),
                    phrase.strip(),
                    severity=Severity.INFO,
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
    """NB516 — a stack of "**Label:**" bold-header bullets (AI listicle formatting).

    Also flags the label-period tell: ``**Intros.** gloss text`` where a human
    writes ``**Intros:**`` — the colon says "here's what this label means"; the
    period reads as a sentence the following clause then contradicts. That one
    fires per item, no stack needed.
    """

    code = "NB516"
    name = "ai-bold-listicle"
    category = "ai"
    codes = ("NB516",)
    default_on = False
    severity = Severity.INFO

    _THRESHOLD = 3
    # "- **Intros.** gloss" — a short bold noun-phrase label ended with a period
    _LABEL_PERIOD = re.compile(
        r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+(\*\*[^*\n:]{2,40}\.\*\*)[ \t]+\S", re.MULTILINE
    )

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.source.original_text
        hits = [m for m in _BOLD_LABEL.finditer(text) if not _in_code(ctx, m.start(1) + 2)]
        if len(hits) >= self._THRESHOLD:
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
        for m in self._LABEL_PERIOD.finditer(text):
            if _in_code(ctx, m.start(1) + 2):
                continue
            yield _issue(
                ctx,
                "NB516",
                "ai-bold-listicle",
                f"AI tell: bold label ends with a period — a human writes '{m.group(1)[:-3]}:**'",
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

    The threshold is per target (short-form registers tolerate flatter rhythm), and
    a genuinely robotic rhythm (below the ``flat`` cutoff) escalates from advisory to
    a warning — badly-flat is the equivalent of a very-hard sentence.
    """

    code = "NB509"
    name = "ai-monotonous-rhythm"
    category = "ai"
    codes = ("NB509",)
    default_on = False
    severity = Severity.INFO

    _MIN_SENTENCES = 6

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        lengths = sentence_lengths(ctx.doc)
        if len(lengths) < self._MIN_SENTENCES:
            return
        cv = burstiness(lengths)
        min_cv, flat_cv = burstiness_thresholds(ctx.config.target)
        if cv >= min_cv:
            return
        severity = Severity.WARNING if cv < flat_cv else Severity.INFO
        yield Issue(
            code="NB509",
            name="ai-monotonous-rhythm",
            message=(
                f"AI tell: monotonous sentence rhythm "
                f"(burstiness {cv:.2f}, aim for >= {min_cv:.2f} by varying length)"
            ),
            line=1,
            col=1,
            end_line=1,
            end_col=1,
            severity=severity,
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


class ParagraphOpenerRule(Rule):
    """NB521 — the same coordinating conjunction opens 3+ paragraphs.

    "And" (or But/So/Yet/Or) opening a paragraph is a deliberate rhetorical move —
    humans use it sparingly and vary the word: across the calibration corpus
    (Stripe, Linear, 37signals, Vercel, PG, Orwell, Housel …) no document opens
    more than 2 paragraphs with the same coordinator, even where DHH opens 29% of
    paragraphs with *mixed* ones. AI drafts ride a single "And…" into every other
    paragraph. Flag when one coordinator opens >= 3 paragraphs and >= 10% of them.
    """

    code = "NB521"
    name = "ai-paragraph-opener"
    category = "ai"
    codes = ("NB521",)
    default_on = False
    severity = Severity.WARNING

    _COORD = {"and", "but", "so", "yet", "or"}
    _MIN_COUNT = 3
    _MIN_SHARE = 0.10
    _PARA = re.compile(r"(?:^|\n)[ \t]*\n[ \t]*(?=\S)|^\s*(?=\S)")
    _WORD = re.compile(r"[A-Za-z']+")

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        paragraphs: list[tuple[int, str]] = []  # (offset of first word, lowered word)
        for m in self._PARA.finditer(text):
            word = self._WORD.match(text, m.end())
            if word:
                paragraphs.append((word.start(), word.group().lower()))
        if not paragraphs:
            return
        counts = Counter(w for _, w in paragraphs if w in self._COORD)
        for opener, count in counts.items():
            if count < self._MIN_COUNT or count / len(paragraphs) < self._MIN_SHARE:
                continue
            for start, word in paragraphs:
                if word != opener:
                    continue
                end = start + len(word)
                yield _issue(
                    ctx,
                    "NB521",
                    "ai-paragraph-opener",
                    f"AI tell: {count} paragraphs open with '{text[start:end]}' — "
                    "vary or merge into the previous paragraph",
                    start,
                    end,
                    text[start:end],
                    severity=self.severity,
                )


class _ListRule(Rule):
    """A rule backed by a list of terms (single words matched by lemma, phrases exact).

    A term caught inside one of ``_exception_terms()`` is dropped: fixed
    expressions where the word loses its tell-sense ("quite a few",
    "test harness", "a great question" in reported speech). Quoted material is
    handled downstream — the analyzer drops findings inside quoted regions.
    """

    default_on = False

    def __init__(self) -> None:
        self._phrase_matcher: Any = None
        self._word_matcher: Any = None
        self._exception_matcher: Any = None

    def _terms(self) -> list[str]:  # pragma: no cover - overridden
        raise NotImplementedError

    def _exception_terms(self) -> list[str]:
        return []

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
        em = PhraseMatcher(nlp.vocab, attr="LOWER")
        exceptions = self._exception_terms()
        if exceptions:
            em.add(self.code, [nlp.make_doc(p) for p in exceptions])
        return pm, wm, em

    def _spans(self, ctx: CheckContext):
        if self._phrase_matcher is None:
            self._phrase_matcher, self._word_matcher, self._exception_matcher = self._build(ctx.nlp)
        raw: list[tuple[int, int]] = []
        if len(self._phrase_matcher):
            raw += [(s, e) for _mid, s, e in self._phrase_matcher(ctx.doc)]
        if len(self._word_matcher):
            raw += [(s, e) for _mid, s, e in self._word_matcher(ctx.doc)]
        excluded: list[tuple[int, int]] = []
        if len(self._exception_matcher):
            excluded = [(s, e) for _mid, s, e in self._exception_matcher(ctx.doc)]
        return [
            ctx.doc[start:end]
            for start, end in _resolve_overlaps(raw)
            if not any(s <= start and end <= e for s, e in excluded)
        ]

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

    # Lemmas whose tell-sense is the verb only: "harness the power" vs "test
    # harness", "foster innovation" vs "foster child" — the noun/adjective
    # readings are ordinary English, not decoration.
    _VERB_ONLY = frozenset({"harness", "foster"})

    def _terms(self) -> list[str]:
        return ai_writing()["puffery"]

    def _exception_terms(self) -> list[str]:
        return ai_writing()["puffery_exceptions"]

    def _message(self, text: str) -> str:
        return f"AI tell: puffery '{text}'"

    @classmethod
    def _noun_sense(cls, tok) -> bool:
        if tok.lemma_.lower() not in cls._VERB_ONLY:
            return False
        # Sentence-initial imperatives ("Harness the power…") mis-tag NOUN or
        # PROPN, but they still carry a direct object — a real noun never does.
        if any(child.dep_ in ("dobj", "obj") for child in tok.children):
            return False
        return tok.pos_ != "VERB"

    def _spans(self, ctx: CheckContext):
        return [
            span
            for span in super()._spans(ctx)
            if not (len(span) == 1 and self._noun_sense(span[0]))
        ]

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

    def _exception_terms(self) -> list[str]:
        # An article in front turns the chatbot opener into reported speech
        # ("she asked a great question") and "full stop" into the British
        # punctuation mark ("end with a full stop").
        return ai_writing()["filler_exceptions"]

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


class AiArtifactRule(Rule):
    """NB519 — AI artifacts: fingerprints, not tells.

    Chat-UI citation tokens (``citeturn0search0``, ``oaicite``), AI-tool URL
    parameters (``utm_source=chatgpt.com``), unfilled template placeholders
    (``[Your Name]``), and knowledge-cutoff disclaimers ("as of my last
    update"). Unlike every other NB5xx signal these are near-proof of an
    unedited paste, so they warn without any density gating. Scans the
    *original* text — URLs are blanked in the analysis text for Markdown.
    """

    code = "NB519"
    name = "ai-artifact"
    category = "ai"
    codes = ("NB519",)
    default_on = False

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.source.original_text
        for kind, pattern in _AI_ARTIFACTS:
            for m in pattern.finditer(text):
                yield _issue(
                    ctx,
                    "NB519",
                    "ai-artifact",
                    f"AI artifact: {kind} '{m.group(0)}' — near-proof of an unedited paste",
                    m.start(),
                    m.end(),
                    m.group(0),
                )


class HedgeStackRule(Rule):
    """NB520 — a modal stacked with a hedge adverb ("could potentially").

    Either word alone is honest hedging; the stack asserts nothing while
    sounding cautious. The fix is to pick one.
    """

    code = "NB520"
    name = "ai-hedge-stack"
    category = "ai"
    codes = ("NB520",)
    default_on = False

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        for m in _HEDGE_STACK.finditer(ctx.doc.text):
            yield _issue(
                ctx,
                "NB520",
                "ai-hedge-stack",
                f"AI tell: stacked hedge '{m.group(0)}' — pick one, the pair asserts nothing",
                m.start(),
                m.end(),
                m.group(0),
            )


class AdjectiveTriadRule(Rule):
    """NB518 — the symmetry attractor: coordinated adjective triads.

    "innovative, transformative, and groundbreaking" — the LLM reflex of pressing
    every enumeration into a balanced triple. The tricolon is also 2,000 years of
    legitimate rhetoric and factual three-item lists are normal, so this is a
    *density* tell: essayists run well under 0.5 triads per 1000 words (measured
    on the corpus); the reflex shows at 1.5+/1000. Advisory even then.
    Human prose varies enumeration size — two for contrast, four for abundance.
    """

    code = "NB518"
    name = "ai-adjective-triad"
    category = "ai"
    codes = ("NB518",)
    default_on = False
    severity = Severity.INFO

    _MIN_TRIADS = 2
    _RATE = 1.5  # triads per 1000 words

    # A triad launched by a copula-colon ("…the real signal is: spontaneous,
    # unfiltered, and impossible to fake") bypasses the density gate: humans
    # write colon-reveal lists behind a noun ("three things: X, Y, and Z") but
    # style guides bar a colon straight after "is" — zero occurrences across
    # the calibration corpus — while LLM broetry leans on exactly that shape.
    _COPULA_COLON = re.compile(r"\b(?:is|are|was|were)\s*:\s*$")

    _CONTENT = ("ADJ", "NOUN", "VERB")

    def _triads(self, ctx: CheckContext):
        # Surface scan — the sm model's parse of "X, Y, and Z" adjective chains
        # is unstable (amod/attr/conj vary with context), so match the token
        # shape directly: ADJ , content-word [,] and/or content-word. The first
        # element must be a confirmed ADJ (an appositive comma after a noun is a
        # clause boundary, not a list); the later two tolerate the model's
        # mis-tags ("transformative" as NOUN). All within one sentence.
        doc = ctx.doc
        toks = [t for t in doc if not t.is_space]
        triads = []
        for idx in range(len(toks) - 4):
            window = toks[idx : idx + 6]
            a, comma = window[0], window[1]
            if a.pos_ != "ADJ" or comma.text != ",":
                continue
            b = window[2]
            if b.pos_ not in self._CONTENT:
                continue
            rest = window[3:]
            if rest[0].text == ",":
                rest = rest[1:]
            if len(rest) < 2 or rest[0].pos_ != "CCONJ" or rest[1].pos_ not in self._CONTENT:
                continue
            c = rest[1]
            group = (a, b, c)
            if a.sent != c.sent:
                continue
            # exclude longer enumerations: a comma/conjunction right before or
            # a continuing list right after means this is not a triple
            prev = doc[a.i - 1] if a.i else None
            if prev is not None and (prev.text == "," or prev.pos_ == "CCONJ"):
                continue
            nxt = doc[c.i + 1] if c.i + 1 < len(doc) else None
            if nxt is not None and nxt.text == ",":
                continue
            triads.append(group)
        return triads

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        triads = self._triads(ctx)
        words = sum(1 for t in ctx.doc if not (t.is_punct or t.is_space))
        text = ctx.doc.text
        dense = (
            len(triads) >= self._MIN_TRIADS
            and words
            and len(triads) / words * 1000 >= self._RATE
        )
        for group in triads:
            start = group[0].idx
            reveal = bool(self._COPULA_COLON.search(text, 0, start))
            if not (dense or reveal):
                continue
            end = group[-1].idx + len(group[-1].text)
            snippet = " ".join(text[start:end].split())
            message = (
                f"AI tell: colon-reveal triad '{snippet}' — a colon straight "
                "after a copula launching a balanced triple"
                if reveal
                else f"AI tell: adjective triad '{snippet}' — vary enumeration size "
                "(two for contrast, four for abundance)"
            )
            yield _issue(
                ctx,
                self.code,
                self.name,
                message,
                start,
                end,
                text[start:end],
                severity=self.severity,
            )


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

    # Emphatic "very" heads that never take the degree reading: superlatives
    # carry tag JJS ("the very best/least/most"), and these ordinal-like
    # adjectives tag plain JJ ("the very first time", "the very same bug").
    _EMPHATIC_HEAD_LEMMAS = frozenset({"first", "last", "next", "same"})

    def _terms(self) -> list[str]:
        return ai_writing()["intensifiers"]

    def _exception_terms(self) -> list[str]:
        # Fixed expressions where the word is not a degree intensifier:
        # "quite a few" is a quantity idiom, "simply put" a discourse marker.
        return ai_writing()["intensifier_exceptions"]

    def _message(self, text: str) -> str:
        return f"AI tell: weak intensifier '{text}' — cut it or be specific"

    def _skip(self, tok) -> bool:
        # "Very" the emphatic adjective (= "exact") is not a degree word.
        # spaCy tags the noun-modifying reading ADJ ("the very beginning");
        # before a superlative or ordinal it tags ADV but the degree reading
        # is ungrammatical there ("*very biggest"), so those are idioms too.
        if tok.lower_ != "very":
            return False
        return (
            tok.pos_ == "ADJ"
            or tok.head.tag_ == "JJS"
            or tok.head.lemma_.lower() in self._EMPHATIC_HEAD_LEMMAS
        )

    def _spans(self, ctx: CheckContext):
        return [
            span for span in super()._spans(ctx) if not (len(span) == 1 and self._skip(span[0]))
        ]


class EngagementBaitRule(Rule):
    """NB522 — engagement-bait closer: the document signs off with a broad
    second-person superlative question ("What's the most unexpected place
    you've found genuine customer insight?").

    The algorithmic-reach CTA that closes LLM-drafted social posts. Humans
    growth-hack with the same shape, so this flags *engagement bait*, not AI —
    advisory for the judgment layer (NB507's logic). The pattern needs a
    superlative (or "your favorite"), a "you" + verb clause, and a question
    mark ending the final paragraph — "What's the best way to reach you?" has
    no verb after "you" and stays clean. Zero hits across the calibration
    corpus.
    """

    code = "NB522"
    name = "ai-engagement-bait"
    category = "ai"
    codes = ("NB522",)
    default_on = False
    severity = Severity.INFO

    _CLOSER = re.compile(
        r"(?:^|[.!?]\s+)(what(?:['’]s| is| was)\s+"
        r"(?:the\s+(?:most|best|biggest|worst)|your\s+favou?rite)\b"
        r"[^?\n]{0,80}\byou(?:['’](?:ve|re|d))?\s+[a-z][^?\n]{0,60}\?)\s*$",
        re.IGNORECASE,
    )

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text.rstrip()
        if not text:
            return
        cut = text.rfind("\n\n")
        para_start = cut + 2 if cut != -1 else 0
        m = self._CLOSER.search(text[para_start:])
        if not m:  # the regex is $-anchored, so a hit is the document's last word
            return
        phrase = m.group(1)
        yield _issue(
            ctx,
            "NB522",
            "ai-engagement-bait",
            f"AI tell: engagement-bait closer '{phrase}' — the algorithmic-reach "
            "CTA question; end on your point instead",
            para_start + m.start(1),
            para_start + m.end(1),
            phrase,
            severity=self.severity,
        )


class AnaphoraTriadRule(Rule):
    """NB523 — in-sentence anaphora triad: the same quantifier opening three
    coordinated phrases — "more code reviews, more reports, and more style
    guides".

    The sibling of NB507's staccato fragments and NB518's adjective triads:
    the symmetry attractor applied to a comparative. Emerson, Dickens, and
    Thoreau all use the shape deliberately (8 hits across 361k words,
    ~0.02/1000 — Emerson's "every secret is told, every crime is punished"),
    so like NB507 this is formally identical to legitimate rhetoric and only
    intent separates them: advisory for the judgment layer.
    """

    code = "NB523"
    name = "ai-anaphora-triad"
    category = "ai"
    codes = ("NB523",)
    default_on = False
    severity = Severity.INFO

    # Closed-class anchors only — an open match on e.g. "the" would fire on
    # every third sentence. "no X, no Y, no Z" already belongs to NB501.
    _TRIAD = re.compile(
        r"\b(more|less|fewer|every|each)\b[^,.;:!?\n]{1,30},\s*\1\b[^,.;:!?\n]{1,30}"
        r",\s*(?:and\s+|or\s+)?\1\b(?:\s+[\w'’-]+){1,2}",
        re.IGNORECASE,
    )

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        for m in self._TRIAD.finditer(ctx.doc.text):
            snippet = " ".join(m.group(0).split())
            yield _issue(
                ctx,
                "NB523",
                "ai-anaphora-triad",
                f"AI tell: anaphora triad '{snippet}' — the same quantifier "
                "three times; vary the enumeration or cut to one concrete item",
                m.start(),
                m.end(),
                snippet,
                severity=self.severity,
            )


class ContrastHeadingRule(Rule):
    """NB524 — the "X, not Y" contrast heading: "Pin decisions, not knowledge".

    The negation-contrast couplet (NB501) compressed into a title. The
    thinnest tell in the catalogue — it fires on legitimate human titles
    ("Ask forgiveness, not permission"), and the classics corpus carries no
    markdown headings to calibrate against, so its pedigree is one detector-
    flagged draft. It exists to make the judgment layer look at the heading;
    a grounded contrast stays, and a document whose every heading corrects
    something is the actual signal.
    """

    code = "NB524"
    name = "ai-contrast-heading"
    category = "ai"
    codes = ("NB524",)
    default_on = False
    severity = Severity.INFO

    _CONTRAST = re.compile(r"^[^,\n]{2,60},\s+not\s+\S.*$")

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.source.original_text
        for m in _HEADING.finditer(text):
            if _in_code(ctx, m.start(2)):
                continue
            heading = m.group(2)
            if self._CONTRAST.match(heading):
                yield _issue(
                    ctx,
                    "NB524",
                    "ai-contrast-heading",
                    f"AI tell: 'X, not Y' contrast heading '{heading}' — name "
                    "what the section says instead of what it corrects",
                    m.start(2),
                    m.end(2),
                    heading,
                    severity=self.severity,
                )
