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

Lint and de-slop prose in three layers. Repeat until clean:

1. **Static** — the `nabokov` linter finds the mechanical tells.
2. **Judgment** — you find what no regex can see: empty content, invented
   detail, dead metaphors.
3. **Cadence** — you read the whole piece for beat, not words. This is the
   layer trained detectors key on, and the linter is blind to it by design.

Rewrite **without changing meaning**. Ask before any large change.

## Talk plainly

When you talk to the user — questions, approval requests, the final report —
use plain English (B1/B2 level). Short sentences. Common words. Name a rule by
its code plus a plain gloss: "NB302 (passive voice)", not linter jargon.

## Layer 1 — static

```sh
uvx 'nabokov>=26.7.7' --format=flake8 <file>  # first call: pins the floor these notes assume
uvx nabokov --format=flake8 --ai <file>       # add the AI-writing / de-slop checks (NB5xx)
uvx nabokov --format=json --ai <file>         # same findings, with fix + tier per finding
uvx nabokov --format=flake8 --ai --hotspots <file>   # + the worst paragraphs, ranked
```

**These notes describe nabokov 26.7.7 or newer.** The skill and the linter ship
through different channels — this file comes from git, the tool from PyPI — so
they can drift apart. Run the version-pinned form **once** at the start of a
session. If it fails to resolve, the installed tool is too old and every rule
below that it has never heard of will silently return nothing; say so instead of
reporting a clean file. After that first call, plain `uvx nabokov` is fine.

(`uvx` needs no install; or `uv tool install nabokov && nabokov download-model`
— note that a `uv tool install` does **not** auto-update, so it needs
`uv tool upgrade nabokov`.)
Pick a target. `--target essay` fits essays and blog posts — it allows long
sentences, because literary prose uses them on purpose. `social` fits short
posts. `email` fits business mail and is the strictest. Rule reference:
`nabokov --list-rules` and `docs/RULES.md`.

**Read the severity.**

- `error` — the document fails its grade limit (`--max-grade`).
- `warning` — a confident tell. Fix it with a small edit that keeps the meaning.
- `info` — advisory. Change it only when the change helps the text; don't
  fight the author's voice.

**Read the fix, and its tier.** Most findings now carry the fix. Severity says
how much it matters; the tier says what you may do with it.

- `→ to` (**replace**) — the tool checked the position. Apply it as written.
  An empty one prints as `→ delete it`: cut the flagged span, nothing else.
  Don't paraphrase around a replace; that is exactly the needless paraphrase
  the minimal-paraphrase rule forbids.
- `try: The team wrote the report` (**rewrite**) — a draft, not an answer. It
  can reach past the flagged span or miss the tense. Read it, then write the
  line yourself. **Never paste one unread.**
- No fix shown (**advisory**) — the tool has no span-level answer. Your
  judgment decides, or you leave it.

In `--format=json` these are the `suggestion` and `applicability` fields on each
diagnostic, which is the easier form to work through in bulk.

A replace tier still doesn't override meaning. `NB303` on "probably" is a clean
deletion mechanically, and still the wrong edit if the hedge is the author being
honest. The tier answers "is this edit safe to type", never "is this edit right".

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

**Human signals — the inverse checklist.** The shapes on the list above are not
banned. A piece can use the not-X-but-Y shape and a punchline ending and still
read human, and one well-known post does exactly that. What carries it is that
every shape stands on a checkable fact: the number has a source, a named person
is quoted, the launch has a partner and a date. Grounding pays for rhetoric. The
same shapes over abstractions read machine-made.

Treat that as a working rule, not a measured one — it rests on reading, not on a
study. What *is* measured is the narrower point that word-level change is not
where the signal lives (`docs/detection-research.md`). Both push the same way: when
you rewrite, add one real detail from the author's material before another round
of tell-removal. Ask for it first — never invent it.

**The cadence pass.** Do this once, on the whole piece, after the bullet list
above. It is the layer trained detectors key on, and no static rule reaches
it: nabokov sees words and measurable rhythm, not *beat*. Read for five
patterns. One of each is craft. A run of them is machine cadence.

1. **Beat-perfect rhetoric** — anaphora runs ("The X… The Y… The Z…"),
   fragment couplets as punchlines, balanced two-clause aphorisms, every
   paragraph landing on a short beat.
2. **Metronome punctuation** — a comma or dash every clause, all clauses the
   same weight. Human prose both under- and over-punctuates. Look for one
   long unpunctuated run and one two-word aside. If neither exists, that is
   the finding.
3. **Model idiolect** — smooth stock phrasing sitting where the author's own
   slightly off-balance wording would. This is what minimal paraphrase
   protects.
4. **Ungrounded rhetoric** — a flourish with no checkable fact under it.
5. **Register uniformity** — every line sits at the same polish level, with
   nothing thrown away: no aside, and no sentence left loose or ending flat.

Discipline for this pass: quote the span verbatim, name the pattern, and say
how to break it. **An empty list is a valid answer** — judge the piece for
what it is, and do not manufacture findings. Never suggest injected errors,
typos, or fake informality to break a pattern; that is fabrication, not
cadence. Calibrate to the whole piece, not to its worst sentence.

**Who rewrites matters, and this is measured.** In Beemo (NAACL 2025),
LLM-edited machine text stays detectable — Binoculars reads 79.90 AUROC on
LLM-edited and 78.15 on GPT-4o-edited text, against 61.24 on human-edited.
A model polishing a model's draft leaves the machine signal in place. So for
findings 1, 2 and 5 — the ones that need new sentences rather than a cut —
prefer handing the author the diagnosis over rewriting it yourself. Your
rewrite of a machine cadence is another machine cadence. Say which lines
need their hand.

**Detector feedback.** Detectors come in two families. Statistical ones
measure rhythm and word predictability. Trained classifiers (Pangram, Turnitin)
learned what whole human documents look like.

**There is no single number to chase, and this is the part people get wrong.**
The same edit moves the two families in opposite directions. Measured on one
benchmark, a synonym swap cost one statistical detector 36 points, cost another
detector 5, and *improved* two others (`docs/detection-research.md`). So "make a
change, watch the score fall" is not a workflow. A number that went down may mean
nothing.

Against trained classifiers, word swaps are close to useless: a synonym swap
costs the best one about 3 points, an automated paraphrase about 8. Commercial
"humanizer" rewriting barely moves it either. Either way, swapping words is not
the fix. It does nothing, or it moves a number without touching the writing.

So when a detector flags a sentence, treat it as one of the cadence or pointer
findings above. Ground it or loosen it; never just swap synonyms. Fix only what
the fix improves, and say where you think the detector is wrong.

**What `--score` is for.** It compares a draft against *your own earlier draft*.
It is not a detector proxy and cannot be one: its inputs are burstiness, punctuation
rhythm and diversity, which are the statistical family's features — the ones that
move unreliably. A text scoring 12 has been observed reading 100% AI to a trained
classifier. Use it to catch polish drift, never as evidence a piece will pass.

After rewriting, check the new sentences against this same list. Rewrites drift
into sibling shapes: a cut not-X-but-Y comes back as "what X does is Y", and a
punchline ending comes back as an "-ing" closer. When a detector still flags text
that lints clean, the register is the tell — impersonal, every clause balanced, no
lived detail. Two things move that. One: the author's own details or first person,
asked for and never invented. Two: uneven syntax — `--score`'s punct-rhythm number
tracks one form of it, so keep the author's long unpunctuated runs instead of
comma-splitting them.

Score the whole piece, not an excerpt, because a short passage carries less signal
either way. Cap the loop at **two** rewrite → re-scan rounds. On the second round
touch only the sentences still flagged — a clean sentence rewritten again can only
drift. If flags survive round two, stop and report what remains and why; a third
pass moves the meaning more than the score.

Essays, opinion pieces, and academic texts also get a structural macro pass.
It covers the thesis, a reverse outline, stitching, cohesion, and the
conclusion. Read
[references/macro-pass.md](references/macro-pass.md) for it. Skip it for
READMEs and reference docs.

**Voice profiles.** When a rewrite is unavoidable, nabokov can keep it inside
the author's own distribution. `uvx nabokov --profile-card list` names the
bundled author profiles; `--style <name-or-json>` adds NB7xx drift findings
(foreign connectors, flat rhythm, punctuation off the author's rate) to any
lint run. Prefer a personal profile built from the author's other texts
(`--build-profile out.json their-posts/`); otherwise suggest the closest
bundled one by genre and confirm before using it. Read the voice card first.
Pull rewritten lines toward its connectors, rhythm, and punctuation. The
author's surviving words still beat any rewrite a profile guides, and a
profile never supplies facts.

## Workflow

1. **Static pass**: `nabokov --format=flake8 <file>`. Add `--ai` when the
   goal is de-slopping or humanizing — it usually is when this skill runs.
   Skip it when the user asked for a plain readability lint. On anything
   longer than a few paragraphs add `--hotspots`: it ranks the paragraphs
   with the most findings per word, so you start where the trouble is instead
   of walking the file top to bottom. A paragraph that tops the list with
   findings across many codes is usually a rebuild, not a set of small fixes.
2. **Judgment pass** (+ macro pass for essays). Read the whole piece, not only
   the hotspots — a topic jump leaves no finding behind, and the flattest
   writing in a draft is often the part that lints clean. Finish with the
   **cadence pass** (above) when the goal is de-slopping or humanizing. Run it
   once, on the whole document: a short excerpt has no beat to read.
3. **Fix, keeping the meaning** — playbooks below. Keep the author's intent,
   facts, links, code, structure. Never invent content. **Minimal
   paraphrase:** a line that nothing flagged — linter, detector, judgment
   pass — keeps its original wording, word for word. Every needless
   paraphrase trades author idiolect for model idiolect. That swap is the
   exact pattern trained detectors hunt for. The author's surviving words are
   the one human signal a rewrite cannot fake. **Patch or rebuild?**
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
   - *Denser* — `--stats` also prints a `register:` line: `nominal` (share of
     content words that are nouns), `pronouns` per 100 words, and the temporal
     share of connectives. Compare the two runs, never the absolute value —
     these have no thresholds and no rules behind them, and technical prose is
     legitimately noun-heavy. What matters is the direction. If `nominal` rose
     and `pronouns` fell, you turned verbs into noun phrases and started
     re-naming things instead of referring to them. That is how a rewrite reads
     stiffer while every finding goes away.
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
   approval*. If you ran `--hotspots`, run it again and say whether the worst
   paragraph moved off the top — that is the clearest evidence the edit landed
   where it mattered.

## Fix playbook — static

Findings not listed here carry their fix in the `suggestion` field (NB304 names the verb,
NB401 the simpler phrase). The rows below are the ones where the fix needs a
judgment the field cannot hold.

| Code | Fix |
|------|-----|
| NB201/NB202 | Split into shorter sentences. Long sentences are half of burstiness, so never split them all. Vary the new openers (a time phrase, an object, a clause) so splits don't create "We did X. We did Y." chains. |
| NB301/NB302/NB303/NB510 | Act only at warning level. Thin, don't remove all. Fold weak adverbs into stronger verbs. Rewrite the weakest passives; passive that keeps the known topic in front is fine. Keep hedges that do work. |
| NB305 | Name the real subject. Keep "there is no X" when existence itself is the point. |
| NB308 | "Simply", "obviously" — cut the word. But "Installation is easy" is not fixed by cutting "easy": say what the task takes, or drop the claim. Ask for the step count or the timing; don't guess it. |
| NB309 | An acronym nothing expands. Two honest fixes: expand it on first use, or add it to `known_acronyms` in the project config when the audience knows it. **Never guess the expansion** — a wrong one is worse than none. Ask the user. |
| NB310 | "The diagram above" has an exact fix; apply it. "See above" does not — replace it with a real cross-reference that names the section. If you can't tell which section, ask. |
| NB311 | An image with no alt text. **Never invent alt text.** You cannot see the image. Ask the user what it shows, or leave it and report it. If the image is decorative, empty alt is already correct. |
| NB312 | Vague link text. The message names the target URL — use it to write text that says where the link goes. Read the target if it's a local file. Don't relabel every link "the docs". |
| NB314 | A step naming the reader. The draft is usually right, but check what the subject took with it: "you will *then* restart" loses "then", which may have been doing work. |
| NB315 | Off unless `--terminology` is passed, so you will not normally see it. Where a term has two replacements ("denylist, blocklist"), pick the one that fits the sentence. |
| NB316 | A claim attributed to nobody ("studies show", "experts agree"). Three honest fixes. Ask the author for the source and name it. Or drop the borrowed authority and let the claim stand in their own voice: "Studies show caching helps" → "Caching helps". Or cut the claim. **Never invent a citation** — see the guardrail below. The second fix is usually right and needs no new facts, because the sentence was never leaning on a real source. On an essay the rule stays quiet (`--target essay`): naming a view in order to refute it is the form working as intended. |
| NB801 | The README never says what the project is. **Never invent it.** Ask the user for one sentence: what it is, who it's for. |
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
- **Never invent** facts, examples, or numbers to satisfy a check. Five rules ask
  for something only the author knows. NB601 wants a concrete detail. NB309 wants
  an acronym's expansion, NB311 what an image shows, NB801 what the project is,
  and NB316 the source behind "studies show". All five are questions for the
  user, never gaps for you to fill. A plausible invention is the worst outcome
  here — it is wrong and it looks right. **NB316 is the most dangerous of the
  five**: a fabricated citation is the one invention that makes the text look
  *more* rigorous, so it survives review. Never supply an author, a year, a
  percentage, or a study title. Ask, or cut the claim.
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
