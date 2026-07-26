"""NB310 — "the diagram above": orienting the reader by position on the page.

Position is not stable. The same document reflows on a phone, gets paginated in
print, is read aloud in linear order by a screen reader, and has its sections
reordered by the next editor. "Above" survives none of that; "preceding" survives
all of it. Google's accessibility guidance says so outright, and Microsoft ships
the same check in its Vale style.

The discriminator comes free from the parse. ``above`` and ``below`` are normally
prepositions that take an object — "above 50 percent", "above the intake
manifold" — and both of those are ordinary English about the world. A bare
``above`` with no object is not a preposition at all; it is a postmodifier
pointing at the page:

    In the diagram above, …      advmod on NOUN 'diagram', no children  -> flag
    Values above 50 percent      prep with child 'percent'              -> skip
    The sensor sits above the …  prep with child 'manifold'             -> skip

Having no object is necessary but not sufficient, because "put it on the shelf
above" is a real spatial description. So the head noun also has to be a document
element, from the closed list below.

Left and right are deliberately absent. Google names "right-hand side" too, but
that phrase is usually describing a user interface, where the position is the
content rather than a way of navigating the page. Flagging it would fire on
correct writing in exactly the documents this rule is meant to help.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule, match_case

# Parts of a document. "The paragraph above" points at the page; "the shelf
# above" points at a shelf, so the noun is what separates them.
_DOCUMENT_NOUNS = frozenset(
    {
        "block",
        "callout",
        "chapter",
        "chart",
        "code",
        "command",
        "comment",
        "definition",
        "diagram",
        "equation",
        "example",
        "figure",
        "formula",
        "graph",
        "illustration",
        "image",
        "line",
        "list",
        "listing",
        "note",
        "output",
        "page",
        "paragraph",
        "procedure",
        "sample",
        "screenshot",
        "section",
        "sidebar",
        "snippet",
        "step",
        "table",
        "text",
        "tip",
        "topic",
        "warning",
    }
)

# Verbs of reference. A bare "see above" / "as shown below" is always pointing at
# the page — there is no other reading.
_REFERENCE_VERBS = frozenset(
    {
        "see",
        "show",
        "describe",
        "discuss",
        "mention",
        "list",
        "note",
        "explain",
        "define",
        "outline",
        "cover",
        "illustrate",
        "state",
    }
)

# above -> the word that survives reflow, and likewise for below
_REPLACEMENT = {"above": "preceding", "below": "following"}

_LINK_FIX = "name the section or link to it — position does not survive reflow"

# A preposition's object is a nominal. spaCy sometimes hangs a *verb* off a bare
# "below" ("the table below lists every flag"), which is a parse slip rather than
# a real object, so only a nominal child counts as one.
_NOMINAL = frozenset({"NOUN", "PROPN", "PRON", "NUM"})


def _has_object(tok) -> bool:
    """True when the direction word is a real preposition taking a real object."""
    return any(child.pos_ in _NOMINAL for child in tok.children)


def _preceding_word(tok):
    """The nearest non-whitespace token before ``tok``, or None."""
    for i in range(tok.i - 1, -1, -1):
        candidate = tok.doc[i]
        if not candidate.is_space:
            return candidate
    return None


class DirectionalLanguageRule(Rule):
    code = "NB310"
    name = "directional-language"
    category = "word"
    codes = ("NB310",)
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        for tok in ctx.doc:
            word = tok.lower_
            if word not in _REPLACEMENT or _has_object(tok):
                continue
            # Identify the noun by adjacency rather than by the parse. spaCy
            # attaches the head inconsistently for this shape — in "the table
            # below lists every flag" it makes 'below' a preposition of 'table'
            # but hangs the verb off it, and in "check the table below" it
            # attaches to the verb instead. The word before the direction word is
            # stable where the dependency edge is not.
            noun = _preceding_word(tok)
            if noun is not None and noun.lemma_.lower() in _DOCUMENT_NOUNS:
                yield self._noun_issue(ctx, tok, noun, word)
                continue
            head = tok.head
            if head.pos_ in ("VERB", "AUX") and head.lemma_.lower() in _REFERENCE_VERBS:
                yield self._issue(
                    ctx,
                    f"directional: '{tok.text}' orients the reader by position",
                    tok.idx,
                    tok.idx + len(tok.text),
                    tok.text,
                    _LINK_FIX,
                    Applicability.REWRITE,
                )

    def _noun_issue(self, ctx: CheckContext, tok, noun, word: str) -> Issue:
        """Flag "the diagram above", spanning the phrase so the fix can move the word.

        The replacement has to land *before* the noun ("the preceding diagram"),
        which an in-place substitution on ``above`` alone cannot express. Spanning
        the determiner through the direction word makes it mechanical again — the
        one case in this rule that earns REPLACE. Where an adjective sits between
        ("the first example above") the reordering needs judgment, so it does not.
        """
        replacement = _REPLACEMENT[word]
        message = f"directional: '{noun.text} {tok.text}' orients the reader by position"
        determiners = [c for c in noun.children if c.dep_ == "det" and c.i == noun.i - 1]
        if determiners:
            det = determiners[0]
            start = det.idx
            phrase = f"{det.text} {replacement} {noun.text}"
            return self._issue(
                ctx,
                message,
                start,
                tok.idx + len(tok.text),
                ctx.doc.text[start : tok.idx + len(tok.text)],
                match_case(phrase, ctx.doc[det.i : det.i + 1]),
                Applicability.REPLACE,
            )
        return self._issue(
            ctx,
            message,
            tok.idx,
            tok.idx + len(tok.text),
            tok.text,
            f"the {replacement} {noun.text}",
            Applicability.REWRITE,
        )

    def _issue(self, ctx, message, start, end, text, suggestion, applicability) -> Issue:
        line, col = ctx.source.linecol(start)
        end_line, end_col = ctx.source.linecol(end)
        return Issue(
            code=self.code,
            name=self.name,
            message=message,
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
            severity=self.severity,
            suggestion=suggestion,
            applicability=applicability,
            text=text,
        )
