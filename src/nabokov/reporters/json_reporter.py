"""JSON reporter: a diagnostics array plus a per-file readability summary."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from ..analyzer import AnalysisResult
    from ..config import Config


def report(results: list[AnalysisResult], config: Config, out: TextIO) -> None:
    payload = []
    for result in results:
        payload.append(
            {
                "path": result.source.display_name,
                "summary": {
                    "grade": result.stats.grade,
                    "readability": result.stats.readability,
                    "words": result.stats.words,
                    "sentences": result.stats.sentences,
                    "reading_time_secs": round(result.stats.reading_time_secs, 1),
                    "counts": result.stats.counts,
                },
                "diagnostics": [
                    {
                        "code": issue.code,
                        "name": issue.name,
                        "message": issue.message,
                        "severity": issue.severity.value,
                        "line": issue.line,
                        "col": issue.col,
                        "end_line": issue.end_line,
                        "end_col": issue.end_col,
                        "suggestion": issue.suggestion,
                        "text": issue.text,
                    }
                    for issue in result.issues
                ],
            }
        )
    json.dump(payload, out, indent=2, ensure_ascii=False)
    out.write("\n")
