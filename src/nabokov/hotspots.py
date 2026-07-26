"""Hotspots — which paragraphs carry the most trouble per word.

The report answers "what is wrong"; the score answers "how bad is it overall".
Neither answers the question a writer with ten minutes actually has: *where do I
start*. A 3000-word draft with 60 findings spreads them unevenly, and a linear
walk through the file spends the same effort on a clean paragraph as on the one
that needs rebuilding.

This ranks paragraphs by the findings already produced. It introduces no new
signal and no new data — every input is an ``Issue`` some rule emitted, weighted
by the severity that rule (and the analyzer's budget pass) settled on. If a
hotspot looks wrong, the rules are wrong, not the ranking.

Density, not count, does the ranking: a long paragraph collects more findings
just by being long. Dividing by length alone would then hand the top spot to a
six-word heading with one info finding, so the divisor has a floor
(``_LENGTH_FLOOR``) that damps short paragraphs without excluding them.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .checks.base import paragraph_ranges
from .issue import Severity

if TYPE_CHECKING:
    from .analyzer import AnalysisResult

# What one finding contributes, by severity. An error is a hard failure, a
# warning is a tell the rule is confident about, an info is a judgment call left
# to the writer — so they are not worth the same when deciding where to look.
_WEIGHT = {Severity.ERROR: 4.0, Severity.WARNING: 2.0, Severity.INFO: 1.0}

# Divisor floor, in words. Below this a paragraph is scored as if it were this
# long, so a heading with a single finding cannot out-rank a dense paragraph.
_LENGTH_FLOOR = 25

_DEFAULT_LIMIT = 3
_PREVIEW_CHARS = 60


@dataclass(frozen=True)
class Hotspot:
    """One paragraph, with the weighted finding load it carries."""

    line: int
    end_line: int
    words: int
    issues: int
    weight: float
    density: float  # weighted load per 100 words, short-paragraph damped
    counts: Counter[str] = field(default_factory=Counter)
    preview: str = ""

    @property
    def top_codes(self) -> list[tuple[str, int]]:
        """Codes driving this hotspot, most frequent first."""
        return sorted(self.counts.items(), key=lambda kv: (-kv[1], kv[0]))


def compute(result: AnalysisResult, limit: int = _DEFAULT_LIMIT) -> list[Hotspot]:
    """Rank the paragraphs of one analyzed file, worst first."""
    source = result.source
    # Paragraphs are found in the analysis text, where blanked markup cannot
    # fake a blank line; offsets are shared with the original (see `source`).
    ranges = paragraph_ranges(source.analysis_text)
    if not ranges:
        return []

    buckets: dict[int, list] = {i: [] for i in range(len(ranges))}
    starts = [start for start, _ in ranges]
    for issue in result.issues:
        offset = source.offset(issue.line, issue.col)
        index = _paragraph_of(offset, ranges, starts)
        if index is not None:
            buckets[index].append(issue)

    spots = []
    for index, issues in buckets.items():
        if not issues:
            continue
        start, end = ranges[index]
        text = source.analysis_text[start:end]
        words = len(text.split())
        weight = sum(_WEIGHT.get(i.severity, 1.0) for i in issues)
        line, _ = source.linecol(start)
        end_line, _ = source.linecol(max(start, end - 1))
        spots.append(
            Hotspot(
                line=line,
                end_line=end_line,
                words=words,
                issues=len(issues),
                weight=weight,
                density=weight / max(words, _LENGTH_FLOOR) * 100,
                counts=Counter(i.code for i in issues),
                preview=_preview(source.original_text[start:end]),
            )
        )

    # Density decides; total weight breaks ties so the bigger mess wins, and the
    # line number keeps the order stable for identical paragraphs.
    spots.sort(key=lambda s: (-s.density, -s.weight, s.line))
    return spots[:limit]


def _paragraph_of(offset: int, ranges: list[tuple[int, int]], starts: list[int]) -> int | None:
    """Index of the paragraph containing ``offset``, or None if it sits between them."""
    from bisect import bisect_right

    index = bisect_right(starts, offset) - 1
    if index < 0:
        return None
    start, end = ranges[index]
    return index if start <= offset < end else None


def _preview(text: str) -> str:
    flat = " ".join(text.split())
    if len(flat) <= _PREVIEW_CHARS:
        return flat
    return flat[: _PREVIEW_CHARS - 1].rstrip() + "…"


def payload(result: AnalysisResult, limit: int = _DEFAULT_LIMIT) -> list[dict]:
    """The hotspots of one file as JSON-ready dicts."""
    return [
        {
            "line": spot.line,
            "end_line": spot.end_line,
            "words": spot.words,
            "issues": spot.issues,
            "weight": round(spot.weight, 1),
            "density": round(spot.density, 1),
            "codes": dict(spot.top_codes),
            "preview": spot.preview,
        }
        for spot in compute(result, limit)
    ]


def format_hotspots(results: list[AnalysisResult], limit: int = _DEFAULT_LIMIT) -> str:
    """Plain-text hotspot block, for the flake8 and color reporters."""
    lines: list[str] = []
    for result in results:
        spots = compute(result, limit)
        if not spots:
            continue
        lines.append("")
        lines.append(f"Hotspots ({result.source.display_name}) — worst paragraphs first:")
        for rank, spot in enumerate(spots, 1):
            codes = " ".join(f"{code}×{n}" if n > 1 else code for code, n in spot.top_codes)
            lines.append(
                f"  {rank}. line {spot.line}"
                + (f"-{spot.end_line}" if spot.end_line != spot.line else "")
                + f": {spot.issues} finding{'s' if spot.issues != 1 else ''} "
                f"in {spot.words} words (density {spot.density:.1f})"
            )
            lines.append(f"       {codes}")
            if spot.preview:
                lines.append(f"       {spot.preview}")
    return "\n".join(lines) + "\n" if lines else ""
