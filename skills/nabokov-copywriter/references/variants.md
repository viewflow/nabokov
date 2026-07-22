# Variants and the fresh-eyes check

Iterating one draft in a single context drifts. Each edit makes a paragraph
stronger, and the whole piece quietly goes flat — the model anchors on the
over-worked version and keeps "improving" it toward a press release. This is a
measured effect, not a hunch. On a real LinkedIn post, successive polishing
dropped sentence-length variation (burstiness CV) from 0.41 to 0.35 — and every
individual edit still looked like a win.

The fix is not more polishing. It is a fresh, independent look — and variants that
never saw the polishing history.

## The method (works on any host)

1. **Diverge, don't iterate.** Produce two or three variants from *different
   structural angles* — PAS vs BAB vs a bare open loop — each built from the same
   facts. They are not edits of one another; that is the point. Divergent angles
   stop the copy converging on one flavor.

2. **Judge with fresh eyes.** Evaluate each variant as if you had not written it.
   Re-lint (`nabokov --ai --target <genre>`), run the fabrication check (every
   specific traces to a real fact), and score goal-fit. On a host with subagents,
   spawn a judge in a *fresh context* that never saw how the variant was made — it
   can't anchor on a draft it hasn't read.

3. **Check rhythm against the source — the drift detector.** Re-linting in
   isolation is not enough: nabokov's flat-rhythm rule (NB509) can pass while a
   piece still flattens. So read the burstiness number directly — `nabokov --stats
   <file>` prints it per file — and compare each variant's to the *original
   draft's*, not to zero. If a "cleaner" variant has markedly lower burstiness than
   the source, polishing dried it out — prefer the variant that kept the variation,
   or graft the short punchy lines back in. (Burstiness is the sentence-length CV;
   the tool computes it, so you never eyeball or reimplement it.)

4. **Pick or graft.** Choose the strongest variant, or lift the best lines from
   each into one. Never average them — a blend of three voices is mush.

## Mechanism, by host

- **A single agent** (Cursor, Codex, Gemini, plain Claude): generate the variants,
  then critique each in a *separate* pass, reading it cold. Weaker than true
  isolation, but it still breaks most of the anchoring.
- **Subagents** (the Claude Code Agent tool, and similar): spawn each variant and
  each judge in its own fresh context. This is the "independent context" the method
  wants, and it is cheap.
- **A Claude Code workflow** (opt-in): fan the variants out in parallel, judge each
  in isolation, and rank them in one deterministic run. This is the heavy option.
  A workflow is **user-triggered** — the user asks for it ("use a workflow"); this
  skill never fires one on its own, and no other host needs it.

## The workflow, ready to run (Claude Code only)

Optional. When a piece is worth several shots, offer it to the user — and run it
only when they opt in (same rule as above: never fire it unasked). Pass the source
draft, the real facts, the goal, the linter target, and the source's burstiness as
`args` — get that last number once with `nabokov --stats <sourcefile>`. Each judge
runs blind, lints the variant with the real tool (`nabokov --stats --ai`), and
reports the tool's burstiness so drift is measured, never estimated.

```js
export const meta = {
  name: 'copy-variants',
  description: 'Generate copy variants from different angles, judge each blind with nabokov, flag rhythm drift vs the source',
  phases: [{ title: 'Diverge' }, { title: 'Judge' }],
}

const ANGLES  = args?.angles || ['PAS', 'BAB', 'open-loop']
const FACTS   = args?.facts  || ''
const SOURCE  = args?.source || ''
const GOAL    = args?.goal   || 'sell'
const TARGET  = args?.target || 'social'
const SRC_CV  = args?.srcBurstiness ?? null  // from `nabokov --stats <sourcefile>`

const VERDICT = {
  type: 'object',
  properties: {
    burstiness: { type: 'number' },       // read from `nabokov --stats`, not estimated
    fabricated: { type: 'array', items: { type: 'string' } },
    goalFit: { type: 'string' },
    lintNotes: { type: 'string' },
    score: { type: 'number' },
  },
  required: ['burstiness', 'fabricated', 'score'],
}

const ranked = await pipeline(
  ANGLES,
  (angle) => agent(
    `Write a ${GOAL} variant of this copy using the ${angle} structure. Use ONLY these facts — invent nothing. `
    + `If a scene needs a detail you don't have, leave a [ASK: ...] placeholder instead of making one up. Return only the copy.\n\n`
    + `SOURCE DRAFT:\n${SOURCE}\n\nFACTS:\n${FACTS}`,
    { label: `write:${angle}`, phase: 'Diverge' }
  ),
  (text, angle) => agent(
    `You did NOT write this and have not seen how it was made. Judge this ${GOAL} copy cold.\n`
    + `1. Write it to a temp file and run: nabokov --stats --ai --target ${TARGET} <file>\n`
    + `2. Report its burstiness from the --stats line, and any lint tells.\n`
    + `3. List every fabricated specific (number, name, price, testimonial) NOT in the facts.\n`
    + `4. Rate goal-fit and give a 0-10 score.\n\n`
    + `FACTS:\n${FACTS}\n\nCOPY:\n${text}`,
    { label: `judge:${angle}`, phase: 'Judge', schema: VERDICT }
  ).then(v => ({
    angle, text, verdict: v,
    drift: (SRC_CV != null && v?.burstiness != null) ? Number((v.burstiness - SRC_CV).toFixed(2)) : null,
  }))
)

// Negative drift = flatter than the source (polished dry). Surface it next to the score.
return ranked.filter(Boolean).sort((a, b) => (b.verdict?.score || 0) - (a.verdict?.score || 0))
```

Read the result with the score *and* the drift: a top-scored variant with a big
negative drift got polished flat — graft its facts into the variant that kept the
rhythm. The burstiness is nabokov's own number, so it matches NB509 exactly. The
`[ASK: ...]` placeholders are the fabrication line holding; fill them with the
user's real detail before shipping.
