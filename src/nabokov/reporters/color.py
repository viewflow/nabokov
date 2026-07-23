"""Colored, human-facing reporter (rich).

Each finding is shown as a compact, single-line snippet: a window of the source
centered near the flagged span, truncated with `…` when the line is long, so output
never wraps into an unreadable block. The offending span is highlighted inline (the
color rides on the characters), markup nabokov ignores (URLs, syntax) is dimmed, and
findings are spaced apart for scanning.

Colors follow the classic palette: very-hard = red, hard = yellow, adverbs and
qualifiers = blue, passive = green, complex phrases = magenta.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ..readability import HARD, VERY_HARD
from .common import total_issues

if TYPE_CHECKING:
    from ..analyzer import AnalysisResult
    from ..config import Config

# code -> rich style
_STYLE = {
    "NB101": "bold red",
    "NB201": "red",
    "NB202": "yellow",
    "NB301": "blue",
    "NB302": "green",
    "NB303": "blue",
    "NB401": "magenta",
    "NB501": "cyan",
    "NB502": "cyan",
    "NB503": "cyan",
    "NB504": "cyan",
    "NB505": "cyan",
    "NB506": "cyan",
    "NB507": "cyan",
    "NB508": "cyan",
    "NB509": "cyan",
    "NB510": "cyan",
    "NB511": "cyan",
    "NB512": "cyan",
    "NB513": "cyan",
    "NB514": "cyan",
    "NB515": "cyan",
    "NB516": "cyan",
}

# codes with no meaningful source span (document-level); skip the snippet for them
_NO_SNIPPET = {"NB101", "NB509"}

_CONTEXT = 12  # chars of lead-in before the span
_MARKUP = "grey42"


def report(results: list[AnalysisResult], config: Config, out: TextIO) -> None:
    from rich.console import Console
    from rich.text import Text

    force = True if config.color == "always" else (False if config.color == "never" else None)
    console = Console(
        file=out,
        force_terminal=force,
        no_color=config.color == "never",
        highlight=False,
    )
    width = console.width

    for result in results:
        source = result.source
        console.print(Text(source.display_name, style="bold underline"))
        console.print()
        if not result.issues:
            console.print(Text("  no issues", style="dim green"))
        else:
            for issue in sorted(result.issues, key=lambda i: (i.line, i.col, i.code)):
                _print_finding(console, Text, source, issue, width)
        _print_summary(console, Text, result)
        console.print()

    total = total_issues(results)
    files = len(results)
    console.print(
        Text(
            f"{total} issue{'s' if total != 1 else ''} in {files} file{'s' if files != 1 else ''}",
            style="bold",
        )
    )


def _print_finding(console, Text, source, issue, width) -> None:
    style = _STYLE.get(issue.code, "white")
    console.print(
        Text.assemble(
            ("  ", ""),
            (f"{issue.line}:{issue.col}", "dim"),
            ("  ", ""),
            (issue.code, f"bold {style}"),
            ("  ", ""),
            (issue.message, ""),
        )
    )
    if issue.code not in _NO_SNIPPET:
        snippet = _snippet(Text, source, issue, style, width)
        console.print(Text.assemble(("      ", ""), snippet))
    console.print()


def _snippet(Text, source, issue, style, width):
    """A single-line source window around the span, with `…` when truncated."""
    line = source.line_text(issue.line)
    n = len(line)
    span_start = min(max(issue.col - 1, 0), n)
    span_end = min(issue.end_col - 1, n) if issue.end_line == issue.line else n
    span_end = max(span_end, span_start)

    budget = max(30, width - 10)  # leave room for indent + both ellipses
    win_start = max(0, span_start - _CONTEXT)
    win_end = min(n, win_start + budget)
    if win_end - win_start < budget:  # pull left if we hit the end
        win_start = max(0, win_end - budget)

    left_cut = win_start > 0
    right_cut = win_end < n

    text = Text()
    if left_cut:
        text.append("…", style="dim")
    prefix = len(text)
    text.append(line[win_start:win_end])
    if right_cut:
        text.append("…", style="dim")

    # highlight the offending span (translated into window coordinates)
    s = max(span_start, win_start) - win_start
    e = min(span_end, win_end) - win_start
    if e > s:
        text.stylize(style, prefix + s, prefix + e)

    # dim ignored markup (URLs, syntax) inside the window, applied last so it wins
    if source.has_markup:
        for ms, me in source.markup_spans(issue.line):
            a = max(ms, win_start) - win_start
            b = min(me, win_end) - win_start
            if b > a:
                text.stylize(_MARKUP, prefix + a, prefix + b)
    return text


def _print_summary(console, Text, result) -> None:
    stats = result.stats
    if stats.readability == VERY_HARD:
        grade_style = "red"
    elif stats.readability == HARD:
        grade_style = "yellow"
    else:
        grade_style = "green"
    counts = stats.counts
    parts = Text("  ")
    parts.append(f"grade {stats.grade}", style=f"bold {grade_style}")
    parts.append(
        f"  ·  {stats.words} words · {stats.sentences} sentences · "
        f"burstiness {stats.burstiness:.2f} · "
        f"diversity {stats.mattr:.2f} · "
        f"~{round(stats.reading_time_secs)}s read",
        style="dim",
    )
    console.print(parts)
    detail = (
        f"  {counts['veryHardSentences']} very hard · {counts['hardSentences']} hard · "
        f"{counts['adverbs']} adverbs · {counts['passiveVoices']} passive · "
        f"{counts['qualifiers']} qualifiers · {counts['complexWords']} complex"
    )
    console.print(Text(detail, style="dim"))
    if result.issues:
        from collections import Counter

        by_code = Counter(i.code for i in result.issues)
        grouped = " · ".join(
            f"{code} ×{n}" if n > 1 else code
            for code, n in sorted(by_code.items(), key=lambda kv: (-kv[1], kv[0]))
        )
        console.print(Text(f"  {grouped}", style="dim"))
