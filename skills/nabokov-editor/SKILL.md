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

Loop on the `flake8` output. What the static layer covers:

- **Readability**: hard / very-hard sentences, a document grade (`--max-grade`).
- **Word/phrase**: adverbs, passive voice, qualifiers, wordy phrases (with a fix).
- **AI tells (`--ai`)**: `it's not X, it's Y` negation-contrast; puffery vocabulary
  (`delve`, `tapestry`, `embark`); editorializing and significance inflation; chatbot
  filler and signposting; overused transitions; em-dash and emoji overuse; rule-of-three
  fragments; **flat sentence rhythm (low burstiness)**; weak intensifiers; participial
  "significance" closers; repeated sentence openers.

Full code list: `nabokov --list-rules` and `docs/RULES.md`.

**Triage by severity** (from `--format=json`): a `warning` is a confident tell — fix it
with a small, meaning-preserving edit. An `info` is an advisory "hard part" static isn't
sure about (burstiness, intensifiers, transitions, editorializing, participial closers,
repeated openers) — you decide whether changing it improves the text or just fights the
author's voice. Static suggests; you decide.

## Layer 2 — judgment (read the text yourself)

Static rules see form, not meaning. After the linter, read the prose and flag these —
the core of every humanizer skill, and the part a linter cannot do:

- **Vapidity** — sentences that are grammatical but say nothing. The strongest tell.
- **No lived detail** — confident and generic, with no concrete example, number, or
  first-hand specific ("this broke in production" energy).
- **False ranges** — "from X to Y" where X and Y aren't on a real scale.
- **Manufactured aphorisms** — "X is the language of Y", tidy fake wisdom.
- **Synonym cycling / elegant variation** — the same thing renamed each mention
  (protagonist → main character → hero).
- **Speculative gap-filling** — inventing facts or biography with stock phrases when
  the source doesn't say ("is believed to", "likely", "keeps a low profile").
- **Diff-anchored writing** — narrating the change ("was added to replace") instead of
  describing the current state.
- **Hollow conclusion** — "the future looks bright", "exciting times ahead".
- **Both-sides mush** — every claim hedged, no stance taken.
- **Dead / nonsensical metaphor** — imagery that adds nothing or doesn't parse.
- **Press-release / sycophantic tone** — throat-clearing, over-politeness, hype.

## Workflow (the loop)

1. **Static pass**: `nabokov --format=flake8 --ai <file>`.
2. **Judgment pass**: read the text; note the Layer-2 issues.
3. **Fix, preserving meaning** — statement by statement (playbooks below). Keep the
   author's intent, facts, links, code, and structure. Never invent content.
4. **Approval gate**: if a fix needs a *big change* (below), collect it and ask first.
5. **Re-lint**: run nabokov again; fix anything new. Tokenization estimates are
   imperfect, so expect a couple of passes.
6. **Stop** when the static layer is clean and the judgment issues are resolved
   (minus anything the user declined).
7. **Verify & report**: links, code, and structure intact; meaning preserved.
   Summarize *N found → M fixed, K needed approval*.

## Fix playbook — static (small edits, apply directly)

| Code | Fix |
|------|-----|
| NB201 / NB202 | Split into shorter sentences (nabokov never flags one under the target's minimum — 14 words for the default NORMAL, 8 for ACCESSIBLE), but keep it natural. |
| NB301 | Cut the adverb or fold it into a stronger verb. |
| NB302 | Rewrite in active voice. |
| NB303 / NB510 | Delete the hedge or weak intensifier unless it earns its place. |
| NB401 | Use the simpler suggestion in the message. |
| NB501–NB508 | Recast the tell: drop the antithesis, cut puffery, trim em-dashes/emoji, break the triad. |
| NB509 | Vary sentence length — mix short and long — to raise burstiness. |
| NB511 | Replace the ", -ing …" significance tail with a plain clause or cut it. |
| NB512 | Vary the sentence openers. |

## Fix playbook — judgment

- Vapidity / hollow → cut it, or replace with one concrete, specific claim.
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
- **Never fabricate** facts, examples, or numbers to satisfy a check.
- **Preserve markup** — nabokov ignores URLs, code, and headings; so must you.
- **Respect voice.** The `--ai` checks flag emoji, em-dashes, and punchy phrasing that
  are often the author's deliberate style. Turn them on when de-slopping is the goal;
  don't strip voice by default.
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
