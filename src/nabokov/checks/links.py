"""NB312 — a link whose visible text does not say where it goes.

Screen readers can list a page's links on their own, stripped of the sentences
around them. A page of "click here", "here", "read more" becomes a list of
identical entries pointing nowhere. Google's accessibility guidance says not to
write them; WCAG 2.4.4 makes link purpose a Level A requirement.

This is the rule the markup index was worth building for. Without it the check
can only phrase-match "click here" anywhere in the prose, which misses the bare
``[here](url)`` — by far the commonest form — and cannot tell the difference
between a link and someone writing the words *click here* about a button. With
``link-text`` spans the question is exact: these are the words in the brackets.

The list stays closed and short. "Documentation" is vague in the abstract but
perfectly good link text, so this flags only the phrases that carry no
information at all about the destination.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule

# Link text that could point anywhere. Every entry is a complete link text, not a
# substring — "read the installation guide" contains "read" and is fine.
_VAGUE = frozenset(
    {
        "click",
        "click here",
        "click this",
        "click this link",
        "details",
        "documentation",
        "download",
        "follow this link",
        "go here",
        "here",
        "info",
        "learn more",
        "link",
        "more",
        "more here",
        "more info",
        "more information",
        "read more",
        "read this",
        "see here",
        "see this",
        "this",
        "this article",
        "this document",
        "this link",
        "this one",
        "this page",
    }
)

# Emphasis markers and trailing punctuation are decoration around the words.
_TRIM = re.compile(r"^[\s*_`~]+|[\s*_`~.,;:!?]+$")

_FIX = "name the destination — the words alone should say where the link goes"


class VagueLinkTextRule(Rule):
    code = "NB312"
    name = "vague-link-text"
    category = "markup"
    codes = ("NB312",)
    severity = Severity.WARNING

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        source = ctx.source
        urls = source.spans("link-url")
        for span in source.spans("link-text"):
            phrase = _TRIM.sub("", source.span_text(span)).lower()
            phrase = " ".join(phrase.split())
            if phrase not in _VAGUE:
                continue
            line, col = source.linecol(span.start)
            end_line, end_col = source.linecol(span.end)
            yield Issue(
                code=self.code,
                name=self.name,
                message=f"vague link text '{source.span_text(span)}'{_target(source, urls, span)}",
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                # Only the author knows what is worth saying about the target.
                # The URL is shown in the message so they do not have to look.
                suggestion=_FIX,
                applicability=Applicability.REWRITE,
                text=source.span_text(span),
            )


def _target(source, urls, span) -> str:
    """ " — points at <url>", when the link's target is close enough to be sure."""
    following = [u for u in urls if u.start >= span.end]
    if not following or following[0].start - span.end > 3:
        return ""
    url = source.span_text(following[0])
    return f" — points at {url}"
