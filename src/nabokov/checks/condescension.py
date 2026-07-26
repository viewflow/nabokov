"""NB308 — words that tell the reader the task is easy.

"Simply run the migration." If it works, the word was noise. If it doesn't, the
reader now knows the thing they cannot do is a thing everyone else finds easy —
so the sentence has taught them nothing and cost them something. Both major
developer style guides say to cut these, and ``alex`` flags the presupposition
family ("obviously", "everyone knows") on the same grounds.

The whole rule is its guards. Every word here has an ordinary, correct sense that
must never fire:

- ``simply`` as "merely", describing behavior — "the function simply returns null"
- ``clearly`` as manner — "the error clearly states the cause"
- ``simple`` / ``easy`` attributively, describing a thing rather than the reader's
  work — "the API returns a simple object"

So the ease adverbs fire only on an instruction (an imperative, or a clause whose
subject is the reader), the presupposition adverbs fire only sentence-initially,
and the ease adjectives fire only predicatively. Anything else is somebody using
an ordinary English word.

The words overlap NB301 (adverb) and NB510 (intensifier), which see the same
tokens without the instructional reading. NB308 is the more specific finding, so
the analyzer's span-precedence table lets it win — see ``_SPAN_PRECEDENCE``.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule, deletion_is_safe

# Adverbs asserting the action is little work. Cut them: an instruction that is
# genuinely one step reads as one step without being told so.
_EASE_ADVERBS = frozenset({"simply", "easily", "merely", "effortlessly", "painlessly"})

# Sentence adverbs that presuppose the reader already agrees. Sentence-initial
# only — mid-sentence these are manner adverbs and usually fine.
_PRESUPPOSITION_ADVERBS = frozenset({"obviously", "clearly", "naturally", "evidently"})

# Predicative adjectives claiming the task is small.
_EASE_ADJECTIVES = frozenset({"easy", "simple", "trivial", "straightforward", "painless"})

# Fixed phrases that assert shared knowledge. Always condescending in documentation.
_PRESUPPOSITION_PHRASES = (
    "of course",
    "everyone knows",
    "as you know",
    "as we all know",
    "needless to say",
    "it goes without saying",
    "it should be obvious",
)

# Subjects that make a clause an instruction to the reader rather than a
# description of the system.
_READER_SUBJECTS = frozenset({"you", "we"})

_MESSAGE = {
    "ease": "condescending: '{word}' tells the reader the task is easy",
    "presupposition": "condescending: '{word}' presupposes the reader already agrees",
    "adjective": "condescending: calling the task '{word}' — say what it takes instead",
}

_ADJECTIVE_FIX = "say what the task actually takes (steps, or how long), or drop the claim"


def _is_instruction(verb) -> bool:
    """True when ``verb`` heads an instruction aimed at the reader.

    Two shapes count: a bare imperative ("Run the migration"), and a clause whose
    subject is the reader ("you can add a plugin"). A clause about the software
    ("the function returns null") is neither, which is what keeps the ordinary
    "merely" sense of *simply* out of the findings.
    """
    subjects = [c for c in verb.children if c.dep_ in ("nsubj", "nsubjpass")]
    if not subjects:
        # No subject at all: an imperative, provided the verb is in base form.
        return verb.tag_ == "VB"
    return any(s.lower_ in _READER_SUBJECTS for s in subjects)


class CondescensionRule(Rule):
    code = "NB308"
    name = "condescending"
    category = "word"
    codes = ("NB308",)
    severity = Severity.WARNING

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        yield from self._phrases(ctx)
        for tok in ctx.doc:
            hit = self._classify(tok)
            if hit is None:
                continue
            kind, word = hit
            span = ctx.doc[tok.i : tok.i + 1]
            if kind == "adjective":
                # Cutting "easy" out of "Installation is easy" leaves "Installation
                # is". The honest fix replaces the claim with the facts behind it,
                # which the linter does not have.
                suggestion, applicability = _ADJECTIVE_FIX, Applicability.REWRITE
            else:
                suggestion, applicability = self._cut(span)
            yield self._issue(
                ctx,
                _MESSAGE[kind].format(word=word),
                tok.idx,
                tok.idx + len(tok.text),
                tok.text,
                suggestion,
                applicability,
            )

    @staticmethod
    def _cut(span) -> tuple[str, Applicability]:
        if deletion_is_safe(span):
            return "", Applicability.REPLACE
        return "cut it", Applicability.REWRITE

    @staticmethod
    def _classify(tok) -> tuple[str, str] | None:
        """Which condescension family ``tok`` belongs to, if any."""
        lower = tok.lower_
        if lower in _EASE_ADVERBS and tok.pos_ == "ADV":
            # "the function simply returns null" describes behavior, not effort.
            return ("ease", lower) if _is_instruction(tok.head) else None
        if lower in _PRESUPPOSITION_ADVERBS and tok.pos_ == "ADV":
            # Mid-sentence these read as manner ("the error clearly states why").
            return ("presupposition", lower) if tok.is_sent_start else None
        if lower in _EASE_ADJECTIVES and tok.pos_ == "ADJ":
            # Predicative only: "installation is easy" claims the task is small,
            # while "a simple object" just describes a thing.
            return ("adjective", lower) if tok.dep_ == "acomp" else None
        return None

    def _phrases(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text.lower()
        for phrase in _PRESUPPOSITION_PHRASES:
            start = text.find(phrase)
            while start != -1:
                span = self._char_span(ctx, start, start + len(phrase))
                if span is not None:
                    suggestion, applicability = self._cut(span)
                    yield self._issue(
                        ctx,
                        _MESSAGE["presupposition"].format(word=span.text),
                        span.start_char,
                        span.end_char,
                        span.text,
                        suggestion,
                        applicability,
                    )
                start = text.find(phrase, start + 1)

    @staticmethod
    def _char_span(ctx: CheckContext, start: int, end: int):
        """Token span for a character range, or None when it straddles tokens."""
        return ctx.doc.char_span(start, end, alignment_mode="strict")

    def _issue(self, ctx, message, start, end, text, suggestion, applicability) -> Issue:
        line, col = ctx.source.linecol(start)
        end_line, end_col = ctx.source.linecol(end)
        return Issue(
            code=self.code,
            name=self.name,
            message=message,
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
            severity=self.severity,
            suggestion=suggestion,
            applicability=applicability,
            text=text,
        )
