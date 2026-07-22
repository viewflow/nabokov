---
name: nabokov-editor
description: >-
  Lint, de-slop, and improve prose in one pass — check, clean up, "de-AI"/de-slop,
  humanize, or rewrite writing in a file (README, essay, docs, copy) for readability,
  passive voice, wordy phrases, or AI-writing tells, or make text pass the nabokov
  linter. Combines nabokov's static checks with a judgment pass, rewrites preserving
  meaning, and asks before any big change. Replaces ad-hoc humanizer / unslop /
  anti-AI-slop skills.
---

# nabokov-editor

Lint and de-slop prose in two layers, looping until clean:

1. **Static** — the `nabokov` linter catches the mechanical tells.
2. **Judgment** — you catch what no regex can see: hollow content, invented
   detail, dead metaphors.

Rewrite **preserving meaning**, re-lint, repeat — asking before any large or
meaning-changing edit.

## Layer 1 — static

```sh
uvx nabokov --format=flake8 <file>        # readability + style checks
uvx nabokov --format=flake8 --ai <file>   # add the AI-writing / de-slop checks (NB5xx)
```

(`uvx` needs no install; or `uv tool install nabokov && nabokov download-model`.)
Pick a target. `--target essay` fits essays and blog posts — it tolerates the
long sentences literary prose sustains on purpose. `social` fits short posts
(staccato is the genre there); `email` fits business mail (tightest budgets).
Rule reference: `nabokov --list-rules` and `docs/RULES.md`.

**Triage by severity.** `error` = document-level failure (grade over
`--max-grade`). `warning` = a confident tell — fix with a small,
meaning-preserving edit. `info` = advisory — change it only if that improves the
text rather than fighting the author's voice. The style checks (adverbs,
passive, qualifiers, wordy phrases) start as `info` and escalate to `warning`
when the document overuses the pattern for its target. An escalated warning
means "too many", **not** "each one is wrong": thin them out (cut roughly a
third, the ones doing no work) and leave the rest. In first-person or opinion
prose a hedge ("I think", "probably") is epistemic honesty: deleting it turns a
hedged claim into an absolute one — that's a meaning change, approval gate.

## Layer 2 — judgment

Read the prose yourself and flag:

- **Topic jumps (missing connective tissue)** — the most common LLM coherence
  failure. Read each sentence and paragraph opening and ask *how did we get here
  from the last one?* If you can't answer, the logical link is missing. The fix is
  a real bridge: a clause that carries the prior point into this one, or an opener
  that echoes the previous unit's key idea. A bolted-on *Moreover / Additionally*
  is not a bridge — it labels a transition without making one. No linter catches
  this; judging whether B follows from A needs meaning, so it is yours to read.
- **Vapidity** — grammatical sentences that say nothing. The strongest tell.
- **Interchangeability** — swap in a competitor's name; if the sentence still
  works, it says nothing about *this* subject.
- **No lived detail** — confident and generic; no example, number, or
  first-hand specific.
- **False ranges** — "from X to Y" where X and Y aren't on a real scale.
- **Manufactured aphorisms** — "X is the language of Y", tidy fake wisdom.
- **Aphoristic closer cadence** — read only the *last* sentence of each
  paragraph, top to bottom. If they read as a list of quotable maxims, the
  cadence is generated. A punchy closer is human (PG lands one on up to 40% of
  paragraphs — corpus-measured); closing *every* paragraph on one is the tell,
  and no length statistic separates it, so this is yours to read. Fix: keep the
  two or three that earn it, end the rest flat — on a fact, a detail, or
  nothing.
- **Repeated rhetorical figure** — the same syntactic move recurring through
  the document: the two-beat reversal ("This feels X. It is not."), the
  negation-contrast, the copula-colon reveal, symmetric section bridges
  ("That answers A. A harder question is B."). Once is style; three times is a
  pattern the reader starts hearing. Keep the best instance, recast the rest.
- **Synonym cycling** — the same thing renamed each mention.
- **Catalogue instead of integration** — interdependent elements presented as a
  flat list; write the relationships, not the inventory.
- **Self-labeling significance** — "here's where it gets clever"; cut the label
  and let the content carry the weight.
- **Treadmill prose** — per paragraph: what's actually new here? Name each
  paragraph's one contribution; cut the ones without one.
- **Signposting out of scale** — "let us explore three ways…" narrates the move
  instead of making it; judge density against document scale.
- **Speculative gap-filling** — invented facts or biography ("is believed to",
  "keeps a low profile") the source doesn't support.
- **Diff-anchored writing** — narrating the change instead of the current state.
- **Hollow conclusion** — "the future looks bright"; **both-sides mush** — every
  claim hedged, no stance.
- **Dead metaphor**; **press-release / sycophantic tone**.

Essays, opinion pieces, and academic texts also get the structural macro pass —
thesis, reverse outline, stitching, cohesion, conclusion. Read
[references/macro-pass.md](references/macro-pass.md) for it; skip it for
READMEs and reference docs.

## Workflow

1. **Static pass**: `nabokov --format=flake8 <file>`; add `--ai` when
   de-slopping / humanizing is the goal (usually it is when this skill is
   invoked), not when the user asked for a plain readability lint.
2. **Judgment pass** (+ macro pass for essays).
3. **Fix, preserving meaning** — playbooks below. Keep the author's intent,
   facts, links, code, structure. Never invent content. **Patch vs. rebuild**:
   when vocabulary hits span 3+ categories *and* the rhythm is flat (NB509),
   the structure itself is generated. Propose a rebuild from the piece's
   one-sentence core (approval gate).
4. **Approval gate**: batch the big changes (below) and ask once.
5. **Re-lint**; expect a couple of passes.
6. **Dryness & blandness check** — zero findings is NOT the goal. Three ways a
   rewrite passes the linter and still fails:
   - *Drier* — burstiness dropped, every hedge stripped: restore the texture
     that carried the voice. Measure it — `nabokov --stats` prints burstiness per
     file; run it on the draft before and after, and if your rewrite dropped the
     number, it went flatter than the original.
   - *Blander* — slop became clean generic claims (fails the
     interchangeability test): if the rewrite gained no concrete fact and no
     stance, the slop was paraphrased, not fixed.
   - *Monotone* — your own splits open every sentence the same way
     ("We… We… We…"); read the openers *and the paragraph closers* down the
     page and vary them — a rewrite that lands every paragraph on a punchline
     traded one machine cadence for another.
7. **Stop** when warnings and errors are resolved and judgment issues handled
   (minus anything the user declined). Remaining `info` is the author's call.
8. **Verify & report**: links, code, structure intact; meaning preserved.
   Summarize *N found → M fixed, K needed approval*.

## Fix playbook — static

Findings not listed here carry their fix in the message (NB304 names the verb,
NB401 the simpler phrase).

| Code | Fix |
|------|-----|
| NB201/NB202 | Split into shorter sentences, naturally. Long sentences are half of burstiness — never split them all. Vary the new openers (a time phrase, an object, a subordinate clause) so splits don't spawn "We did X. We did Y." chains. |
| NB301/NB302/NB303/NB510 | Act only when escalated to warning, and thin rather than eradicate. Fold weak adverbs into stronger verbs. Recast the weakest passives — passive that fronts the known topic is fine. Keep hedges that do work. |
| NB305 | Name the real subject. Keep "there is no X" when existence itself is the point. |
| NB501–NB508 | Recast the tell: drop the antithesis, cut puffery, trim em-dashes/emoji, break the triad. |
| NB502/NB503 | Deleting the amplifier treats the symptom. **Ground before generalize** — lay the concrete case first, then let the claim arrive plain. |
| NB509 | Vary sentence length — mix short and long. |
| NB512/NB521 | Vary sentence/paragraph openers: reorder, merge, or drop the opener word (a paragraph break already carries the transition). |
| NB518 | Vary enumeration size: two for contrast, three for closure, four-plus for abundance. |
| NB601 | The paragraph names nothing concrete. NEVER invent detail — ask the user for a real example or number (approval gate). If abstraction is the honest register (philosophy, math), leave it. |

## Fix playbook — judgment

- Vapidity / hollow / interchangeable → **never paraphrase it**: a neutral
  rewrite of an empty sentence is still empty. Puffery usually buries a real
  event — someone decided, delayed, shipped, broke, traded off. Write *who did
  what, and why*:
  - slop: "this transformative journey stands as a testament to the power of innovation"
  - paraphrase trap: "the result is a better product that is easier to adopt"
  - fix: "we delayed the rollout because onboarding wasn't good enough"
  If the source lacks the event, compress to the one honest short claim — or cut
  and ask the user for the missing fact. De-slopping *shrinks* text; same-length
  output with no new fact is the trap.
- No lived detail → add a real example or number (ask if you don't have one).
- False range / dead metaphor / aphorism → delete; say the plain thing.
- Synonym cycling → pick one name and repeat it.
- Gap-filling → state only what the source supports.
- Diff-anchored → describe the current state.
- Hollow conclusion / both-sides mush → take a stance or cut (both alter
  meaning — approval gate; the stance must be the author's, so ask which).

## STOP and ask before any BIG change

Small edits (word swaps, sentence splits, active voice) proceed automatically.
Ask first — batched — before a change that:

- alters meaning or a factual claim (including deleting a hedge that guards a
  claim; thinning surplus qualifiers that do no work is a small edit);
- removes or merges content, an example, or a section;
- restructures significantly or rewrites the author's voice/tone;
- substantially re-authors a passage rather than lightly editing it;
- would **add** detail you don't have — never invent facts to fill a gap.

## Guardrails

- **Meaning first.** If a clean fix and a faithful fix conflict, keep meaning
  and ask.
- **Quotes and mentions are evidence, not the author's prose.** Never edit
  quoted material or cited specimens ("phrases like X" held up for criticism) —
  even when the quote marks were lost in conversion. nabokov skips quoted spans;
  extend the same respect to what its heuristics miss.
- **Don't dry the text out.** Zero `info` findings is an anti-goal; success is
  warnings resolved with voice intact.
- **Linted slop is still slop.** The linter can't tell "clean and concrete"
  from "clean and interchangeable" — that judgment is yours alone.
- **Never fabricate** facts, examples, or numbers to satisfy a check.
- **Preserve markup** — nabokov ignores URLs, code, and headings; so must you.
- **Respect voice.** Emoji, em-dashes, and punchy phrasing are often deliberate
  style — enable `--ai` when de-slopping is the goal, not by default. If other
  writing by the same author is available, read some first.
- Inline `<!-- nabokov: ignore NBxxx -->` only for exceptions the user agrees
  to — don't silence findings to "win".
