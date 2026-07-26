"""NB302 — passive voice via spaCy dependency parsing.

spaCy-primary: any verb that has an ``auxpass`` child is passive ("was written",
"is being replaced"). We span the passive auxiliaries + the participle, and extend
over the ``agent`` ("by …") phrase when present. This diverges from the classic
regex heuristic on purpose — it catches multi-auxiliary passives and avoids the
false positives the `(is|are|was…) + word` pattern produces.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..data_loader import participle_to_past
from ..issue import Applicability, Issue, Severity
from .base import CheckContext, Rule

# get + participle idioms that parse as get-passives but mean "begin"/enter a
# state, not passive voice: "get started", "get going", "got married",
# "got stuck", "get dressed". Flagging these reads as a linter bug.
_GET_IDIOM_LEMMAS = {"start", "go", "marry", "stick", "dress"}


# A draft longer than this stops being a suggestion and becomes a wall of text;
# the writer is better served by the plain "this is passive" message.
_MAX_DRAFT_CHARS = 120

# Relative and interrogative pronoun tags. When one of these is the passive
# subject the clause is a relative clause ("synergies which were unlocked by the
# team") and the thing acted on lives in the antecedent, outside the clause —
# swapping in place yields "the team unlocked which".
_RELATIVE_TAGS = frozenset({"WDT", "WP", "WP$", "WRB"})


def _phrase(tokens) -> str:
    """Flatten a token sequence back to readable text, in document order."""
    return " ".join(t.text for t in sorted(tokens, key=lambda t: t.i) if not t.is_space)


def _decapitalize(tokens, text: str) -> str:
    """Drop the capital a phrase only had because it opened the sentence.

    Swapping subject and agent moves the old subject into the middle of the
    clause ("The report was written by the team" -> "the team wrote the
    report"), so its sentence-initial capital has to go — unless the word earns
    it as a proper noun.
    """
    first = min(tokens, key=lambda t: t.i)
    if first.is_sent_start and first.pos_ != "PROPN" and text[:1].isupper():
        return text[0].lower() + text[1:]
    return text


def _active_draft(verb, aux) -> str | None:
    """Draft the active-voice version of a passive clause, or None.

    Three conditions, and all of them have to hold:

    1. The parse names both ends — a ``nsubjpass`` (what the action landed on)
       and a ``by``-agent (who did it). Without the agent the actor is missing
       from the sentence entirely and no rearrangement recovers it; the writer
       has to supply the name.
    2. The auxiliary is past tense. Tense lives in the auxiliary, not the
       participle, and the irregular map only yields past forms — so "are found
       by Alice" would come back as "Alice found bugs", a tense the sentence
       never had. Present-tense passives would also need subject-verb agreement
       on the new subject ("finds" vs "find"), which is more inflection than a
       lookup table can carry. A wrong draft costs more trust than a missing one.
    3. The result stays short enough to read.

    The result is a REWRITE, never a substitution: the flagged span covers only
    the verb group, while the rewrite reorders the whole clause around it.
    """
    if not any(a.tag_ == "VBD" for a in aux):
        return None
    subjects = [c for c in verb.children if c.dep_ == "nsubjpass"]
    agents = [c for c in verb.children if c.dep_ == "agent"]
    if not subjects or not agents:
        return None
    if subjects[0].tag_ in _RELATIVE_TAGS:
        return None
    # the agent subtree is "by <who>"; drop the preposition itself
    actor = [t for t in agents[0].subtree if t.i != agents[0].i]
    if not actor:
        return None
    patient = list(subjects[0].subtree)
    # "written" -> "wrote"; regular verbs share the two forms, so a miss on the
    # irregular map means the participle is already the past tense.
    past = participle_to_past().get(verb.text.lower(), verb.text.lower())
    draft = (
        f"{_decapitalize(actor, _phrase(actor))} {past} {_decapitalize(patient, _phrase(patient))}"
    )
    # The clause led the sentence, so the rewritten clause leads it too.
    if min(patient + actor, key=lambda t: t.i).is_sent_start:
        draft = draft[0].upper() + draft[1:]
    return None if len(draft) > _MAX_DRAFT_CHARS else draft


class PassiveRule(Rule):
    code = "NB302"
    name = "passive-voice"
    category = "grammar"
    codes = ("NB302",)

    def check(self, ctx: CheckContext) -> Iterable[Issue]:
        doc = ctx.doc
        for verb in doc:
            aux = [c for c in verb.children if c.dep_ == "auxpass"]
            if not aux:
                continue
            if (
                all(a.lemma_ == "get" for a in aux)
                and verb.lemma_ in _GET_IDIOM_LEMMAS
                and not any(c.dep_ == "agent" for c in verb.children)
            ):
                continue
            parts = [*aux, verb]
            # include the "by <agent>" phrase if spaCy attached one
            for child in verb.children:
                if child.dep_ == "agent":
                    parts.extend(child.subtree)
            start_tok = min(parts, key=lambda t: t.i)
            end_tok = max(parts, key=lambda t: t.i)
            start = start_tok.idx
            end = end_tok.idx + len(end_tok.text)
            text = doc.text[start:end]
            flat = " ".join(text.split())  # spans can wrap a line; keep the message flat
            line, col = ctx.source.linecol(start)
            end_line, end_col = ctx.source.linecol(end)
            draft = _active_draft(verb, aux)
            yield Issue(
                code="NB302",
                name="passive-voice",
                message=f"passive voice: '{flat}'",
                line=line,
                col=col,
                end_line=end_line,
                end_col=end_col,
                severity=Severity.WARNING,
                suggestion=draft,
                applicability=(Applicability.REWRITE if draft else Applicability.ADVISORY),
                text=text,
            )
