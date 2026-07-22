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

One skill to lint and de-slop prose. It runs in two layers and loops until clean:

1. **Static** — the `nabokov` linter catches the mechanical tells (deterministic, fast,
   no model needed).
2. **Judgment** — you (the agent) catch the tells no regex can see: hollow content,
   invented detail, dead metaphors.

Then rewrite **preserving meaning**, re-lint, and repeat — asking the user before any
large or meaning-changing edit. This replaces scattered humanizer/unslop skills: the
mechanical patterns run as fast static rules; the qualitative ones run as an explicit
checklist instead of a vague prompt.

## Layer 1 — static (run nabokov)

Setup: use `uvx nabokov …` (no install, fetches the model on first use), or install once
with `uv tool install nabokov && nabokov download-model`.

```sh
nabokov --format=flake8 <file>        # readability + style checks
nabokov --format=flake8 --ai <file>   # add the AI-writing / de-slop checks (NB5xx)
```

For essays, blog posts, and opinion pieces add `--target essay` — it tolerates the
longer sentences literary prose sustains deliberately and carries the loosest style
budgets. For social posts use `--target social` (staccato fragments and repeated
openers are the genre there, so those tells are off); for business email,
`--target email` (tightest budgets — a high-trust audience is where puffery costs
the most).

Loop on the `flake8` output. What the static layer covers:

- **Readability**: hard / very-hard sentences, a document grade (`--max-grade`),
  buried main clauses (NB203 — where a hard sentence can be split).
- **Word/phrase**: adverbs, passive voice, qualifiers, wordy phrases (with a fix),
  nominalizations behind light verbs (NB304, with the verb to use), dummy
  subjects (NB305).
- **Semantic density**: abstract "empty prose" paragraphs (NB601), scored against
  the Brysbaert concreteness norms — the linter now *detects* the strongest
  Layer-2 tell; the fix stays with you (below).
- **AI tells (`--ai`)**: `it's not X, it's Y` negation-contrast; puffery vocabulary
  (`delve`, `tapestry`, `embark`); editorializing and significance inflation; chatbot
  filler and signposting; overused transitions; em-dash and emoji overuse; rule-of-three
  fragments; **flat sentence rhythm (low burstiness)**; weak intensifiers; participial
  "significance" closers; repeated sentence openers.

Full code list: `nabokov --list-rules` and `docs/RULES.md`.

**Triage by severity** (from `--format=json`): an `error` is a document-level failure
(NB101 over `--max-grade`). A `warning` on NB2xx/NB4xx/NB5xx is a confident tell — fix
it with a small, meaning-preserving edit. An `info` is advisory — you decide whether
changing it improves the text or just fights the author's voice. Static suggests; you
decide.

The style checks (NB301 adverbs, NB302 passive, NB303 qualifiers, NB401 wordy
phrases) use **severity-by-density**: each finding is `info` while the document
stays inside its per-1000-word budget, and the whole set escalates to `warning`
only when the text overuses the pattern. NB202 likewise drops to `info` when the
whole document reads fine for its target, and a puffery lemma (NB502) the document
repeats 3+ times is topic vocabulary, reported as `info`. An escalated style warning means "too many", **not** "each one
is wrong" — thin them out; don't eradicate them. As a rule of thumb, cut at most about
a third of the flagged qualifiers/adverbs — the ones doing no work — and leave the
rest. And in first-person or opinion prose, hedges ("I think", "probably") are
epistemic honesty: deleting one turns a hedged claim into an absolute claim. That is a
meaning change and goes through the approval gate.

## Layer 2 — judgment (read the text yourself)

Static rules see form, not meaning. After the linter, read the prose and flag these —
the core of every humanizer skill, and the part a linter cannot do:

- **Vapidity** — sentences that are grammatical but say nothing. The strongest tell.
- **Interchangeability** — swap in a competitor's name (or any product, any team):
  if the sentence still works unchanged, it says nothing about *this* subject.
  "Our platform gives teams the insights they need" fits every B2B site on earth —
  clean grammar, zero content.
- **No lived detail** — confident and generic, with no concrete example, number, or
  first-hand specific ("this broke in production" energy).
- **False ranges** — "from X to Y" where X and Y aren't on a real scale.
- **Manufactured aphorisms** — "X is the language of Y", tidy fake wisdom.
- **Synonym cycling / elegant variation** — the same thing renamed each mention
  (protagonist → main character → hero).
- **Catalogue instead of integration** — elements that constrain and produce each
  other presented as a flat list. Ask what each item does to the others, what
  breaks if one is removed — then write the relationships, not the inventory.
- **Self-labeling significance** — "that last move is the contrarian one", "here's
  where it gets clever". The label does the work the content was supposed to do;
  cut it and restructure so the right item carries the weight itself.
- **Treadmill prose** — per paragraph, ask "what's actually new here?" If 40–60%
  could be cut with no information lost, the text restates its premise in fresh
  words instead of advancing it. Name each paragraph's one contribution; cut the
  ones without one.
- **Signposting out of scale** — "let us explore three ways…" narrates the move
  instead of making it. Judge density against document scale: ten orientation
  moments serve a hundred-page layered argument; three per page in a short flat
  text is a tic. Cut the tics, keep the load-bearing ones.
- **Speculative gap-filling** — inventing facts or biography with stock phrases when
  the source doesn't say ("is believed to", "likely", "keeps a low profile").
- **Diff-anchored writing** — narrating the change ("was added to replace") instead of
  describing the current state.
- **Hollow conclusion** — "the future looks bright", "exciting times ahead".
- **Both-sides mush** — every claim hedged, no stance taken.
- **Dead / nonsensical metaphor** — imagery that adds nothing or doesn't parse.
- **Press-release / sycophantic tone** — throat-clearing, over-politeness, hype.

## Macro pass — essays and arguments only

For an essay, opinion piece, or academic text (not READMEs or reference docs), add a
structural read after Layer 2. These come from Williams (*Style*), Zinsser, and the
Harvard/Purdue writing guides:

- **Thesis**: is the central claim *arguable* (answers how/why), or merely
  descriptive (answers who/what/when)? A descriptive thesis turns the essay into a
  report — flag it and propose a sharper claim for the user to approve.
- **Reverse outline**: write down each paragraph's one main point. The list should
  form a chain with no repeats and no dropped threads; a paragraph with two points
  wants splitting, two paragraphs with one point want merging (approval gate).
- **Stitching over signposting**: paragraph openers like *Moreover / Furthermore /
  Additionally* are mechanical connectors. The fix is not deleting the word — it's
  opening with a semantic echo of the previous paragraph's key concept, so the
  logic carries the transition.
- **Old-to-new flow** (cohesion): sentences should open with information the reader
  already has and end with the new. This is also the legitimate use of passive
  voice — keep a passive that fronts the known topic.
- **Conclusion**: synthesize, don't summarize. No new evidence, no apologies
  ("this is just one approach…"), no hollow closers. If the conclusion restates
  the intro, propose one of: zoom out to the bigger picture, name a consequence
  for the future, or end on the strongest concrete image.

## Workflow (the loop)

1. **Static pass**: `nabokov --format=flake8 --ai <file>`.
2. **Judgment pass**: read the text; note the Layer-2 issues. For essays and
   arguments, run the macro pass (thesis, reverse outline, stitching, conclusion).
3. **Fix, preserving meaning** — statement by statement (playbooks below). Keep the
   author's intent, facts, links, code, and structure. Never invent content.
   **Patch vs. rebuild**: when the static pass returns heavy vocabulary hits
   across 3+ categories *plus* flat rhythm (NB509), patching phrases won't fix
   it — the structure itself is generated. Propose a rebuild from the piece's
   one-sentence core instead (approval gate; this is a big change).
4. **Approval gate**: if a fix needs a *big change* (below), collect it and ask first.
5. **Re-lint**: run nabokov again; fix anything new. Tokenization estimates are
   imperfect, so expect a couple of passes.
6. **Dryness & blandness check**: zero style findings is NOT the goal. Two ways a
   rewrite passes the linter and still fails:
   - *Drier* — burstiness dropped (NB509 appears or worsens), every hedge and
     adverb stripped, flatter than the original. Restore texture: put back the
     hedges and rhythm that carried the author's voice.
   - *Blander* — the slop became clean generic claims that could ship on any
     product's site (the interchangeability test). The strong writing this skill
     aims at (Stripe, Linear, 37signals) is not merely shorter — it is more
     concrete and takes a position. If de-slopping produced no new concrete fact
     and no stance, the slop was paraphrased, not fixed: go back to the vapidity
     playbook.
7. **Stop** when warnings and errors are resolved and the judgment issues are
   handled (minus anything the user declined). Remaining `info` findings are fine —
   they are the author's call, not defects.
8. **Verify & report**: links, code, and structure intact; meaning preserved.
   Summarize *N found → M fixed, K needed approval*.

## Fix playbook — static (small edits, apply directly)

| Code | Fix |
|------|-----|
| NB201 / NB202 | Split into shorter sentences (nabokov never flags one under the target's minimum — 14 words for the default NORMAL, 8 for ACCESSIBLE), but keep it natural. Long sentences are half of burstiness — never split them all. |
| NB301 | Only when escalated to warning: thin the adverbs out — fold the weakest into stronger verbs, keep the ones doing work. As `info`, leave unless one clearly adds nothing. |
| NB302 | Only when escalated to warning: rewrite the weakest in active voice. Passive that puts the right thing first is fine. |
| NB303 / NB510 | Thin, don't eradicate: cut at most about a third — the ones doing no work. In first-person prose a hedge is epistemic honesty; deleting it changes the claim's strength (approval gate). |
| NB401 | Use the simpler suggestion in the message. |
| NB501–NB508 | Recast the tell: drop the antithesis, cut puffery, trim em-dashes/emoji, break the triad. |
| NB502 / NB503 | Inflation: deleting the amplifier treats the symptom. **Ground before generalize** — lay the concrete case first, then let the claim arrive plain; the reader already knows its weight. |
| NB518 | Vary enumeration size: two items for contrast, three for closure, four-plus for abundance. If every list is a triple, break some. |
| NB509 | Vary sentence length — mix short and long — to raise burstiness. |
| NB511 | Replace the ", -ing …" significance tail with a plain clause or cut it. |
| NB512 | Vary the sentence openers. |
| NB203 | Advisory: the main clause is buried. If the sentence also reads hard, split right before the pile-up or front-load the point; deliberate suspense stays. |
| NB304 | Use the verb from the message: "came to an agreement" → *agreed*. Almost always safe and meaning-preserving. |
| NB305 | Name the real subject: "There are many resorts in Colorado" → "Colorado has many resorts". Keep "there is no X" when existence itself is the point. |
| NB517 | Thin the cluster: keep the one generic-praise word doing work, replace the rest with specifics. |
| NB601 | The paragraph is grammatical but names nothing concrete. NEVER invent detail — ask the user for a real example, number, or image (approval gate). Once the case is laid, let the general claim arrive plain (ground before generalize). If the abstraction is the honest register (philosophy, math), leave it. |

## Fix playbook — judgment

- Vapidity / hollow / interchangeable → **never paraphrase it**. A neutral rewrite of
  an empty sentence is still empty — linted slop is still slop. Puffery usually
  buries a real event: someone decided, delayed, shipped, broke, or traded
  something off. Dig it out and write *who did what, and why*:
  - slop: "this transformative journey stands as a testament to the power of innovation"
  - paraphrase trap: "the result is a better product that is easier to adopt"
  - fix: "we delayed the rollout because onboarding wasn't good enough"
  If the source doesn't contain the event, compress to the one honest short claim —
  or cut the sentence and ask the user for the missing fact. De-slopping *shrinks*
  text; a rewrite that keeps the original length without gaining a fact is the trap.
- No lived detail → add a real example, number, or first-hand specific (ask the user if you don't have it).
- False range / dead metaphor / manufactured aphorism → delete; say the plain thing.
- Synonym cycling → pick one name and repeat it.
- Speculative gap-filling → remove the invented claim; state only what the source supports.
- Diff-anchored → describe the current state, not the change.
- Hollow conclusion / both-sides mush → take a stance or cut the paragraph.

## STOP and ask before any BIG change

Small edits (word swaps, splitting a sentence, active voice, dropping a hedge) proceed
automatically. Get the user's approval before a change that:

- alters meaning or any factual claim;
- removes or merges content, an example, or a section;
- restructures significantly (inline list → bullets, reordered sections);
- rewrites the author's voice/tone (de-slopping that strips personality, humor, emoji,
  or a deliberate device);
- needs you to substantially re-author a passage rather than lightly edit it;
- would **add** detail you don't have — never invent facts to fill a Layer-2 gap; ask.

Batch these so the user approves several at once.

## Guardrails

- **Meaning first.** If a clean fix and a faithful fix conflict, keep meaning and ask.
- **Quotes are evidence, not the author's prose.** Never edit quoted material —
  block quotes, epigraphs, poem or song excerpts, dialogue attributed to others.
  The same goes for **mentions**: phrases the author cites as specimens or examples
  ("phrases like X", "tags like Y", a wordy expression held up for criticism) are
  being exhibited, not used — never "fix" them, even when the italics or quote marks
  that marked them were lost in conversion. nabokov drops findings inside blockquotes
  and quoted spans; extend the same respect to quotes and mentions its heuristics
  miss (e.g. quoted verse in a plain-text file).
- **Don't dry the text out.** A rewrite that strips every hedge, adverb, and long
  sentence "passes the linter" and reads like cardboard. Zero `info` findings is an
  anti-goal; measure success by warnings resolved with voice intact.
- **Linted slop is still slop.** The linter can't tell "clean and concrete" from
  "clean and interchangeable" — that judgment is yours alone. Passing text that
  says nothing is a failure even at zero warnings.
- **Never fabricate** facts, examples, or numbers to satisfy a check.
- **Preserve markup** — nabokov ignores URLs, code, and headings; so must you.
- **Respect voice.** The `--ai` checks flag emoji, em-dashes, and punchy phrasing that
  are often the author's deliberate style. Turn them on when de-slopping is the goal;
  don't strip voice by default. If other writing by the same author is available,
  read some first — what looks like a tell in general may be the author's
  fingerprint in particular.
- Use inline `<!-- nabokov: ignore NBxxx -->` only for a finding the user agrees is a
  deliberate exception — don't silence findings to "win".

## Example

```
$ nabokov --format=flake8 --ai post.md
post.md:3:1: NB502 AI tell: puffery 'delve'
post.md:3:20: NB501 AI tell: negation-contrast 'not just a tool, it's'
post.md:7:1: NB509 AI tell: monotonous sentence rhythm (burstiness 0.28, aim for >= 0.40 by varying length)
```

- NB502 / NB501 → recast directly (drop "delve", cut the antithesis).
- NB509 → vary sentence length across the piece.
- Judgment pass → paragraph 2 is confident but says nothing; flag it and ask the user
  for a concrete example rather than inventing one.
```
$ nabokov --format=flake8 --ai post.md
0 issues in 1 file
```
Report: *3 static + 1 judgment found → 3 fixed, 1 needs a real example from you.*
