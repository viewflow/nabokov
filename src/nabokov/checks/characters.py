"""NB317 — invisible and look-alike characters.

A zero-width space, a stray BOM, a Cyrillic ``е`` sitting inside a Latin word.
These break search, copy-paste, diffs, screen readers, and code that happens to
contain them. They are almost never typed on purpose.

**Why this is not an AI tell, and why it moved out of NB519.** These characters
arrive two ways: an unedited paste from a chat UI, and deliberate text laundering
by a "humanizer" tool. Both readings suggest an ``--ai``-gated rule, and that is
where this lived. The detection research says otherwise. Cosmetic attacks of
exactly this class — homoglyph substitution, zero-width insertion, whitespace
tricks — are *neutralized by simple text normalization* before a detector scores
anything (RAID shared task; see ``docs/detection-research.md``). So their presence
is not evidence about authorship at all.

What it is instead is a plain defect, and one that hurts every reader regardless
of who wrote the text: a reader searching for "detection" will not find
"dеtection", and a zero-width space pasted into a code block produces a syntax
error nobody can see. A defect that needs no theory of authorship should not need
a de-slop flag, so this rule is on by default while NB519 keeps the genuinely
AI-specific fingerprints (chat citation markup, tool URL parameters, unfilled
placeholders, knowledge-cutoff disclaimers).

Scans the **original** text, not the analysis text. Markup blanking would hide a
zero-width space inside a code fence, which is the case where it does the most
damage.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule

# Zero-width and joiner characters, plus a BOM appearing mid-text. NBSP and
# narrow NBSP are deliberately absent: Russian and French typography use them,
# and flagging them by default would fire on ordinary correct writing.
_INVISIBLE = re.compile("[​‌‍⁠﻿]")

# A Cyrillic or Greek look-alike letter sandwiched inside a Latin word, or the
# reverse. The sandwich shape is what keeps legitimate multilingual text clean:
# whole-script words (ordinary Russian or Greek), a Latin brand with a Cyrillic
# inflection suffix ("в Slackе"), and unit prefixes ("μs") have no interior
# mixed letter.
_HOMOGLYPH = re.compile(
    "[A-Za-z][Ѐ-ӿͰ-Ͽ][A-Za-z]|[Ѐ-ӿ][A-Za-z][Ѐ-ӿ]"
)

_INVISIBLE_MESSAGE = (
    "invisible character (U+{code:04X}) — breaks search and copy-paste; delete it"
)
_HOMOGLYPH_MESSAGE = (
    "look-alike character in '{text}' — mixed scripts inside one word; retype it in one alphabet"
)


class HiddenCharacterRule(Rule):
    code = "NB317"
    name = "hidden-character"
    category = "markup"
    codes = ("NB317",)
    severity = Severity.WARNING

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.source.original_text
        for match in _INVISIBLE.finditer(text):
            yield self._issue(
                ctx,
                _INVISIBLE_MESSAGE.format(code=ord(match.group(0))),
                match.start(),
                match.end(),
                match.group(0),
                # Deleting an invisible character is always safe: it carries no
                # meaning and no width, so nothing around it changes.
                "",
                Applicability.REPLACE,
            )
        for match in _HOMOGLYPH.finditer(text):
            yield self._issue(
                ctx,
                _HOMOGLYPH_MESSAGE.format(text=match.group(0)),
                match.start(),
                match.end(),
                match.group(0),
                # The tool cannot know which alphabet the writer meant, and
                # guessing would silently change a word.
                "retype the word in a single alphabet",
                Applicability.REWRITE,
            )

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
