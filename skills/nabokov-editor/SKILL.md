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

Lint and de-slop prose in two layers. Repeat until clean:

1. **Static** — the `nabokov` linter finds the mechanical tells.
2. **Judgment** — you find what no regex can see: empty content, invented
   detail, dead metaphors.

Rewrite **without changing meaning**. Ask before any large change.

## Talk plainly

When you talk to the user — questions, approval requests, the final report —
use plain English (B1/B2 level). Short sentences. Common words. Name a rule by
its code plus a plain gloss: "NB302 (passive voice)", not linter jargon.

## Layer 1 — static

```sh
uvx nabokov --format=flake8 <file>        # readability + style checks
uvx nabokov --format=flake8 --ai <file>   # add the AI-writing / de-slop checks (NB5xx)
```

(`uvx` needs no install; or `uv tool install nabokov && nabokov download-model`.)
Pick a target. `--target essay` fits essays and blog posts — it allows long
sentences, because literary prose uses them on purpose. `social` fits short
posts. `email` fits business mail and is the strictest. Rule reference:
`nabokov --list-rules` and `docs/RULES.md`.

**Read the severity.**

- `error` — the document fails its grade limit (`--max-grade`).
- `warning` — a confident tell. Fix it with a small edit that keeps the meaning.
- `info` — advisory. Change it only when the change helps the text; don't
  fight the author's voice.

The style checks (adverbs, passive, qualifiers, wordy phrases) start as `info`.
They become `warning` when the document repeats the pattern too often for its
target. That warning means "too many", **not** "each one is wrong". Cut about
a third — the ones doing no work — and keep the rest. In first-person or
opinion prose a hedge ("I think", "probably") is honesty. Deleting it turns a
careful claim into an absolute one. That changes meaning, so it needs approval.

## Layer 2 — judgment

Read the prose yourself and look for:

- **Topic jumps** — the most common LLM failure. At each sentence and each
  paragraph opening, ask: *how did we get here from the last one?* If you
  can't answer, a link is missing. Write a real bridge — a clause that carries
  the last point into this one. A bolted-on *Moreover / Additionally* is a
  label, not a bridge. No linter catches this; it needs meaning, so it's yours.
- **Empty sentences** — grammatical sentences that say nothing. The strongest
  tell.
- **Interchangeable claims** — put a competitor's name into the sentence. If
  it still works, it says nothing about *this* subject.
- **No real detail** — confident and generic; no example, number, or
  first-hand fact.
- **False ranges** — "from X to Y" where X and Y aren't on a real scale
  (NB526 catches some; judge the rest).
- **Fake wisdom** — "X is the language of Y": a tidy saying the text didn't
  earn.
- **Every paragraph ends on a punchline** — keep the two or three that earn
  it; end the rest on a fact or on nothing. Punchy endings are human; the
  100% rate is the tell.
- **The same figure repeated** — "This feels X. It is not.", the
  not-X-but-Y shape, "the answer is: …", mirrored section bridges. Once is
  style, three is a tic: keep the best, rewrite the rest.
- **A key sentence made of pointers** — "that answer", "both", "it", while
  the concrete detail sits a sentence away. The top detector trigger. Pull
  the specific word in, or break the tidy frame ("When X, Y" → a command, a
  question, a fragment).
- **Synonym cycling** — the same thing renamed at each mention.
- **A flat list where relationships matter** — the parts depend on each
  other; write how, don't inventory them.
- **Self-praise labels** — "here's where it gets clever": cut the label, let
  the content carry the weight.
- **Treadmill paragraphs** — ask what new thing each paragraph adds. Cut the
  ones that add nothing.
- **Signposting out of scale** — "let us explore three ways…" describes the
  move instead of making it. A little is fine in a long document.
- **Invented facts** — "is believed to", "keeps a low profile": claims the
  source doesn't support.
- **Diff writing** — describing the change ("now improved") instead of the
  current state.
- **Hollow ending** — "the future looks bright"; **no stance** — every claim
  hedged both ways.
- **Dead metaphor**; **press-release tone**; **flattery**.

**Human signals — the inverse checklist.** Substack's Pangram-launch post
scores 100% human while using the not-X-but-Y shape and a punchline ending.
Why? Every shape stands on a checkable fact. The number has a source ("as
much as 40%… according to Pangram's estimate"). A named person is quoted. The
launch has a partner and a date. Grounding pays for rhetoric. The same shapes
over abstractions read machine-made. So when you rewrite, add one real detail
from the author's material before another round of tell-removal. Ask for it
first — never invent it.

**Detector feedback.** Detectors come in two families. Statistical ones
measure rhythm and word predictability; real structural variety moves them.
Trained classifiers (Pangram, Turnitin) learned what whole human documents
look like; only grounded specifics and a real voice move them. Word swaps
move neither. When a detector highlights a sentence, treat it as one of the
cadence or pointer findings above. Ground it or roughen it; never just swap
synonyms. Track movement with `nabokov --score <file>` before and after —
and pass on the caveat it prints: it gauges the statistical family only. Fix only what the fix improves, and say where the detector is
wrong. After rewriting, check the new sentences against this same list.
Rewrites drift into sibling shapes: a cut not-X-but-Y comes back as "what X
does is Y", and a punchline ending comes back as an "-ing" closer. Sometimes
the detector still flags text that lints clean. Then the register is the
tell: impersonal, every clause balanced, no lived detail. Word swaps will not
move that score. Two things move it. One: the author's own details or first
person — ask, never invent. Two: uneven syntax. One more note: a short
polished excerpt seems to score worse than a whole document (not confirmed).
So score the whole piece before rewriting further. Cap the loop at **two**
rewrite → re-scan rounds. On the second round touch only the sentences still
flagged — a clean sentence rewritten again can only drift. If flags survive
round two, stop and report what remains and why; a third pass moves the
meaning more than the score.

Essays, opinion pieces, and academic texts also get a structural macro pass.
It covers the thesis, a reverse outline, stitching, cohesion, and the
conclusion. Read
[references/macro-pass.md](references/macro-pass.md) for it. Skip it for
READMEs and reference docs.

## Workflow

1. **Static pass**: `nabokov --format=flake8 <file>`. Add `--ai` when the
   goal is de-slopping or humanizing — it usually is when this skill runs.
   Skip it when the user asked for a plain readability lint.
2. **Judgment pass** (+ macro pass for essays).
3. **Fix, keeping the meaning** — playbooks below. Keep the author's intent,
   facts, links, code, structure. Never invent content. **Patch or rebuild?**
   When vocabulary hits span 3+ categories *and* the rhythm is flat (NB509),
   the structure itself is generated. Propose a rebuild from the piece's
   one-sentence core (needs approval).
4. **Approval gate**: collect the big changes and ask once.
5. **Re-lint**; expect a couple of passes.
6. **Dryness check** — zero findings is NOT the goal. Three ways a rewrite
   passes the linter and still fails:
   - *Drier* — hedges stripped, texture gone. Measure it: `nabokov --stats`
     prints burstiness (sentence-length variety) and diversity (vocabulary
     variety, MATTR). Run it before and after. If your rewrite lowered either
     number, the text got flatter.
   - *Blander* — slop became clean generic claims that fail the
     competitor-name test. No new concrete fact and no stance means the slop
     was paraphrased, not fixed.
   - *Monotone* — your own splits open every sentence the same way ("We… We…
     We…"). Read the openers *and the paragraph endings* down the page; vary
     them.
7. **Stop** when warnings, errors, and judgment issues are handled — minus
   anything the user declined. Remaining `info` is the author's call.
8. **Verify & report.** Check that links, code, and structure are intact and
   the meaning held. Report in plain words: *N found → M fixed, K need your
   approval*.

## Fix playbook — static

Findings not listed here carry their fix in the message (NB304 names the verb,
NB401 the simpler phrase).

| Code | Fix |
|------|-----|
| NB201/NB202 | Split into shorter sentences. Long sentences are half of burstiness, so never split them all. Vary the new openers (a time phrase, an object, a clause) so splits don't create "We did X. We did Y." chains. |
| NB301/NB302/NB303/NB510 | Act only at warning level. Thin, don't remove all. Fold weak adverbs into stronger verbs. Rewrite the weakest passives; passive that keeps the known topic in front is fine. Keep hedges that do work. |
| NB305 | Name the real subject. Keep "there is no X" when existence itself is the point. |
| NB501–NB508 | Rewrite the tell: drop the not-X-but-Y shape, cut puffery, trim em-dashes/emoji, break the triple. |
| NB502/NB503 | Deleting the buzzword treats the symptom. Put the concrete case first — then the claim can arrive plain. |
| NB509 | Vary sentence length — mix short and long. Working range: short is 3–8 words, long is 25–40. Ends of a range to visit, not a pattern to alternate. The finding points at the flattest run — start there. |
| NB512/NB521 | Vary sentence and paragraph openers. Reorder, merge, or drop the opener word — a paragraph break is already a transition. |
| NB518 | Vary list size: two items, or four — not always three. |
| NB528 | The words it names repeat because the *content* repeats. Cut or merge the sentences that re-say the same thing; vary sentence subjects. Do NOT fix it with synonym swaps — synonym cycling is its own tell. |
| NB601 | The paragraph names nothing concrete. NEVER invent detail — ask the user for a real example or number. If abstract is the honest register (philosophy, math), leave it. |

## Fix playbook — judgment

- Empty / interchangeable sentence → **never paraphrase it**. A neutral
  rewrite of an empty sentence is still empty. Puffery usually hides a real
  event: someone decided, delayed, shipped, broke, traded off. Write *who
  did what, and why*:
  - slop: "this transformative journey stands as a testament to the power of innovation"
  - paraphrase trap: "the result is a better product that is easier to adopt"
  - fix: "we delayed the rollout because onboarding wasn't good enough"
  If the source has no event, compress to one honest short claim — or cut,
  and ask the user for the missing fact. De-slopping *shrinks* text;
  same-length output with no new fact means you paraphrased.
- No real detail → add a true example or number (ask if you have none).
- False range / dead metaphor / fake wisdom → delete; say the plain thing.
- Synonym cycling → pick one name and repeat it.
- Invented facts → keep only what the source supports.
- Diff writing → describe the current state.
- Hollow ending / no stance → take a stance or cut. Both change meaning, so
  ask — and the stance must be the author's, so ask which.

## STOP and ask before any BIG change

Small edits (word swaps, sentence splits, active voice) go ahead without
asking. Ask first — as one batch — before a change that:

- changes meaning or a factual claim. Deleting a hedge that guards a claim
  counts; thinning qualifiers that do no work does not;
- removes or merges content, an example, or a section;
- restructures heavily or rewrites the author's voice or tone;
- re-authors a passage instead of editing it;
- would **add** detail you don't have — never invent facts to fill a gap.

## Guardrails

- **Meaning first.** If a clean fix and a faithful fix conflict, keep the
  meaning and ask.
- **Quotes are evidence, not the author's prose.** Never edit quoted material
  or cited examples ("phrases like X" shown for criticism). This holds even
  when the quote marks were lost in conversion. nabokov skips quoted spans;
  give the same care to what its heuristics miss.
- **Don't dry the text out.** Zero `info` findings is a failure, not a goal;
  success is warnings fixed with the voice intact.
- **Clean slop is still slop.** The linter can't tell "clean and concrete"
  from "clean and interchangeable" — that judgment is yours alone.
- **Never invent** facts, examples, or numbers to satisfy a check.
- **Never fake imperfection.** Don't add spelling or grammar mistakes to look
  human — detectors don't reward broken English, and readers notice. Human
  texture means variety and voice, not errors.
- **Preserve markup** — nabokov ignores URLs, code, and headings; so must you.
- **Respect voice.** Emoji, em-dashes, and punchy phrasing are often
  deliberate style — use `--ai` when de-slopping is the goal, not by default.
  If other writing by the same author is available, read some first. Note the
  average *and the range* of sentence length, the punctuation habits, and any
  recurring tics — then edit inside that pattern, not toward a generic one.
- Use inline `<!-- nabokov: ignore NBxxx -->` only for exceptions the user
  agrees to — don't silence findings to "win".
