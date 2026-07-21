"""Reporter registry — maps a format name to its report() function."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TextIO

from . import color, flake8, github, json_reporter

if TYPE_CHECKING:
    from ..analyzer import AnalysisResult
    from ..config import Config

Reporter = Callable[["list[AnalysisResult]", "Config", TextIO], None]

_REPORTERS: dict[str, Reporter] = {
    "color": color.report,
    "flake8": flake8.report,
    "json": json_reporter.report,
    "github": github.report,
}


def get_reporter(fmt: str) -> Reporter:
    return _REPORTERS[fmt]


def resolve_format(fmt: str, out: TextIO) -> str:
    """Resolve the 'auto' format: color on a tty, flake8 otherwise."""
    if fmt != "auto":
        return fmt
    return "color" if getattr(out, "isatty", lambda: False)() else "flake8"
