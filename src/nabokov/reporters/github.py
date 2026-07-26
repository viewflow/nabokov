"""GitHub Actions reporter: workflow annotation commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from ..issue import Severity
from .common import format_suggestion

if TYPE_CHECKING:
    from ..analyzer import AnalysisResult
    from ..config import Config

_LEVEL = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "notice"}


def _escape(text: str) -> str:
    """Escape a GitHub annotation message (its official encoding)."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def report(results: list[AnalysisResult], config: Config, out: TextIO) -> None:
    for result in results:
        name = result.source.display_name
        for issue in result.issues:
            level = _LEVEL.get(issue.severity, "warning")
            text = f"{issue.code} {issue.message}"
            # Annotations render multiline, so the fix gets its own line.
            fix = format_suggestion(issue)
            if fix:
                text = f"{text}\n{fix}"
            body = _escape(text)
            out.write(f"::{level} file={name},line={issue.line},col={issue.col}::{body}\n")
