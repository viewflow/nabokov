"""NB314 — a list step that tells the reader about themselves.

"1. You should click Save." The step is about the reader, so naming them is
redundant; the imperative says the same thing shorter and in the mood every
style guide asks instructions to use. Google prescribes the imperative with an
implied "you", and Diátaxis builds how-to guides out of conditional imperatives
("If you want x, do y").

The rule turned out simpler than expected. The obvious framing — "flag a list
item that is not imperative" — needs to separate an *action* list from a *fact*
list ("- Requires Python 3.12"), which is hard. But every genuine offender has
one thing in common: **the reader is the explicit subject**. Fact lists never do
that. They have no subject at all, or a subject that is the software:

    1. You should click Save.        subj=You      -> flag
    2. The user clicks Save.         subj=user     -> flag
    1. Click Save to continue.       subj=[]       -> imperative already
    - Requires Python 3.12.          subj=[]       -> a fact
    - The parser handles nesting.    subj=parser   -> a fact about the software

Restricted to list items, because outside one the second person is *correct* —
"you can create a website" is Google's own recommended phrasing for body prose.
It is the step that wants the imperative, not the page.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule, span_sents

# Subjects that mean "the person reading this".
_READER = frozenset({"you", "user", "users", "reader", "readers", "one"})

# Verbs that carry the modality and hand the real action to a complement:
# "you need to run …", "you should click …". The draft promotes the complement.
_MODAL_LEMMAS = frozenset({"need", "have", "want", "should", "must", "be", "get", "try"})

_MESSAGE = "step names the reader — use the imperative"


# How far into the item the reader-subject may sit. A step that names the reader
# opens with them: "You should…", "The user clicks…" (one determiner of slack).
# Any deeper and the pronoun belongs to a subordinate clause, which is ordinary
# writing — "add detail you don't have", "nabokov ignores headings; so must you".
_SUBJECT_WINDOW = 1


def _reader_subject(sent):
    """The (subject, verb) pair where the reader is the item's subject, or None.

    Not simply the sentence root's subject: a capitalised UI label derails the
    parse — in "The user clicks Continue" spaCy makes *clicks* the subject of
    *Continue* — while "user" remains ``nsubj`` of "clicks" further down the tree.
    So the search covers the sentence and takes the verb from the subject's own
    head, but the subject has to open the item, or every relative clause
    containing "you" becomes a finding.
    """
    for tok in sent:
        if tok.i - sent.start > _SUBJECT_WINDOW:
            return None
        if tok.dep_ not in ("nsubj", "nsubjpass"):
            continue
        if tok.lemma_.lower() not in _READER:
            continue
        if tok.head.pos_ in ("VERB", "AUX"):
            return tok, tok.head
    return None


class NonImperativeStepRule(Rule):
    code = "NB314"
    name = "non-imperative-step"
    category = "markup"
    codes = ("NB314",)
    severity = Severity.INFO

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        source = ctx.source
        # The marker span's *end* is where the item's text begins. Its start is
        # not reliable: the pattern's leading \s* swallows the newline of a
        # preceding blank line, putting span.start a line early.
        item_lines = {source.linecol(s.end)[0] for s in source.spans("list-marker")}
        if not item_lines:
            return
        for sent in span_sents(ctx.doc[:]):
            if source.linecol(sent.start_char)[0] not in item_lines:
                continue
            found = _reader_subject(sent)
            if found is None:
                continue
            yield self._issue(ctx, sent, *found)

    def _issue(self, ctx: CheckContext, sent, subject, verb) -> Issue:
        if verb.lemma_.lower() in _MODAL_LEMMAS:
            complements = [c for c in verb.children if c.dep_ in ("xcomp", "ccomp")]
            if complements:
                verb = complements[0]
        tail = " ".join(t.text for t in sent if t.i > verb.i and not t.is_punct)
        draft = f"{verb.lemma_.capitalize()} {tail}".strip()
        start = subject.idx
        end = sent.end_char
        line, col = ctx.source.linecol(start)
        end_line, end_col = ctx.source.linecol(end)
        return Issue(
            code=self.code,
            name=self.name,
            message=_MESSAGE,
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
            severity=self.severity,
            # A draft: dropping the subject can drop an adverb that sat before the
            # verb ("you will *then* restart"), and only the writer knows whether
            # that word was doing work.
            suggestion=draft,
            applicability=Applicability.REWRITE,
            text=ctx.doc.text[start:end],
        )
