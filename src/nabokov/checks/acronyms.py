"""NB309 — an acronym used before anything says what it stands for.

The reader who already knows the term loses nothing to an expansion; the reader
who doesn't is stopped cold. Both Vale's Google and Microsoft styles ship an
``Acronyms`` check, and Microsoft's is *conditional* — exactly this
definition-before-use shape.

The allowlist in ``data/acronyms.json`` is the rule. A developer audience meets
API and JSON daily and an expansion there is noise, so the check is worth only as
much as that list is generous. Two things keep the failure mode survivable:

- **First use only.** A document using CRD forty times gets one finding, not
  forty. So an acronym the list doesn't know costs the reader one line of output,
  not a screen of it.
- **``known_acronyms`` in config.** Every domain has everyday abbreviations that
  no shipped list can enumerate. Growing the list is the intended response to a
  noisy run — not switching the rule off.

Severity is info by design. Whether an audience knows a term is a judgment about
that audience, which the linter is in no position to make.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..data_loader import concreteness, known_acronyms
from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule

# An acronym: 2-6 letters, all caps. One letter is a variable or an initial; more
# than six is usually a constant or shouted prose, neither of which this rule owns.
_ACRONYM = re.compile(r"^[A-Z]{2,6}$")

# A gloss is counted anywhere in the document, not only before the first bare use.
# A glossary at the foot of a reference page is legitimate structure, and flagging
# it would make the rule noisy on exactly the documents that try hardest.
#
# Three forms, because real writing uses all three:
#   "Fully Qualified Domain Name (FQDN)"          parenthesised initials
#   "MATTR (moving-average type-token ratio)"     parenthesised expansion
#   "**PAS** — Problem, Agitate, Solution"        dash or colon gloss
# The first is deliberately loose: the initials only have to appear *inside* a
# parenthetical, so "diversity (vocabulary variety, MATTR)" counts. Matching the
# capitals against the words would reject "Cascading Style Sheets (CSS)" anyway,
# where a small word is skipped.
# Newlines allowed: a gloss in hard-wrapped prose routinely straddles a line
# break ("diversity (vocabulary\nvariety, MATTR)"). Bounded length keeps a stray
# unclosed paren from swallowing the document.
_PARENTHETICAL = re.compile(r"\(([^)]{2,120})\)", re.DOTALL)
_ACRONYM_IN_TEXT = re.compile(r"\b([A-Z]{2,6})s?\b")
# Line-initial acronym (optionally bold/emphasised) followed by a dash or colon
# and a word — the glossary and definition-list shape.
_DASH_GLOSS = re.compile(
    r"^[\s>*_-]*\**([A-Z]{2,6})\**\s*[—–:-]\s*\S",
    re.MULTILINE,
)


def _glossed(text: str) -> set[str]:
    """Acronyms the document explains somewhere, in any of the three gloss forms."""
    found: set[str] = set()
    for paren in _PARENTHETICAL.finditer(text):
        found |= {m.group(1) for m in _ACRONYM_IN_TEXT.finditer(paren.group(1))}
        # "MATTR (moving-average …)" — the initials sit just before the paren.
        before = text[max(0, paren.start() - 12) : paren.start()]
        found |= {m.group(1) for m in _ACRONYM_IN_TEXT.finditer(before)}
    found |= {m.group(1) for m in _DASH_GLOSS.finditer(text)}
    return found


def _is_english_word(acronym: str) -> bool:
    """True when the capitals spell an ordinary English word.

    All-caps English words in technical prose are almost always identifiers, not
    abbreviations: a config value (``SOCIAL``, ``NORMAL``), an HTTP method
    (``GET``, ``POST``, ``HEAD``), an enum member. None of them wants expanding.
    The few real acronyms that *are* words — RADAR, SCUBA, LASER — long ago
    stopped needing it too, so the guard cuts the right way in both directions.

    The dictionary is the Brysbaert concreteness norms nabokov already ships for
    NB601: 37k common English lemmas, and zero of the acronyms this rule exists
    to catch. spaCy's small model carries no usable frequency data, so this
    reuses data already on disk rather than adding a word list.
    """
    return acronym.lower() in concreteness()


def _normalize(text: str) -> str:
    """Strip a possessive and a plural 's' so one list entry covers API/APIs/API's."""
    stripped = text.replace("’s", "").replace("'s", "")
    return stripped[:-1] if stripped.endswith("s") and stripped[:-1].isupper() else stripped


class UndefinedAcronymRule(Rule):
    code = "NB309"
    name = "undefined-acronym"
    category = "word"
    codes = ("NB309",)
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        text = ctx.doc.text
        allowed = known_acronyms() | {a.upper() for a in ctx.config.known_acronyms}
        glossed = _glossed(text)
        # Emphasis, not an acronym: if the document also uses the word in lower
        # case ("the CLIENT must" alongside "the client must"), the capitals are
        # shouting and the term is ordinary English.
        lowercased = {t.lower_ for t in ctx.doc if t.is_alpha and not t.is_upper}
        seen: set[str] = set()
        for tok in ctx.doc:
            if not tok.is_alpha or not tok.is_upper:
                continue
            acronym = _normalize(tok.text)
            if not _ACRONYM.match(acronym):
                continue
            if acronym in allowed or acronym in glossed or acronym in seen:
                continue
            if acronym.lower() in lowercased:
                continue
            if _is_english_word(acronym):
                continue
            seen.add(acronym)
            start, end = tok.idx, tok.idx + len(tok.text)
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(end)
            yield Issue(
                code=self.code,
                name=self.name,
                message=(
                    f"'{acronym}' is never expanded — give it once, or add it to known_acronyms"
                ),
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=self.severity,
                # The linter has no idea what the letters stand for, and guessing
                # would put a wrong expansion in front of the one reader who
                # needed the right one.
                applicability=Applicability.ADVISORY,
                text=tok.text,
            )
