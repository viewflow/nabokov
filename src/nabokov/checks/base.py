"""Rule base class and the context object every rule receives.

Each rule is a self-contained, individually toggleable check (flake8 style). A rule
may emit more than one code (e.g. the sentence rule emits both NB201 and NB202); the
analyzer runs a rule when *any* of its codes is enabled and filters the emitted
issues down to the enabled set.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..issue import Severity

if TYPE_CHECKING:
    from spacy.language import Language
    from spacy.tokens import Doc, Span

    from ..config import Config
    from ..issue import Issue
    from ..source import SourceFile

_PARA_BREAK = re.compile(r"\n[ \t]*\n\s*")


def span_sents(span: Span) -> Iterator[Span]:
    """Sentences inside a Span.

    Span.sents is real at runtime but missing from spaCy's type stubs, so the
    ignore lives here once instead of at every paragraph-walking call site.
    """
    return span.sents  # pyright: ignore[reportAttributeAccessIssue]


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


# Punctuation that a deletion would strand ("we should, in my opinion, wait" ->
# "we should, , wait"). A span touching one of these needs a human pass.
_CLAUSE_PUNCT = frozenset({",", ";", ":", "—", "–", "(", ")", "-"})


def _neighbor(doc, index: int, step: int):
    """The nearest non-whitespace token from ``index`` walking by ``step``."""
    while 0 <= index < len(doc):
        if not doc[index].is_space:
            return doc[index]
        index += step
    return None


def match_case(replacement: str, span) -> str:
    """Give ``replacement`` the capitalization the span it stands in for had.

    The phrase dictionaries are written in lower case, so a substitution at a
    sentence start would otherwise decapitalize the sentence: "Despite the fact
    that sales fell" -> "although sales fell". Substitutions only have this
    problem — nothing is stranded, because something takes the old text's place.
    """
    if not replacement or not span[0].is_sent_start:
        return replacement
    return replacement[0].upper() + replacement[1:]


def deletion_is_safe(span) -> bool:
    """True when cutting ``span`` leaves grammatical text behind.

    Cutting a word is only mechanical mid-sentence. A span that opens its
    sentence carries the capital letter away with it, and one sitting against a
    comma or dash strands the punctuation. Both need judgment, so a rule that
    would otherwise offer a straight deletion drops from REPLACE to REWRITE
    here. This is the same trap as "In order to" -> "To" at a sentence start:
    the dictionary entry is right, the mechanical substitution is not.
    """
    if span[0].is_sent_start:
        return False
    before = _neighbor(span.doc, span.start - 1, -1)
    after = _neighbor(span.doc, span.end, 1)
    return not (
        (before is not None and before.text in _CLAUSE_PUNCT)
        or (after is not None and after.text in _CLAUSE_PUNCT)
    )


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
