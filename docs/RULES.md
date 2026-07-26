# nabokov rules

Every check nabokov can emit, with its code, what it flags, and an example. Codes work
like flake8: enable/disable by exact code or prefix with `--select` / `--ignore` /
`--extend-select` / `--extend-ignore`, in `[tool.nabokov]` config, or inline with
`nabokov: ignore NBxxx`.

- **Default run** (`nabokov file`) enables the core checks: `NB201 NB202 NB203 NB301 NB302 NB303 NB304 NB305 NB306 NB307 NB401 NB601`.
- **`NB101`** (readability grade) is emitted only with `--max-grade N`.
- **`NB5xx`** (signs of AI writing) is **off by default**: enable with `--select NB5`
  (AI checks only) or `--extend-select NB5` (alongside the core checks).

Run `nabokov --list-rules` to print this catalog from the tool itself.

---

## Fix suggestions

Many findings carry a fix as well as a diagnosis. Because a fix is only worth as
much as a reader's willingness to trust it, every suggestion is tagged with how
mechanically it applies:

| Tier | Meaning | Shown as |
|------|---------|----------|
| `replace` | Substitutes for the flagged span verbatim. An empty suggestion means *delete the span*; where several alternatives are listed, the first is the default. | `→ to` |
| `rewrite` | A drafted direction. It may reach outside the flagged span, or need tense and number agreement the parse cannot settle. Read it, don't paste it. | `try: the team wrote the report` |
| `advisory` | No span-level fix exists. The message carries the direction and the suggestion is empty. | *(nothing)* |

Severity says how much a finding matters; applicability says what you are allowed
to *do* about it. They are independent — an `info` finding can be a clean
`replace`, and a `warning` can be `advisory`.

The line between `replace` and `rewrite` is position, not the dictionary. The same
entry lands in different tiers depending on where it sits:

- `Moreover, the team shipped it.` — cutting `Moreover` strands the comma and
  takes the capital with it, so this is a `rewrite`.
- `The build was moreover green.` — cutting mid-sentence is mechanical: `replace`.
- `Despite the fact that sales fell…` → `Although` — a substitution, so only the
  capital needs matching, and it stays `replace`.

The same care governs the data:

- `NB303` never offers to delete a negated hedge. Cutting "I don't think" out of
  "I don't think we should ship" does not soften the claim, it flips it. Those
  entries carry written guidance instead.
- `NB502` offers a substitution only for a base-form match (`delve` →
  `examine`). The alternatives are stored uninflected, so `delved` drops to
  `rewrite`.
- `NB302` drafts the active voice under three conditions: the parse names the
  actor, the auxiliary is past tense, and the subject is not a relative
  pronoun. Otherwise it reports the passive and stops.

In `--format json` both fields ride on every diagnostic as `suggestion` and
`applicability`. The flake8 format appends the fix to the message so editors keep
one finding per line; the color and GitHub formats give it its own line.

---

## Hotspots

`--hotspots` ranks the paragraphs carrying the most trouble *per word* and prints
them after the findings. The report says what is wrong and `--score` says how bad
the whole document is; this says where to start.

```sh
nabokov --ai --hotspots draft.md
```

```
Hotspots (draft.md) — worst paragraphs first:
  1. line 5-7: 17 findings in 34 words (density 88.2)
       NB502×11 NB201 NB302 NB401 NB505 NB510 NB520
       Moreover, the platform leverages a robust tapestry of very…
```

It adds no new signal: the inputs are the findings the rules already produced,
weighted by severity (error 4, warning 2, info 1). Ranking is by density, not
count — a long paragraph collects more findings just by being long. The divisor
has a 25-word floor so a two-word heading with one finding cannot out-rank a
dense paragraph. Set `hotspots = N` in the config to see more than the default
three; the JSON format carries them under a `hotspots` key.

---

## Readability (NB1–NB2)

Readability uses the Automated Readability Index (ARI):
`grade = round(letters/words × 4.71 + words/sentences × 0.5 − 21.43)`. Thresholds come
from the reading-level target (`--target`):

- `NORMAL` (default)
- `ACCESSIBLE`
- `TECHNICAL`
- `ESSAY` — voice-friendly: tolerates the longer sentences literary prose sustains
  deliberately, and carries the loosest style budgets (see *Style budgets*)
- `SOCIAL` — short-form posts: plain-language thresholds. The genre's own devices
  (staccato fragments, repeated openers, flat-rhythm and periodic-sentence checks)
  are switched off, since they are the register there, not tells
- `EMAIL` — business email: a high-trust audience, so the tightest style budgets of
  any target

| Code | Name | Color | Flags |
|------|------|-------|-------|
| `NB101` | readability | red | The whole-document grade. Emitted as a finding only when it exceeds `--max-grade`. |
| `NB201` | very-hard-sentence | red | A sentence whose reading level is very high (NORMAL: grade ≥ 14, ≥ 14 words). |
| `NB202` | hard-sentence | yellow | A sentence whose reading level is high (NORMAL: grade 10–13, ≥ 14 words). |
| `NB203` | periodic-sentence | yellow | Advisory (info): the main clause lands only after 20+ words of build-up — a periodic pile-up. Tells the editor *where* a hard sentence can be split; periodicity as deliberate suspense is the author's call. |

Sentence boundaries: a blank line always ends a sentence. In *line-oriented*
documents (one thought per line — almost every non-blank line ends in terminal
punctuation) every newline does too. So an unpunctuated heading or title never
glues into the paragraph below it. Hard-wrapped prose is unaffected.

Sentences shorter than the target's minimum word count are never flagged. Both
sentence findings are warnings: a long sentence in a readable document is rhythm,
not failure; the hard document-level gate is `NB101` via `--max-grade`. When the
whole document reads fine for its target, `NB202` drops further to `info`: a
grade-11 sentence in a grade-8 document is the long half of burstiness, so only the
extreme `NB201` sentences stay warnings there.

```
report.md:12:1: NB201 very hard to read (grade 17)
```

## Word & phrase checks (NB3–NB4)

| Code | Name | Color | Flags | Example |
|------|------|-------|-------|---------|
| `NB301` | adverb | blue | An `-ly` adverb spaCy confirms (POS = ADV), minus the exception list. | "He ran **quickly**." |
| `NB302` | passive-voice | green | A passive construction, via spaCy dependency parse (`auxpass`), incl. the "by …" agent. Drafts the active voice (`rewrite`) when the agent is named and the auxiliary is past tense. | "The report **was written by the team**." |
| `NB303` | qualifier | blue | A weakening/hedging phrase from the qualifier list. Suggests the cut where it is grammatical; the negated hedges get guidance instead, since deleting one inverts the claim. "just" is only flagged in hedge positions ("it's **just** a way to…") — restrictive "just one", the imperative opener "Just tell me…", and temporal "I'd just read" are precision devices and skipped. | "**I think** we should wait." |
| `NB304` | nominalization | blue | The action hidden in a noun behind a light verb (dependency-matched, so articles/adjectives/inflection don't matter; the noun alone is never flagged). Suggests the verb (`rewrite` — it has to pick up the light verb's tense). | "**came to an agreement**" → agreed |
| `NB305` | dummy-subject | blue | An expletive subject burying the real one (spaCy `expl`). Locative "there" is untouched. | "**There are** many resorts in Colorado." → "Colorado has…" |
| `NB306` | repeated-word | blue | (`replace`) The same word twice in a row — the lexical illusion that hides on a line wrap. Grammatical doubles ("had had", "that that"), proper-noun pairs ("Pago Pago"), and emphasis runs of 3+ ("no no no") are skipped. | "Paris in **the the** spring" |
| `NB307` | uncomparable | blue | (`replace`) A degree word on an absolute adjective — the quality either holds or it doesn't. Approximators stay legal ("almost impossible"), and soft absolutes (essential, universal, ideal, ultimate, absolute) accept comparison — "the most essential feature" is ordinary prose; only intensifiers fire on them ("really essential"). | "**very unique**", "**most perfect**" |
| `NB308` | condescending | blue | A word claiming the task takes no effort — the ease adverbs (`simply`, `easily`, `merely`) on an instruction, the presupposition adverbs (`obviously`, `clearly`) opening a sentence, `easy`/`trivial`/`simple` predicated of the task, and the shared-knowledge phrases (`of course`, `as you know`). Guarded hard: the descriptive senses never fire — "the function **simply** returns null", "a **simple** object", "**Simply put**, …". Outranks NB301/NB510 on the same word. Off for ESSAY and SOCIAL. | "**Simply** run the migration.", "Installation is **easy**." |
| `NB309` | undefined-acronym | blue | An acronym no part of the document expands (advisory). A gloss counts in any of three forms and anywhere in the file, including a glossary below first use: `Fully Qualified Domain Name (FQDN)`, `MATTR (moving-average type-token ratio)`, `**PAS** — Problem, Agitate, Solution`. Exempt: the ~120-entry allowlist in `data/acronyms.json`, all-caps words that are ordinary English (`SOCIAL`, `GET` — config values and HTTP methods, checked against the concreteness dictionary), anything the file also writes in lower case, and single letters. Reported once per acronym. Extend with `known_acronyms` in config. Off for SOCIAL. | "Configure the **FQDN** in the settings." |
| `NB310` | directional-language | blue | Orienting the reader by position (advisory): a document element followed by a bare `above`/`below` ("the diagram above", "check the table below"), or a bare reference idiom ("see above", "as shown below"). Position does not survive reflow, pagination, screen readers, or the next editor reordering the page. A real preposition with a real object is untouched — "above 50 percent", "above the intake manifold" — and so is a non-document noun ("the shelf above"). Left and right are deliberately absent: "the right-hand side" usually describes a UI, where position is the content. Off for SOCIAL. | "In the **diagram above**, clients run jobs." → "In the preceding diagram…" |
| `NB311` | image-no-alt | blue | An image whose alt text is empty or missing (advisory), in Markdown `![](x.png)` or a raw `<img>` tag, in `.md` and `.html` alike. Images inside a code fence are showing the syntax, not using it, and never fire. Precision is capped by the standard: Google says to mark a *decorative* image with empty alt text, so an empty alt is either that or an oversight and the source cannot say which — hence info, and a message that names the case. | `![](chart.png)` |
| `NB312` | vague-link-text | blue | A link whose visible text could point anywhere — `click here`, `here`, `this`, `read more`, `learn more`. Screen readers can list a page's links stripped of their sentences, and a list of identical "here" entries points nowhere (WCAG 2.4.4, Level A). Matching is on the *whole* link text, so "Read the installation guide" is fine, and it reads the `link-text` span rather than the prose — the same words in a sentence about a button are untouched. The message names the target so the writer need not go and look. | "For the options, [**click here**](/config)." |
| `NB313` | heading-punctuation | blue | A heading ending in `.`, `,`, `;` or `:` — a heading is a label, not a sentence (advisory). Question marks and ellipses stay legal, and only *trailing* punctuation counts, so "Step 1: Install" is untouched. Setext headings (underlined with `===`) are not indexed as headings and so are invisible here. Prior art: `HeadingPunctuation` in both Vale styles. | "## Requirements**:**" |
| `NB314` | non-imperative-step | blue | A list step whose subject is the reader — "1. **You should** click Save", "1. **The user** clicks Save" — where the imperative says it shorter and in the mood Google and Diátaxis both ask instructions to use (advisory). The subject must *open* the item: a reader pronoun deeper in the sentence belongs to a subordinate clause ("add detail you don't have") and is ordinary writing. Restricted to list items, since outside one the second person is Google's own recommended phrasing. Fact lists are untouched — they have no subject, or the software is the subject. Off for ESSAY and SOCIAL. | "1. **You should** click Save." → "Click Save" |
| `NB316` | nameless-authority | blue | A claim whose source is never named — "**Studies show** that adoption grew", "**Experts agree**", "**It is widely believed that** scale matters", "**Many argue** that…", "**Conventional wisdom holds** that…". The reader cannot check it and the writer cannot be wrong. Prior art: WP:WEASEL, both Vale styles, proselint. The guard is the **determiner**: a bare generic subject points outside the document at nobody, while a definite or possessive one refers — "**studies** show" fires, "**the** study shows" and "**our** research shows" do not, and an adjective is not a reference ("**recent studies** show" still fires). A paragraph containing a link, URL, or citation is skipped entirely. Warning for the research and expert families, info for the vague crowd ("some say" is common rhetorical setup). Always `rewrite`: only the author knows which source they meant. Off for ESSAY — naming a view to argue against it is the essay's basic move. | "**Studies show** adoption grew." → name the study |
| `NB401` | complex-phrase | magenta | A wordy phrase with a simpler alternative (`replace`, capitalization matched to the span). | "**in order to**" → "to" |

```
report.md:3:8: NB302 passive voice: 'was written by the team'
report.md:3:40: NB401 wordy: 'utilize' → use
```

### Style budgets — severity by density

An adverb, qualifier, passive, or wordy phrase is a style *signal*, not a defect.
The defect is overuse. `NB301`/`NB302`/`NB303`/`NB401` findings are therefore
advisory (`info`) while the document stays inside its per-1000-word budget, and
escalate to `warning` only when the text overuses the pattern. Short texts get a
flat grace of 2 occurrences.

Default budgets per 1000 words, by target:

| Target | NB301 adverbs | NB302 passive | NB303 qualifiers | NB304 nominalizations | NB305 dummy subjects | NB401 wordy |
|--------|---------------|---------------|------------------|-----------------------|----------------------|-------------|
| ACCESSIBLE | 10 | 5 | 8 | 2 | 2 | 2 |
| NORMAL | 15 | 8 | 10 | 2 | 5 | 3 |
| TECHNICAL | 10 | 15 | 8 | 3 | 4 | 3 |
| ESSAY | 25 | 15 | 15 | 3 | 6 | 6 |
| SOCIAL | 15 | 5 | 10 | 2 | 4 | 3 |
| EMAIL | 10 | 5 | 8 | 2 | 3 | 2 |

ESSAY is calibrated against a corpus of Paul Graham essays: strong essayistic prose
produces no style-layer warnings there. Override any budget in config:

```toml
[tool.nabokov.budgets]
NB301 = 20   # per 1000 words
```

Two more calibration choices keep the layer honest. An `NB301` finding is dropped
when `NB303`/`NB510` already flags the same words ("probably" is a hedge, not a
manner adverb; one finding per span). And the `NB301` message only says "consider
a stronger verb" when the adverb actually modifies a verb; elsewhere it says
"consider cutting it".

### Quoted material

Quotes are evidence, not the author's prose, so findings that fall entirely inside
quoted material are dropped. A quoted region is a Markdown blockquote (`>` lines) or
a quoted span of at least 2 words: straight or curly double quotes, or curly single
quotes (that pair is apostrophe-safe). A multi-word quoted phrase is a mention,
dialogue, or citation — "phrases like ‘objective considerations of contemporary
phenomena’" is exhibiting the phrase, not using it. A single quoted word keeps the
findings *around* it (an inch mark must not swallow its neighborhood), but when the
quote holds exactly the flagged term — 'the word "delve"' — that is a pure mention
and the finding drops. A hard-sentence finding (`NB201`/`NB202`) whose span is *mostly* quotation
(an author's short sentence framing a long citation) is demoted to info: the
grade belongs to the quoted prose, not the author's. (Plain-text files that lost
their quote markers and italics, e.g. a blog post saved as `.txt`, can't be fully
protected; keep the markup when you can.)

## Signs of AI writing (NB5) — opt-in

Tells drawn from the [Wikipedia "Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
reference plus community lists (Reddit / OpenAI forum threads). These are **tells, not
proof** — enable them deliberately.

**Tells migrate.** Each model generation retires last season's vocabulary and grows
new structural habits, so a frozen list gradually scans for patterns no current model
produces. The signal lists carry an `_updated` date in `ai_writing.json`; refresh them
against the detection literature (and re-run the corpus calibration) every release
or two.

Each row has a **severity**: `warning` = a confident tell to fix; `info` = an advisory
"hard part" static isn't sure about (the [nabokov-editor skill](../skills/nabokov-editor/SKILL.md)
leaves those for the LLM to decide). Severity shows in the `json` reporter.

The table states what each rule flags. The full exemption logic and the corpus
calibration behind each threshold live in the rule docstrings in
[`src/nabokov/checks/ai_writing.py`](../src/nabokov/checks/ai_writing.py).

| Code | Name | Sev | Flags | Example |
|------|------|-----|-------|---------|
| `NB501` | ai-negation-contrast | warning / info | "it's not X, it's Y" / "not only X but Y" / "No X, no Y, just Z" (warning). Advisory reframes: "no longer" / "doesn't mean" / "more than just" / negation → role reveal / the appearance-verdict couplet. Bare negations, first person, questions, and spoken replies are exempt. | "This **isn't just fast, it's** transformative."; "**This feels pointless. It is not.**" |
| `NB502` | ai-puffery | warning | Buzzword vocabulary (lemma-matched), with a plain-word alternative (`replace` on a base-form match, `rewrite` when inflected). A repeated lemma is topic vocabulary and drops to info; literal senses ("test harness") are exempt. | delve, tapestry, embark, synergy … |
| `NB503` | ai-editorializing | info | Promotional / "importance" / vague-attribution phrases. | "**plays a crucial role**", "**experts argue**" |
| `NB504` | ai-filler | warning | Chatbot filler, sycophancy, signposting. Reported speech ("asked **a** great question") is exempt. | "**Great question!**", "**let's dive in**" |
| `NB505` | ai-transition | info | Overused formal transitions — human formal prose uses them too, so advisory. | "**Moreover**", "**In conclusion**" |
| `NB506` | ai-em-dash | warning | Em-dash *density* above the human range (> 12 per 1000 words). Counts `—`, spaced `–`, and the spaced hyphen; list bullets don't count. One finding per document. | "It was fast — clean — simple — done." |
| `NB507` | ai-rule-of-three | info | 3+ consecutive short *verbless* fragments on one line. Fragments with a verb are human staccato and exempt. | "The jokes. The wins. The team." |
| `NB508` | ai-emoji | warning | Emoji as formatting (≥ 3 in the document). One finding per document. | "✅ fast ✅ safe 🚀 shipped" |
| `NB509` | ai-monotonous-rhythm | info / warning | Flat sentence rhythm (low burstiness). Per-target threshold; robotic flatness escalates to warning. The finding anchors at the flattest run of near-equal sentences. See the CV with `--stats`. | uniform mid-length sentences throughout |
| `NB510` | ai-intensifier | info | Weak intensifiers / weasel words; suggests the cut where it is grammatical. Emphatic "very" ("the very first time") and idioms ("quite a few") are exempt. | "**very**", "**really**", "**basically**" |
| `NB511` | ai-participial-closer | info | Empty present-participle "significance" closer. | "…, **highlighting its importance**." |
| `NB512` | ai-repeated-opener | info | 3+ sentences in a row opening with the same word. | "It … It … It …" |
| `NB513` | ai-curly-quote | info | Curly quotes in the *minority* against straight quotes — a pasted-in snippet. All-curly typography is exempt. | straight text with a stray “curly” pair |
| `NB514` | ai-title-case-heading | info | Title Case headings (a capitalized function word gives it away). | "## Getting Started **With** Django" |
| `NB515` | ai-predicate-hyphen | info | A hyphenated compound used predicatively should drop the hyphen (`replace`). | "the team is **cross-functional**" |
| `NB516` | ai-bold-listicle | info | A stack (≥ 3) of `**Label:**` bold-header bullets, or a bold label ended with a period. One finding per stack. | "- **First:** … - **Second:** …" |
| `NB517` | ai-vocab-cluster | info | Generic-praise words that are normal alone but cluster: 2+ *distinct* list words in one paragraph. | "our **significant** and **innovative** platform" |
| `NB518` | ai-adjective-triad | info | Balanced adjective triples at 1.5+/1000 words (min 2) — the tricolon is legitimate rhetoric, so only the density is the tell. A copula-colon launch ("…is: X, Y, and Z") fires alone. | "**innovative, transformative, and groundbreaking**" |
| `NB519` | ai-artifact | warning | Fingerprints: chat citation tokens, AI-tool URL parameters, unfilled placeholders, knowledge-cutoff disclaimers, invisible characters (zero-width space/joiners, mid-text BOM), and mixed-script homoglyph swaps ("dеtection" with a Cyrillic е). Ordinary multilingual text is exempt: the non-breaking space (NBSP), whole-script words, and Cyrillic suffixes on Latin brands don't fire. No density gating. | "**citeturn0search0**", "**[Your Name]**" |
| `NB520` | ai-hedge-stack | warning | A modal stacked with a hedge adverb — the two hedges cancel out; keep one (`replace`, collapsing to the modal). | "**could potentially** create" |
| `NB521` | ai-paragraph-opener | warning | The same coordinating conjunction opening 3+ paragraphs (and ≥ 10% of them). | "**And** … ¶ **And** … ¶ **And** …" |
| `NB522` | ai-engagement-bait | info | A closing second-person superlative question — reply bait. Flags *bait*, not AI: humans growth-hack too. | "**What's the most unexpected place you've found genuine customer insight?**" |
| `NB523` | ai-anaphora-triad | info | The same quantifier (more/every/each…) opening three coordinated phrases. A pair or a varied list is exempt. | "**more code reviews, more reports, and more style guides**" |
| `NB524` | ai-contrast-heading | info / warning | The "X, not Y" heading. One is advisory (human titles use it); 2+ in a document escalate to warning. Running text is `NB501`'s territory. | "## **Pin decisions, not knowledge**" |
| `NB525` | ai-hook-question | info | A verbless 2–4-word question answered by the next sentence. Real questions ("Why? Because…") and fragments with a verb are exempt. | "**The best part? It's free.**" |
| `NB526` | ai-false-range | info | "from X to Y" where the endpoints aren't on any scale (both abstract per the concreteness norms). Proper nouns, numbers, concrete pairs, and motion-verb transfers are exempt. | "everything **from strategy to execution**" |
| `NB527` | ai-uniform-paragraphs | info | Every paragraph the same number of sentences (CV < 0.35 over ≥ 6 prose paragraphs). All-one-sentence documents are exempt. One finding per document. | eight paragraphs, three sentences each |
| `NB528` | ai-low-lexical-diversity | info / warning | Narrow, repetitive vocabulary: moving-average TTR (window 100) below 0.55 on ≥ 120 words; below 0.45 escalates to warning. Names the most-repeated content words. See the value with `--stats` (`diversity`). One finding per document. | the same nouns and verbs cycling through every sentence |
| `NB529` | ai-punchline-endings | info | Most paragraphs close on a short beat (≥ 3 closers of ≤ 8 words, ≥ half of ≥ 6 prose paragraphs averaging ≥ 2 sentences). Two or three punchline endings are craft; every paragraph landing is cadence. One finding per document. | every paragraph ending "**It worked.**" |
| `NB530` | ai-fragment-density | info | Verbless label fragments (noun-rooted, with terminal punctuation — headings and list items are exempt) at ≥ 3 and > 12% of ≥ 8 sentences. Any one fragment is a beat and the writer's call; the density is the tell. One finding per document. | "**Three contexts. One question. A single answer.**" |
| `NB531` | ai-bolted-connector | info | A paragraph opens with a bolted-on associative connector ("That reminded me of…", "Recently, I was listening to…", "It made me wonder…") — a transition that announces the link instead of building it. A single hop is fine; a piece built on them reads as beads glued by "this reminded me". Bridge with an echo of the prior point. One finding per offending paragraph. | "**Recently, I was listening to a podcast.** The conversation began with desire." |
| `NB532` | ai-asserted-unity | info | The writer concedes the parts *seem* separate, then asserts they are one ("These may sound like different conversations, but they are all about the same thing") — the coherence gap papered over with a claim of unity instead of a shown connection. Name the shared idea and let the reader feel it. One finding per occurrence. | "These may sound different. **But they are all about the same thing.**" |

```
essay.md:3:1: NB502 AI tell: puffery 'delve'
essay.md:7:1: NB509 AI tell: monotonous sentence rhythm (burstiness 0.28, aim for >= 0.40)
```

Enable them with the shorthand flag:

```bash
nabokov --ai draft.md        # core checks + AI-writing checks
nabokov --ai-only essay.md   # only the AI-writing checks
```

(`--ai` = `--extend-select NB5`, `--ai-only` = `--select NB5`.) Or make it the default:

```toml
[tool.nabokov]
extend_select = ["NB5"]
```

### `--score` — one number for before/after edits

`nabokov --score draft.md` prints a composite **AI-likeness estimate (0–100,
higher = more AI-like)** per file, built from five calibrated signals:
sentence burstiness (25), punctuation rhythm (10 — segment-length CV; LLM
prose punctuates on a metronome, human prose mixes long unpunctuated runs
with short asides), NB5 tell density per 100 words (40), NB519/NB513
artifacts (cap 15), and vocabulary diversity (10). Bands: <25 reads human, <50 leans
human, <75 leans AI, 75+ reads AI. Run it before and after an edit to show
movement. It is a gauge of the measurable statistical signals only — **not a
detector verdict**: a low score does not mean a trained classifier will read
the text as human. Texts under 25 words or 3 sentences are not scored.
(Adapted from lakshitha-dev/ai-humanizer-skill's estimator, MIT; rebuilt on
nabokov's own signals.)

### Register metrics — reported, never scored

`--stats` prints a second line per file with three numbers that no rule reads and
nothing scores:

```
  draft.md: grade=8 level=normal words=4775 ... burstiness=0.74 diversity=0.73
    register: nominal=0.57 pronouns=3.9/100w temporal_connectives=0.18
```

- **nominal** — nouns as a share of content words. High means meaning is packed
  into noun phrases rather than verbs, which reads dense and flat. The lexical
  version of this is `NB304`; this is the overall balance.
- **pronouns** — pronouns per 100 words, a rough stand-in for how often the text
  refers back instead of re-naming. Rough on purpose: real anaphora needs
  coreference, which the small spaCy model has not got.
- **temporal_connectives** — temporal connectives as a share of temporal plus
  additive ones. High means the text sequences ("then", "next", "finally"); low
  means it relates ideas ("however", "because", "instead"). The weakest of the
  three: "and", "but", "so" and "or" dominate the additive side by frequency, so
  real documents cluster narrowly — every sample in this repo, technical docs and
  essays alike, lands between 0.14 and 0.20.

They separate genre cleanly — technical docs in this repo measure nominal
0.57–0.58 with ~4 pronouns per 100 words, Paul Graham's essays 0.34 and 13.7 —
which makes them useful for comparing two drafts of the same text and useless as
absolute targets.

**Why they are not rules.** They come from a 2025 synthesis on AI prose that
gives directions without thresholds ("AI text is noun-heavier", "AI under-uses
anaphoric reference"), and the one effect size it quotes is an ARI difference of
19 vs 18 — inside the noise of the grade nabokov already computes. A direction
with no threshold is worth showing a writer and not worth a finding. Wiring any
of them into `--score` or a rule needs a calibrated threshold first;
`tests/test_register_metrics.py::test_no_rule_and_no_score_reads_them` is there
to stop it happening by accident.

## Inclusive terminology (NB3) — opt-in

| Code | Name | Flags |
|------|------|-------|
| `NB315` | exclusionary-term | An exclusionary term with a settled replacement: `whitelist` → `allowlist`, `blacklist` → `denylist`/`blocklist`, `master/slave` → `primary/replica`, `sanity check`, `dummy value`, `grandfathered`, `man hours`. `REPLACE` tier — single tokens, same part of speech, no reordering — with inflected forms listed rather than stemmed, since a substitution that guesses at morphology is not one. |

Off by default; enable with `--terminology` (or `--extend-select NB315`). Every
other rule here points at something that makes prose harder to read. This one
points at a choice a project makes about its own language, so it waits to be
asked.

An entry earns its place by having an **agreed** replacement, not by someone
having objected to the word. `crazy`, `insane` and `blind spot` were drafted into
`data/terminology.json` and removed: no settled alternative, and entries like them
are what get a whole rule switched off. `master` alone is absent for the same
reason — a master's degree, a master copy, mastering an API, a branch name
hard-coded in a million scripts. Only the slave-paired sense is unambiguous.

Source: [IETF draft-knodel-terminology](https://datatracker.ietf.org/doc/draft-knodel-terminology/06/).

## README structure (NB8)

| Code | Name | Flags |
|------|------|-------|
| `NB801` | readme-no-description | A README whose opening region — up to the third heading — holds no sentence of prose saying what the project is. Badge rows, code fences and images are already blanked, and heading text is masked out, because a title is a label: "# nabokov" does not describe nabokov. Only files actually named `README.*` are judged. |

This is the **only** README-structure rule the evidence supports. Prana et al.
hand-annotated 4,226 sections across 393 randomly sampled repositories: 97.0% of
READMEs contain a section describing the *what* of the project, so demanding one
fires on about three repositories in a hundred.

The same table is why the obvious siblings do not exist. Contribution appears in
27.8% of READMEs, Why in 25.7%, When in 21.4% — a "missing Contributing section"
check would fire on 72% of real-world READMEs, which is not a defect rate but the
norm. Popular checklist advice, contradicted by the only measurement of it. A test
in `tests/test_readme.py` pins their absence. See
[rule-research.md](rule-research.md).

## Semantic density (NB6) — empty prose

| Code | Name | Sev | Flags | Example |
|------|------|-----|-------|---------|
| `NB601` | low-concreteness | info | A paragraph whose nouns and verbs average far toward the abstract end of the Brysbaert et al. (2014) concreteness norms (~37k lemmas, rated 1 = abstract … 5 = concrete by thousands of raters). Grammatical prose that names nothing you can see or touch — corporate mush and LLM filler score here. Calibrated on the essayist corpus: all 810 paragraphs of Paul Graham, Orwell, Housel, Sivers, Slate Star Codex, V. Nabokov, and patio11 score above the threshold. Needs ≥ 12 rated words to judge. | "The strategic integration of innovative paradigms requires the optimization of dynamic synergies…" (2.1/5) |

The fix is never mechanical: add a concrete example, number, or image, or ask the
author for one. The [nabokov-editor skill](../skills/nabokov-editor/SKILL.md) treats
this as an approval-gated change, since inventing detail is worse than abstraction.

## Style drift (NB7) — needs an author profile

Classic stylometry in reverse: instead of identifying an author, nabokov records
their signature and flags what falls outside it. Build a profile from a corpus of
one author's texts, then lint against it:

```bash
nabokov --build-profile me.style.json my-posts/          # extract the signature
nabokov --profile-card paulgraham                        # read a bundled voice card
nabokov --profile-card list                              # bundled profile names
nabokov --ai --style paulgraham draft.md                 # lint with drift checks
```

Bundled profiles (built from the calibration corpus): `paulgraham`, `orwell`,
`housel`, `patio11`, `scottalexander`, `sivers`, `nabokov`. `--style` also takes a
path to your own profile JSON. The NB7 rules are enabled by default but **inert
without `--style`** — no profile, no findings. All advisory: the advice direction
is always "come back to the author's distribution", never "imitate harder".

| Code | Name | Sev | Flags | Example |
|------|------|-----|-------|---------|
| `NB701` | style-connector | info | A sentence opens with a connector the author uses below 1 per 1000 sentences — strict absence is too strict; on a big corpus every connector appears once somewhere (profile needs ≥ 300 sentences). Names the author's actual favorites. | "**Moreover,** …" against a profile whose connectors are but/and/so |
| `NB702` | style-rhythm | info | Sentence variety or punctuation looseness below 0.65× the author's baseline — flatness only; more varied than the author is not a defect. Needs ≥ 6 sentences and a ≥ 5k-word profile. | uniform 12-word sentences vs an author at CV 0.7 |
| `NB703` | style-punctuation | info | A mark at ≥ 3× the author's per-1000-word rate (≥ 3 occurrences, ≥ 1/1000 excess, max 3 findings). Anchored at the file top — it is a document-level rate. | em dash at 8.1/1000 vs Graham's 1.4 |
| `NB704` | style-authorship | info | Stylometric distance: Burrows' Delta (mean absolute z-score of function-word rates against the author's per-1000-word-block statistics) above 1.1, or POS-trigram Jensen-Shannon divergence above 0.35. Thresholds sit above the same-author p90 measured on the shipped corpus (574 pairings: same-author Delta median 0.67/p90 1.06, cross-author median 1.01). Needs a ≥ 5-block profile and ≥ 300 words of text; an advisory range signal, not an attribution verdict. | Delta 1.4 from `mikhail` on ghostwritten copy |

A profile is honest data — favorite words, connectors, rhythm norms the author
demonstrably has. The voice card ends with the rule that keeps it safe: reuse the
author's *words*, never invent facts or opinions on their behalf.

---

Writing about a style rule

A document that *discusses* these words trips the rules that flag them — this
reference did, on its own NB308 row. nabokov already drops a finding when the
quote holds nothing but the flagged term, so `"simply"` in straight quotes is
read as a mention rather than a use. Where that reads badly, an inline
`<!-- nabokov: ignore NB308 -->` is the escape hatch.

One trap worth knowing when writing these examples: the straight-quote mention
rule **does not span a line break**. `"studies\nshow"` wrapped across two lines
of hard-wrapped source is not seen as quoted, so NB316 fires on it — which is how
both skill files first tripped their own new rule. The restriction is deliberate:
letting a straight quote pair across lines would let an inch mark (`15"`) reach a
closing quote on the next line and swallow every finding between them, which
`test_straight_quote_does_not_span_lines` pins. Keep a quoted example on one line,
or use curly quotes, which are unambiguous and may wrap.

## Severities & exit codes

`NB101` (over `--max-grade`) is the only error. `NB2xx` and the confident `NB5xx`
tells are warnings; `NB301`/`NB302`/`NB303`/`NB401` are `info` within their style
budget and `warning` over it (see *Style budgets*); `NB202` drops to `info`
when the whole document reads fine for its target; the advisory `NB5xx` checks are
`info`. Exit `0` = clean, `1` = findings (`--exit-zero` to soften), `2` = usage
error.

## The markup index

For `.md` and `.html`, blanking records **what** it erased as well as where:
a list of typed `MarkupSpan(start, end, kind)` on the source. Without it the
knowledge is lost — after blanking, every erased region is identical spaces, and
a heading's text is indistinguishable from body prose.

Kinds: `frontmatter`, `fence`, `inline-code`, `html`, `ref-def`, `citation`,
`image`, `image-alt`, `link-text`, `link-url`, `url`, `heading-marker`,
`heading`, `table-row`, `blockquote`, `list-marker`, `emphasis`, `rule`.

Two properties make it usable:

- **It indexes structure, not just erasure.** `link-text` marks words that
  *survive* into the analysis text and get read as prose. A rule asking "was this
  phrase link text?" cannot answer that from the blanked-text diff.
- **Order still does the filtering.** Fenced code is blanked first, so a link or
  an `<img>` inside a code block is never recorded as markup — showing the syntax
  is not using it.

Recording spans does not touch the text, so the length-preserving invariant and
every offset are unchanged. `NB311` and `NB312` use it today. `NB312` is the clearest case for the index
existing: without `link-text` spans the check can only phrase-match "click
here" anywhere in the prose, which misses the bare `[here](url)` — the
commonest form by far — and cannot tell a link from someone writing the words
*click here* about a button. `NB313` reads the `heading` kind. The `fence` and `table-row` kinds are
recorded and not yet consumed.

## Data

The word lists, complex-phrase dictionary, and readability thresholds live in
`../src/nabokov/data/`. The AI-writing signal lists live in
`../src/nabokov/data/ai_writing.json`.

NB309's acronym allowlist is `acronyms.json`; `known_acronyms` in config extends
it per project, which is the intended answer to a noisy run on domain vocabulary.
The English-word guard reuses `concreteness.json` — the Brysbaert norms NB601
already needs — rather than shipping a second dictionary.

The fix data lives beside the terms it annotates: `puffery_alternatives` in
`ai_writing.json`, the `cut`/`replace`/`rewrite` groups in `qualifiers.json`, the
phrase alternatives in `complex_phrases.json`, the nominalization verbs in
`nominalizations.json`, and the participle-to-past forms NB302 rewrites with in
`passive_irregulars.json`.

These are closed, hand-written sets over terms nabokov already flags, never a
general thesaurus. A broad synonym source (WordNet, embeddings) returns the wrong
sense and the wrong register, and one bad suggestion costs more trust than a
missing one buys. Adding an alternative must not widen what gets flagged: the
keys are checked against the term lists in `tests/test_suggestions.py`.
