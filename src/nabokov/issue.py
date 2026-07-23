"""The core data types produced by analysis: Issue and DocumentStats."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """How loud a finding is. Prose findings are advisory (warnings) by default."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Issue:
    """A single style finding at a source location.

    Positions are 1-based (line, col) to match flake8/editor conventions. The
    (line, col) .. (end_line, end_col) span brackets the offending text so
    reporters can underline it.
    """

    code: str
    name: str
    message: str
    line: int
    col: int
    end_line: int
    end_col: int
    severity: Severity = Severity.WARNING
    suggestion: str | None = None
    text: str = ""

    @property
    def sort_key(self) -> tuple[int, int, str]:
        return (self.line, self.col, self.code)


@dataclass(frozen=True)
class DocumentStats:
    """Whole-document readability summary (has no single source location)."""

    grade: int
    readability: str  # "normal" | "hard" | "veryHard" (document-level bucket)
    words: int
    sentences: int
    letters: int
    reading_time_secs: float
    burstiness: float  # sentence-length CV (stdev/mean); high = varied, low = flat
    mattr: float  # moving-average TTR (window 100); high = varied vocabulary, low = repetitive
    counts: dict[str, int]  # per-category highlight counts
    seg_burstiness: float = 0.0  # punctuation-segment length CV; low = metronome commas
