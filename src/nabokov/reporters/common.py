"""Shared reporter helpers."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from ..checks import RULE_META
from ..issue import Applicability

if TYPE_CHECKING:
    from ..analyzer import AnalysisResult
    from ..issue import Issue


def format_suggestion(issue: Issue) -> str | None:
    """Render a finding's fix as one line, or None when it carries no fix.

    Every reporter renders through here, so a rule states the fix once (in
    ``suggestion`` + ``applicability``) and never formats it into its own
    message. The wording separates the tiers on sight: an arrow is a
    substitution you can make, "try:" is a draft you have to land yourself.
    """
    if issue.suggestion is None:
        return None
    if issue.applicability is Applicability.REPLACE:
        return f"→ {issue.suggestion}" if issue.suggestion else "→ delete it"
    return f"try: {issue.suggestion}"


def total_issues(results: list[AnalysisResult]) -> int:
    return sum(len(r.issues) for r in results)


def code_counts(results: list[AnalysisResult]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for result in results:
        for issue in result.issues:
            counter[issue.code] += 1
    return counter


def format_statistics(results: list[AnalysisResult]) -> str:
    counts = code_counts(results)
    if not counts:
        return ""
    lines = ["", "Statistics:"]
    for code in sorted(counts):
        name = RULE_META.get(code, (code, ""))[0]
        lines.append(f"  {counts[code]:>4}  {code}  {name}")
    return "\n".join(lines) + "\n"


def format_document_stats(results: list[AnalysisResult]) -> str:
    """One greppable metrics line per file — for eyeballing and diffing two runs.

    Burstiness is the sentence-length CV (higher = more varied rhythm); a drop
    between two versions of the same text is the polish-drift signal.

    The second line carries the register metrics — noun share, pronoun rate, and the
    temporal share of connectives. They have no thresholds and no rules behind them,
    so they are worth comparing between two drafts of the same text and worth nothing
    as absolute targets.
    """
    if not results:
        return ""
    lines = ["", "Document stats:"]
    for r in results:
        s = r.stats
        avg = s.words / s.sentences if s.sentences else 0.0
        lines.append(
            f"  {r.source.display_name}: "
            f"grade={s.grade} level={s.readability} words={s.words} "
            f"sentences={s.sentences} avg_sentence={avg:.1f} "
            f"burstiness={s.burstiness:.2f} diversity={s.mattr:.2f} "
            f"read_secs={round(s.reading_time_secs)}"
        )
        lines.append(
            f"    register: nominal={s.nominal_density:.2f} "
            f"pronouns={s.pronoun_density:.1f}/100w "
            f"temporal_connectives={s.temporal_ratio:.2f}"
        )
    return "\n".join(lines) + "\n"
