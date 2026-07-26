"""NB801 — a README that never says what the project is.

The only README-structure rule the evidence supports. Prana et al. hand-annotated
4,226 sections across 393 randomly sampled GitHub repositories and found that
**97.0%** contain a section describing the *what* of the project. So a rule
demanding one fires on roughly three repositories in a hundred: rare enough to be
worth saying.

The same table is why its obvious siblings do not exist here. Contribution
appears in 27.8% of READMEs, Why in 25.7%, When in 21.4% — a "missing
Contributing section" check would fire on 72% of real-world READMEs, which is not
a defect rate but the norm. Popular checklist advice, contradicted by the only
measurement of it. See ``docs/rule-research.md``.

What counts as saying what the project is: a sentence of ordinary prose near the
top, before the reader has to scroll. What does not count is the thing this rule
actually catches — a title, a wall of badges, and then straight into
``## Installation``, which is a real and common failure. Badges say a project has
CI; they never say what it does.

Deliberately generous, because a false positive here reads as the linter not
being able to read. Any prose sentence in the opening region satisfies it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule

# Only files that are really READMEs. This asks about a specific document's job,
# not about prose in general, so it must not wander into other Markdown.
_README = re.compile(r"(^|[\\/])readme(\.[a-z]+)?$", re.IGNORECASE)

# How far in to look. The point is what a reader meets before scrolling: past the
# first couple of section breaks the description is not doing its job anyway.
_OPENING_HEADINGS = 2

# A description is a sentence, not a label. Badge rows and one-word lines survive
# blanking as short fragments, so require enough words to be a real claim.
_MIN_WORDS = 5

_MESSAGE = (
    "README never says what the project is — add a sentence before the badges or the first section"
)
_FIX = "one sentence: what it is, and who it is for"


class ReadmeDescriptionRule(Rule):
    code = "NB801"
    name = "readme-no-description"
    category = "structure"
    codes = ("NB801",)
    severity = Severity.WARNING

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        source = ctx.source
        if not source.is_markdown or not _README.search(source.display_name):
            return
        if _has_prose(source, _opening_limit(source)):
            return
        line, col = source.linecol(0)
        yield Issue(
            code=self.code,
            name=self.name,
            message=_MESSAGE,
            line=line,
            col=col,
            end_line=line,
            end_col=col,
            severity=self.severity,
            # Only the author can say what the project is for.
            suggestion=_FIX,
            applicability=Applicability.REWRITE,
            text="",
        )


def _opening_limit(source) -> int:
    """Character offset where the opening region ends.

    The region runs to the start of the third heading, or to the end of a short
    file. Heading spans come from the markup index, so this reads the document's
    real structure rather than guessing from blank lines.
    """
    headings = source.spans("heading-marker")
    if len(headings) > _OPENING_HEADINGS:
        return headings[_OPENING_HEADINGS].start
    return len(source.analysis_text)


def _has_prose(source, limit: int) -> bool:
    """True when the opening region holds at least one sentence-length run of words.

    Markup is already blanked, so badge rows, image links and code fences are
    whitespace here and cannot be mistaken for a description. Heading *text*
    survives blanking, though — only the ``#`` markers go — so headings are masked
    out first. A title is a label: "# nabokov" is not a description of nabokov,
    and neither is a long one.
    """
    region = list(source.analysis_text[:limit])
    for span in source.spans("heading"):
        if span.start >= limit:
            break
        for i in range(span.start, min(span.end, limit)):
            region[i] = " "
    for line in "".join(region).split("\n"):
        stripped = line.strip()
        if len(stripped.split()) >= _MIN_WORDS and any(c.isalpha() for c in stripped):
            return True
    return False
