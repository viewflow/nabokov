"""NB304 (light-verb nominalizations) and NB305 (dummy subjects).

Both implement Joseph Williams' clarity principles (*Style: Lessons in Clarity
and Grace*): the key action belongs in the verb, and the key character in the
subject.

NB304 flags the action hidden inside a noun behind a light verb — "came to an
agreement" instead of "agreed", "conduct an investigation" instead of
"investigate". Matching is dependency-based (the nominalization is the object of
a light verb, or the to/at prepositional object of come/arrive), so articles,
adjectives, and inflection don't matter, and standalone uses of the nouns are
never flagged.

NB305 flags expletive (dummy) subjects — "There are many great resorts in
Colorado" buries the real subject; "Colorado has many great resorts" fronts it.
spaCy tags these with the ``expl`` dependency.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data_loader import nominalizations
from ..issue import Issue, Severity
from .base import CheckContext, Rule

# come/arrive reach their nominalization through a preposition: "come to a
# conclusion", "arrive at a decision".
_PREP_VERBS = {"come": {"to"}, "arrive": {"at"}}
_OBJ_DEPS = {"dobj", "obj"}


def _span_issue(ctx: CheckContext, code, name, message, start, end, text, severity):
    line, col = ctx.source.linecol(start)
    end_line, end_col = ctx.source.linecol(end)
    return Issue(
        code=code,
        name=name,
        message=message,
        line=line,
        col=col,
        end_line=end_line,
        end_col=end_col,
        severity=severity,
        text=text,
    )


class NominalizationRule(Rule):
    code = "NB304"
    name = "nominalization"
    category = "word"
    codes = ("NB304",)

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        data = nominalizations()
        light_verbs = set(data["light_verbs"])
        noun_map = data["nouns"]
        for tok in ctx.doc:
            noun_lemma = tok.lemma_.lower()
            if noun_lemma not in noun_map:
                continue
            head = tok.head
            if tok.dep_ in _OBJ_DEPS and head.lemma_.lower() in light_verbs:
                verb = head
            elif tok.dep_ == "pobj" and head.lemma_.lower() in _PREP_VERBS.get(
                head.head.lemma_.lower(), ()
            ):
                verb = head.head
            else:
                continue
            start = min(verb.idx, tok.idx)
            end = max(verb.idx + len(verb.text), tok.idx + len(tok.text))
            text = ctx.doc.text[start:end]
            flat = " ".join(text.split())
            suggestion = noun_map[noun_lemma]
            yield _span_issue(
                ctx,
                "NB304",
                "nominalization",
                f"nominalization '{flat}' — try the verb: {suggestion}",
                start,
                end,
                text,
                Severity.WARNING,
            )


class DummySubjectRule(Rule):
    code = "NB305"
    name = "dummy-subject"
    category = "word"
    codes = ("NB305",)

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        for tok in ctx.doc:
            if tok.dep_ != "expl" or tok.lemma_.lower() != "there":
                continue
            head = tok.head
            start = min(tok.idx, head.idx)
            end = max(tok.idx + len(tok.text), head.idx + len(head.text))
            text = ctx.doc.text[start:end]
            flat = " ".join(text.split())
            yield _span_issue(
                ctx,
                "NB305",
                "dummy-subject",
                f"dummy subject '{flat}' — start with the real subject",
                start,
                end,
                text,
                Severity.WARNING,
            )
