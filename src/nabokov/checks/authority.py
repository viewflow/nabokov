"""NB316 — a claim attributed to nobody.

"Studies show that adoption grew." Which studies? "Experts agree." Which experts?
The sentence borrows the authority of a source it never names, so the reader cannot
check it and the writer cannot be wrong. Wikipedia's manual of style calls this
family weasel words (WP:WEASEL); Vale ships versions of it in both the Microsoft
and Google rulesets, and proselint has one too. That independent prior art is the
case for this rule — not any single study of AI prose.

**Why this is not an NB5xx AI tell.** People do this constantly, and have since
long before language models; a rule that only ran under ``--ai`` would miss most of
its real hits. So it sits in the NB3xx style band and is on by default. That
placement is the whole reason for the rule's existence as something separate from
NB503, which owns the *promotional cliché* reading of a few of the same phrases
("studies show" as filler) and stays opt-in. Those phrases moved here; see
``data/ai_writing.json``.

Four shapes, because the tell has four grammars:

    Studies show that X.               generic bare-plural subject + reporting verb
    It is widely believed that X.      impersonal passive + 'that'
    Many argue that X.                 bare quantifier as subject
    Conventional wisdom holds that X.  fixed phrase

The guard that makes the first shape usable is the **determiner**. A bare generic
plural points outside the document at a source that does not exist; a definite or
possessive one points at something specific the reader can find:

    Studies show a 12% gain.        -> flagged   (which studies?)
    The study shows a 12% gain.     -> silent    (the one under discussion)
    Our research shows a 12% gain.  -> silent    (the author's own, named)
    Recent studies show a 12% gain. -> flagged   ("recent" names nobody)

And one document-level guard: a paragraph containing a link, a URL, or a citation
is left alone entirely. "Studies show X ([Smith 2020](...))" has already done the
thing this rule asks for, and firing there would be the linter failing to read.

Known limit of that guard: it reads the markup span index, which only exists for
Markdown and HTML. In a **plain-text** file a bare URL next to the claim does not
suppress anything, because nothing indexed it as a URL. Left as is — the 18-file
plain-text corpus produces no findings at all, so it is not biting in practice, and
teaching this rule its own URL regex would duplicate the source layer's job.

The fix is always REWRITE and always a question for the author — nobody but the
writer knows which study they meant. NB316 joins NB601/NB309/NB311/NB801 as a rule
an agent must never satisfy by inventing a plausible citation.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..data_loader import authority
from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule, paragraph_ranges

# Markup that means "the source is right here". Any one of these in the paragraph
# and the rule stays quiet — the reader has somewhere to go.
_SOURCE_MARKUP = ("link-url", "url", "citation", "ref-def")

# Determiners and possessives that make a subject specific rather than generic.
# "the study", "our research", "this survey", "Smith's experiments".
#
# ANY determiner counts, with no exceptions — an earlier draft carved out "no",
# "any" and "such" as "generic anyway", and dogfooding caught all three as wrong in
# the same line of docs/rule-research.md: "convention; no study found" is the writer
# saying a source does NOT exist, which is the opposite of appealing to one. "such
# studies show" refers back to studies just described. A determiner is a reference.
_SPECIFIC_DEPS = frozenset({"det", "poss", "nmod:poss"})

_MESSAGE = "attributed to nobody: '{text}'"
_BELIEF_MESSAGE = "attributed to nobody: '{text}' — who believes it?"


class NamelessAuthorityRule(Rule):
    code = "NB316"
    name = "nameless-authority"
    category = "word"
    codes = ("NB316",)
    severity = Severity.WARNING

    def __init__(self) -> None:
        self._data: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if self._data is None:
            self._data = authority()
        return self._data

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        sourced = _sourced_ranges(ctx)

        def unsourced(start: int) -> bool:
            return not any(lo <= start < hi for lo, hi in sourced)

        for start, end, message, severity, fix in self._findings(ctx):
            if unsourced(start):
                yield self._issue(ctx, start, end, message, severity, fix)

    def _findings(self, ctx: CheckContext) -> Iterable[tuple[int, int, str, Severity, str]]:
        yield from self._generic_subjects(ctx)
        yield from self._impersonal_belief(ctx)
        yield from self._bare_quantifiers(ctx)
        yield from self._phrases(ctx)

    # --- shape 1: generic subject + reporting verb -----------------------------

    def _generic_subjects(self, ctx: CheckContext):
        """"Studies show", "experts agree" — a source that is never named."""
        for spec in self._load()["families"].values():
            subjects = frozenset(spec["subjects"])
            verbs = frozenset(spec["verbs"])
            severity = Severity(spec["severity"])
            fix = spec["fix"]
            for tok in ctx.doc:
                if tok.dep_ not in ("nsubj", "nsubjpass"):
                    continue
                if tok.lemma_.lower() not in subjects:
                    continue
                if _is_specific(tok):
                    continue
                verb = tok.head
                if verb.pos_ not in ("VERB", "AUX") or verb.lemma_.lower() not in verbs:
                    continue
                start, end = _span_bounds(tok, verb)
                text = ctx.doc.text[start:end]
                yield start, end, _MESSAGE.format(text=text), severity, fix

    # --- shape 2: impersonal passive belief ------------------------------------

    def _impersonal_belief(self, ctx: CheckContext):
        """"It is widely believed that X" — a consensus with no members.

        Requires the dummy "it" subject, a passive participle from the belief list,
        and an explicit "that". Without the complement the same words are ordinary
        English: "it is known to fail" describes behaviour, not opinion.

        The "that" is found by **adjacency**, not through the parse. spaCy attaches it
        inconsistently for this shape — ``det`` of the following noun in "it is widely
        believed that scale matters", ``mark`` of the following clause in "it has been
        argued that caching is free" — so in neither case is it a child of the verb.
        The surface position is stable where the dependency is not.

        The participle needs the same tolerance. spaCy reads it either as a passive
        ("it"=nsubjpass, participle=head) or as a predicate adjective ("it"=nsubj of
        *is*, participle=``acomp``), and it picks differently for the same sentence
        depending on surrounding context — "It is well known that DNS is hard" parses
        one way alone and the other way inside a document. Both shapes are checked.
        """
        verbs = frozenset(self._load()["belief_verbs"])
        fix = "say who believes it, or drop the frame and make the claim yourself"
        for tok in ctx.doc:
            if tok.lower_ != "it" or tok.dep_ not in ("nsubj", "nsubjpass"):
                continue
            verb = _belief_participle(tok, verbs)
            if verb is None:
                continue
            following = ctx.doc[verb.i + 1] if verb.i + 1 < len(ctx.doc) else None
            if following is None or following.lower_ != "that":
                continue
            start = tok.idx
            end = verb.idx + len(verb.text)
            text = ctx.doc.text[start:end]
            yield start, end, _BELIEF_MESSAGE.format(text=text), Severity.WARNING, fix

    # --- shape 3: a bare quantifier as the subject -----------------------------

    def _bare_quantifiers(self, ctx: CheckContext):
        """"Many argue that X" — the quantifier IS the subject, so no group is named.

        "Many developers argue" is left alone: naming the group, even loosely, is
        already more than this rule asks for.
        """
        data = self._load()
        quantifiers = frozenset(data["crowd_quantifiers"])
        verbs = frozenset(data["crowd_pronoun_verbs"])
        fix = "name who, or say how many and where that count comes from"
        for tok in ctx.doc:
            if tok.dep_ != "nsubj" or tok.lemma_.lower() not in quantifiers:
                continue
            # A quantifier heading a noun ("many developers") is not this shape.
            if any(c.dep_ in ("nmod", "prep") for c in tok.children):
                continue
            verb = tok.head
            if verb.pos_ not in ("VERB", "AUX") or verb.lemma_.lower() not in verbs:
                continue
            start, end = _span_bounds(tok, verb)
            text = ctx.doc.text[start:end]
            yield start, end, _MESSAGE.format(text=text), Severity.INFO, fix

    # --- shape 4: fixed phrases ------------------------------------------------

    def _phrases(self, ctx: CheckContext):
        lowered = ctx.doc.text.lower()
        for level, phrases in self._load()["phrases"].items():
            severity = Severity(level)
            fix = "name the source, or make the claim in your own voice"
            for phrase in phrases:
                at = lowered.find(phrase)
                while at != -1:
                    end = at + len(phrase)
                    if ctx.doc.char_span(at, end, alignment_mode="strict") is not None:
                        text = ctx.doc.text[at:end]
                        yield at, end, _MESSAGE.format(text=text), severity, fix
                    at = lowered.find(phrase, at + 1)

    def _issue(self, ctx, start, end, message, severity, fix) -> Issue:
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
            severity=severity,
            # Only the author knows which source they had in mind. Never a REPLACE:
            # there is no string a tool can supply here.
            suggestion=fix,
            applicability=Applicability.REWRITE,
            text=ctx.doc.text[start:end],
        )


def _belief_participle(dummy_it, verbs: frozenset[str]):
    """The belief participle governing a dummy "it", under either parse, or None.

    Passive reading: the participle is the subject's head ("It is widely *believed*").
    Predicate-adjective reading: the head is the copula and the participle hangs off
    it as ``acomp`` ("It is well *known*").
    """
    head = dummy_it.head
    candidates = [head, *(c for c in head.children if c.dep_ in ("acomp", "attr", "xcomp"))]
    for tok in candidates:
        if tok.tag_ == "VBN" and tok.lemma_.lower() in verbs:
            return tok
    return None


def _is_specific(subject) -> bool:
    """True when a determiner or possessive ties the subject to something nameable.

    This single test is what separates the weasel from ordinary prose. "The study
    shows" and "our research shows" refer; "studies show" and "recent studies show"
    do not. An adjective is not a reference, so ``amod`` children do not count.
    """
    return any(child.dep_ in _SPECIFIC_DEPS for child in subject.children)


def _span_bounds(subject, verb) -> tuple[int, int]:
    """Character range covering subject through verb, including any auxiliaries.

    "studies have consistently shown" reports as one span rather than two ends with
    a hole in the middle, which is what a reader needs to see.
    """
    tokens = [subject, verb, *(c for c in verb.children if c.dep_ in ("aux", "auxpass", "neg"))]
    start = min(t.idx for t in tokens)
    end = max(t.idx + len(t.text) for t in tokens)
    return start, end


def _sourced_ranges(ctx: CheckContext) -> list[tuple[int, int]]:
    """Paragraph ranges that already carry a link, URL, or citation.

    Whole paragraphs, not sentences: a claim in one sentence is commonly sourced by
    the next ("Adoption grew. See [the report](...)"), and splitting hairs about
    which sentence owns the citation would make the rule fire on well-sourced prose.
    """
    marks = [s.start for s in ctx.source.spans(*_SOURCE_MARKUP)]
    if not marks:
        return []
    return [
        (start, end)
        for start, end in paragraph_ranges(ctx.doc.text)
        if any(start <= m < end for m in marks)
    ]
