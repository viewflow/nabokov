"""The core data types produced by analysis: Issue and DocumentStats."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """How loud a finding is. Prose findings are advisory (warnings) by default."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Applicability(StrEnum):
    """How mechanically an Issue's ``suggestion`` can be applied.

    Severity says how much a finding matters; applicability says what a consumer
    is allowed to *do* with the fix. Without the split, a reporter, an agent, or
    a future ``--fix`` cannot tell "paste this string" from "think about this".

    REPLACE  — the suggestion substitutes for the flagged span verbatim. An empty
               suggestion means "delete the span". Where the suggestion offers
               several comma-separated alternatives, the first is the default.
               Markup blanking is length-preserving (see ``source``), so the span
               offsets address the user's real file and a substitution is safe.
    REWRITE  — a drafted direction. It may reach outside the flagged span, or need
               tense and number agreement the parse cannot settle. Show it, never
               apply it blind.
    ADVISORY — no span-level fix exists. ``suggestion`` stays None and the message
               carries the direction; inventing a replacement here would be worse
               than silence.
    """

    REPLACE = "replace"
    REWRITE = "rewrite"
    ADVISORY = "advisory"


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
    applicability: Applicability = Applicability.ADVISORY
    text: str = ""

    @property
    def sort_key(self) -> tuple[int, int, str]:
        return (self.line, self.col, self.code)

    @property
    def has_fix(self) -> bool:
        """True when the finding carries a concrete fix (replace or rewrite)."""
        return self.suggestion is not None


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
