"""NB311 — an image with no alt text.

The first rule built on the markup index, and the reason the index exists: the
prose pass cannot see an image at all. ``![](chart.png)`` blanks to spaces, and
``<img src="chart.png">`` blanks to spaces, so to a rule reading only the
analysis text the picture was never there.

Both Markdown and HTML arrive here in one shape. ``source`` records an
``image-alt`` span for every image, empty when the attribute is missing
entirely, so this rule does not care which syntax produced it.

Precision is capped by the standard itself, and the cap is honest rather than
fixable. Google says to give every image an alt attribute *and* to use empty alt
text when the image is purely decorative — so an empty alt is either a correctly
marked decoration or a missing description, and nothing in the source
distinguishes them. Hence info, not warning, and a message that names the
decorative case instead of asserting a defect.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule

_MESSAGE = (
    "image has no alt text — describe what it shows, "
    "or leave it empty only if the image is decorative"
)


class ImageAltRule(Rule):
    code = "NB311"
    name = "image-no-alt"
    category = "markup"
    codes = ("NB311",)
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        source = ctx.source
        alts = source.spans("image-alt")
        for image in source.spans("image"):
            # The alt span sits inside its image — including the zero-width one
            # an HTML tag with no alt attribute records at the tag's start.
            alt = next(
                (a for a in alts if image.start <= a.start <= image.end),
                None,
            )
            if alt is None or source.span_text(alt).strip():
                continue
            line, col = source.linecol(image.start)
            end_line, end_col = source.linecol(image.end)
            yield Issue(
                code=self.code,
                name=self.name,
                message=_MESSAGE,
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                # Only the author knows what the picture shows. A guessed
                # description is worse than none for the reader who depends on it.
                applicability=Applicability.ADVISORY,
                text=source.span_text(image),
            )
