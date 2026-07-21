"""flake8-style reporter: `path:line:col: CODE message`, one finding per line."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from .common import format_statistics, total_issues

if TYPE_CHECKING:
    from ..analyzer import AnalysisResult
    from ..config import Config


def report(results: list[AnalysisResult], config: Config, out: TextIO) -> None:
    for result in results:
        name = result.source.display_name
        for issue in result.issues:
            message = " ".join(issue.message.split())  # keep the record on one line
            out.write(f"{name}:{issue.line}:{issue.col}: {issue.code} {message}\n")
    if config.statistics:
        out.write(format_statistics(results))
    total = total_issues(results)
    files = len(results)
    out.write(
        f"\n{total} issue{'s' if total != 1 else ''} in {files} file{'s' if files != 1 else ''}\n"
    )
