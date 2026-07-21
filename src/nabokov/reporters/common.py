"""Shared reporter helpers."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from ..checks import RULE_META

if TYPE_CHECKING:
    from ..analyzer import AnalysisResult


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
