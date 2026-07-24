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
opposite move on purpose: it **adds** — rhythm, a scene, a structure that
carries the reader to a call to action. A clean draft can still be flat. This
skill makes it land.

One rule governs everything and never bends:

> **Craft, not fabrication.** You add *how it's said* — never *what
> happened*. Every concrete detail, number, name, and outcome comes from the
> user. When a technique needs a fact you don't have, ask for it. Never
> invent one to fill the scene. This line is what separates lively copy from
> confident LLM fiction.

## Talk plainly

When you talk to the user — questions, approval requests, the final report —
use plain English (B1/B2 level). Short sentences. Common words. Name a rule
by its code plus a plain gloss: "NB509 (flat rhythm)", not linter jargon.

## Step 0 — goal and facts, before any writing

Two things must be clear before you touch the draft. If either is missing,
ask — one short question each.

**The goal.** Copy has one job, and the structure follows from it:

| Goal | What it optimizes | Default formula |
|------|-------------------|-----------------|
| **Sell** | a decision to buy | PAS or AIDA (ODC for a warm list) |
| **Reach** | shares and forwards | BAB or an open loop |
| **Provoke** | replies and debate | PMHS or a clear stance |
| **Trust** | credibility | QUEST or plain exposition |

**The facts.** List the real material: the product, the event, the numbers,
the customer, the before/after, the objection. Copy is built from this, not
from adjectives. If the draft is generic *because the facts are missing*, the
job is to collect them, not to decorate. Ask the user.

Read [references/formulas.md](references/formulas.md) once the goal is set.
It holds each formula's skeleton, the goal→formula choice, and CTA patterns.

## The five passes

Run them in order. Each pass hands a better draft to the next.

1. **De-slop** — clear the machine tells first, so you enliven signal, not
   noise. This is the nabokov-editor job; run it, or run the linter directly:
   `uvx nabokov --ai <file>`. Cut the confident tells — puffery, the
   not-X-but-Y shape, hollow endings. Thin em-dash pileups and triples under
   the editor's severity rules. Triples (NB507) are advisory on purpose:
   human staccato looks the same, so judge each one. A draft full of slop
   can't be made to flow — the flat rhythm *is* the slop.

2. **Enliven** — the cinematic pass. Turn labels into scenes, weak verbs into
   strong ones, abstractions into something the reader can see — **all from
   the user's facts**. Show, don't tell: "the customer was relieved" carries
   nothing; the symptom the user saw does. Use sensory, concrete detail. Use
   one strong verb instead of a verb plus adverb. Use a metaphor only when it
   comes from the real domain. This is where you ask for a missing detail
   instead of painting one. Full recipe:
   [references/enliven.md](references/enliven.md).

3. **Flow** — the rhythm pass (Gary Provost). Vary sentence length: a
   three-word sentence hits; a long one carries the reader on a current. A
   run of same-length sentences drones, however good each one is. Read it
   aloud in your head. Where it plods, split one sentence short and let the
   next run long. As a working range: a short sentence is 3–8 words, a long
   one 25–40. Treat these as the ends of a range to visit, not a
   short-long-short pattern to alternate — a mechanical see-saw drones as
   badly as uniform length. NB509 flags the flat stretches and points at the
   flattest run. (Logical flow between sections is its own pass — Connect,
   next.) Vary paragraph *endings* too:
   ending every one on a punchline is a machine cadence. Two or three
   punchline endings per piece, where the argument peaks; the rest end flat.
   Ration the figures the same way — one not-X-but-Y hits, three are a tic
   (NB501 flags each). And know the trap in this very pass: the Provost
   cadence *executed too cleanly* is now itself a machine signature. Trained
   detectors flag copy where every beat lands — anaphora runs ("The career
   that… The income that… The lifestyle that…"), balanced two-clause
   aphorisms, a fragment couplet at every hinge. Caps per piece: one fragment
   couplet, one aphorism, at most one anaphora run — and don't let the hook,
   the hinge, *and* the close all land on beats. Watch the commas too:
   machine prose punctuates on a metronome, a comma or dash every clause of
   the same length. Leave one long, loosely coordinated sentence unsplit —
   the kind that runs on "and… and…" the way people actually talk. The
   `--score` punct-rhythm number tracks this. The linter backs the caps:
   NB530 flags a fragment pileup, NB529 flags punchline-heavy paragraph
   endings. But `--target social` silences NB507 and NB512 (staccato and
   repeated openers are the genre), so on a social post you enforce those
   two caps by eye.

4. **Connect** — the coherence pass. Copy fails not only sentence by
   sentence but section by section: parts that each read well yet don't carry
   the reader from one to the next. Sentence rhythm can be perfect and the
   piece still read as beads with no string. Do this as a checklist, not a
   vibe:
   - List each section or scene in order.
   - For each, name the **one sentence** that carries the reader here from the
     section before. If you can't name it, the bridge is missing — the copy
     jumped a topic. Fix it before shipping.
   - Bridge with an **echo of the prior point**, not a bolted-on connector.
     "That reminded me of…", "Recently, I was listening to…", "It made me
     wonder…" *announce* a link instead of building one (NB531 flags these).
   - Watch the failure this pass exists for: **serial anecdote stacking** —
     two or three "I read / I heard / I was asked" hooks piled up in the
     opening, fused only by a claim that "they are all about the same thing"
     (NB532 flags that claim). The fix: pick one entry and thread the others
     through it, and name the shared idea *before* you assert unity, not
     after. The reader should feel the connection, not be told it exists.

   NB531 and NB532 flag *where* to look, never whether the bridge is real —
   that judgment is yours. A clean linter run is not a coherence pass.

5. **Assemble for the goal** — reorder the connected material into the chosen
   formula. Open a loop early and pay it off late. Land the CTA so it grows
   out of the copy instead of bolting on. Reordering the whole piece and
   adding a CTA are **big changes** — collect them and get approval before
   restructuring.

When a piece is worth more than one shot, don't keep polishing the same
draft — polishing drifts it flat. Write a few variants from different angles
and judge them cold. [references/variants.md](references/variants.md) has the
method and a ready Claude Code workflow for it.

## The linter is the floor, not the ceiling

After enlivening, re-lint: `uvx nabokov --ai <file>`. Pick the target for the
genre: `--target social` for a short post (staccato is native there),
`--target essay` for a long read, `--target email` for outreach. The linter
keeps the polish honest: it catches you if a rewrite slid back into slop.

**Voice profiles.** nabokov can also lint against an author's style
signature. `uvx nabokov --profile-card list` names the bundled profiles;
`--style <name-or-json>` adds the NB7xx drift checks — connectors the author
never uses, rhythm flatter than their baseline, punctuation far above their
rate. Use it in this order:

1. If the author has a corpus (their own posts), build a personal profile
   first: `uvx nabokov --build-profile author.style.json their-posts/` —
   that profile beats any bundled one.
2. Otherwise propose the closest bundled profile by genre and **confirm with
   the user** before using it: idea essays → `paulgraham`; plain-style
   opinion → `orwell`; finance/investing → `housel`; business/tech deep
   dives → `patio11`; long argumentative essays → `scottalexander`; short
   personal notes → `sivers`; literary prose → `nabokov`.
3. Read the card (`--profile-card <name>`) before rewriting, and rewrite
   *into* that distribution — its connectors, punctuation rates, and rhythm
   are the register to match. The minimal-paraphrase rule still wins:
   the profile guides only lines you already have to rewrite. A profile
   supplies register, never facts — inventing content "in the author's
   style" is still fabrication.

Cap the polish loop at **two** enliven → re-lint rounds, and on the second
round touch only the lines the linter (or a detector) still flags — every
extra pass over a clean line drifts the copy flat. If findings survive round
two, report them with your judgment instead of churning; drafting a fresh
variant beats a third polish (see variants.md).

But zero findings is **not** the goal, and here the trap is sharper than in
editing. Dry, "clean" copy that names no benefit and takes no stance passes
every check and sells nothing. The infostyle mistake is to strip a draft down
to bare verifiable facts until it reads like a spec sheet — correct, and
dead. Keep the voice, the one honest emotion, the sensory line. A finding is
a prompt to look, not an order to delete.

Grounding also buys back rhetoric: each checkable fact from the user's
material earns the copy one more flourish. Rhetoric without grounding is what
detectors and readers smell. For the worked example, read the "Human signals"
section of nabokov-editor. It shows how Substack's Pangram-launch post scores
100% human on the very detector it announces.

## Approval gates — ask once, batched

Small moves go ahead: a stronger verb, a split sentence, a tightened line.
Stop and ask before anything that changes the piece's shape or substance:

- restructuring into a formula or reordering sections;
- adding or rewriting the CTA, offer, or deadline;
- **adding any concrete detail you don't have** — the fabrication line;
- shifting the claim, the promise, or the stance;
- rewriting the author's voice or tone wholesale.

## Guardrails

- **Craft, not fabrication.** Restated because it's the whole game: enliven
  the user's facts, never manufacture facts to enliven. No invented metrics,
  testimonials, outcomes, or biography. A missing detail is a question, not
  a guess.
- **Minimal paraphrase.** Never rewrite a line that nothing flagged — not the
  linter, not a detector, not your own judgment pass. Every gratuitous
  paraphrase swaps the author's idiolect for model idiolect, which is exactly
  what trained classifiers are trained on. The author's surviving words are
  the one human signal you cannot synthesize; smoothing "This thought stayed
  with me" into "The thought stuck" is a loss, not a fix.
- **The goal is the user's call.** Don't quietly optimize for engagement when
  they asked for trust; the formula follows their stated goal.
- **Preserve markup, links, code, prices, and legal claims** exactly — copy
  that misstates a price or a guarantee is worse than flat copy.
- **One honest emotion beats three manufactured ones.** The fix for flat copy
  is a real specific, not a pile of intensifiers. If enlivening adds no fact
  and no feeling the source supports, it's decoration — cut it.
- **Match the register to the brand.** A dev tool earns blunt and plain; a
  luxury brand earns long, textured sentences. When other copy by the same
  author or brand is available, read some first.
- **Discard the hype.** Ignore unverifiable "X× conversion" and "+N% reach"
  numbers from any playbook, including the ones that seeded this skill.
  Claims in the copy carry the user's evidence or they don't ship.
