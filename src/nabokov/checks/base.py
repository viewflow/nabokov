"""Rule base class and the context object every rule receives.

Each rule is a self-contained, individually toggleable check (flake8 style). A rule
may emit more than one code (e.g. the sentence rule emits both NB201 and NB202); the
analyzer runs a rule when *any* of its codes is enabled and filters the emitted
issues down to the enabled set.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..issue import Severity

_PARA_BREAK = re.compile(r"\n[ \t]*\n\s*")


def paragraph_ranges(text: str) -> list[tuple[int, int]]:
    """0-based [start, end) char ranges of blank-line-separated paragraphs."""
    ranges: list[tuple[int, int]] = []
    start = 0
    for match in _PARA_BREAK.finditer(text):
        if match.start() > start:
            ranges.append((start, match.start()))
        start = match.end()
    if start < len(text):
        ranges.append((start, len(text)))
    return ranges


if TYPE_CHECKING:
    from spacy.language import Language
    from spacy.tokens import Doc

    from ..config import Config
    from ..issue import Issue
    from ..source import SourceFile


@dataclass
class CheckContext:
    """Everything a rule needs to inspect one document."""

    doc: Doc
    source: SourceFile
    config: Config
    nlp: Language


class Rule:
    """Base class for a lint rule. Subclasses set the metadata and implement check()."""

    code: str = ""
    name: str = ""
    category: str = ""
    codes: tuple[str, ...] = ()
    default_on: bool = True
    # WARNING = a confident tell the LLM should normally fix; INFO = an advisory
    # "hard part" static isn't sure about, left for the LLM to decide. The style
    # rules (NB301/NB302/NB303) emit WARNING but the analyzer demotes them to INFO
    # while the document stays inside its per-1000-word budget — see _apply_budgets.
    severity: Severity = Severity.WARNING

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        raise NotImplementedError
