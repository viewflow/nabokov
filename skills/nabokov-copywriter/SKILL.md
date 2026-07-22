---
name: nabokov-copywriter
description: >-
  Turn a flat draft into copy that pulls the reader through — for a launch post,
  landing page, sales email, ad, cold outreach, or any piece meant to persuade,
  sell, or get engagement. Use whenever the user wants writing that "flows",
  "lands", "sells", "hooks", "converts", reads like a human wrote it, or should be
  rewritten toward a goal (reach, sales, discussion, trust). Adds rhythm, sensory
  detail, and a proven structure — from the user's REAL facts, never invented —
  then re-lints with nabokov so the polish never slides back into slop. The
  sibling of nabokov-editor: editor preserves meaning and cleans; copywriter
  deliberately enlivens and restructures toward an outcome.
---

# nabokov-copywriter

nabokov-editor cleans a draft and guards its meaning. This skill does the
opposite move on purpose: it **adds** — rhythm, a scene, a structure that carries
the reader to a call to action. A clean draft can still be flat. This makes it
land.

One rule governs everything and never bends:

> **Craft, not fabrication.** You add *how it's said* — never *what happened*.
> Every concrete detail, number, name, and outcome comes from the user. When a
> technique needs a fact you don't have, you ask for it. You never invent one to
> fill the scene. This is the line that keeps enlivened copy from becoming
> confident LLM fiction.

## Step 0 — goal and facts, before any writing

Two things must be explicit before you touch the draft. If either is missing,
ask — one short question each.

**The goal.** Copy has one job; the structure follows from it. Confirm which:

| Goal | What it optimizes | Default formula |
|------|-------------------|-----------------|
| **Sell** | a decision to buy | PAS or AIDA (ODC for a warm list) |
| **Reach** | shares and forwards | BAB or an open loop |
| **Provoke** | replies and debate | PMHS or a clear stance |
| **Trust** | credibility | QUEST or plain exposition |

**The facts.** List what real material you have: the product, the event, the
numbers, the customer, the before/after, the objection. Copy is built from this,
not from adjectives. If the draft is generic *because the facts are missing*, the
task is to collect them, not to decorate — ask the user.

Read [references/formulas.md](references/formulas.md) once the goal is set — it
holds each formula's skeleton, the goal→formula choice, and CTA patterns.

## The four passes

Run in order. Each pass hands a better draft to the next.

1. **De-slop** — clear the machine tells first, so you enliven signal, not noise.
   This is the nabokov-editor job; run it, or run the linter directly:
   `uvx nabokov --ai <file>`. Cut puffery, triads, negation-contrast, em-dash
   pileups, hollow closers. A draft full of slop can't be made to flow — the flat
   rhythm *is* the slop.

2. **Enliven** — the cinematic pass. Turn labels into scenes, weak verbs into
   strong ones, abstractions into something the reader can see — **all from the
   user's facts**. Show, don't tell: "the customer was relieved" carries nothing;
   the symptom the user witnessed does. Sensory and concrete detail, one strong
   verb over a verb-plus-adverb crutch, a metaphor only when it's grounded in the
   real domain. This is where you ask for a missing detail rather than paint one.
   Full recipe: [references/enliven.md](references/enliven.md).

3. **Flow** — the rhythm pass (Gary Provost). Vary sentence length: a three-word
   sentence hits; a long one carries the reader on a current. A run of same-length
   sentences drones, however good each one is. Read it aloud in your head; where
   it plods, split one sentence short and let the next run long. nabokov's NB509
   flags the flat stretches.

4. **Assemble for the goal** — reorder the enlivened material into the chosen
   formula, open a loop early and pay it off late, and land the CTA so it grows
   out of the copy instead of bolting on. Reordering the whole piece and adding a
   CTA are **big changes** — batch them and get approval before restructuring.

When a piece is worth more than one shot, don't keep polishing the same draft —
polishing drifts it flat. Diverge into a few variants from different angles and
judge them cold instead. [references/variants.md](references/variants.md) has the
method, and a ready Claude Code workflow you can trigger for it.

## The linter is the floor, not the ceiling

After enlivening, re-lint: `uvx nabokov --ai <file>`. Pick the target for the
genre — `--target social` for a short post (staccato is native there),
`--target essay` for a long read (it tolerates the long sentences that carry
voice), `--target email` for outreach. The linter keeps the polish honest: it
catches you if a rewrite slid back into slop.

But zero findings is **not** the goal, and here the trap is sharper than in
editing. Dry, "clean" copy that names no benefit and takes no stance passes every
check and sells nothing. The infostyle mistake is to strip a draft down to bare
verifiable facts until it reads like a spec sheet — correct, and dead. Keep the
voice, the one honest emotion, the sensory line. A finding is a prompt to look,
not an order to delete.

## Approval gates — ask once, batched

Small moves proceed: a stronger verb, a split sentence, a tightened line. Stop and
ask before anything that changes the piece's shape or substance:

- restructuring into a formula or reordering sections;
- adding or rewriting the CTA, offer, or deadline;
- **adding any concrete detail you don't have** — the fabrication line;
- shifting the claim, the promise, or the stance;
- rewriting the author's voice or tone wholesale.

## Guardrails

- **Craft, not fabrication.** Restated because it's the whole game: enliven the
  user's facts, never manufacture facts to enliven. No invented metrics,
  testimonials, outcomes, or biography. Missing detail is a question, not a
  guess.
- **The goal is the user's call.** Don't quietly optimize for engagement when
  they asked for trust; the formula follows their stated goal.
- **Preserve markup, links, code, prices, and legal claims** exactly — copy that
  misstates a price or a guarantee is worse than flat copy.
- **One honest emotion beats three manufactured ones.** The fix for flat copy is
  a real specific, not a pile of intensifiers. If enlivening adds no fact and no
  feeling the source supports, it's decoration — cut it.
- **Match the register to the brand.** A dev tool earns blunt and plain; a luxury
  brand earns long, textured sentences. Read other copy by the same author or
  brand first when it's available.
- **Discard the hype.** Ignore unverifiable "X× conversion" and "+N% reach"
  numbers from any playbook, including the ones that seeded this skill. Claims in
  the copy carry the user's evidence or they don't ship.
