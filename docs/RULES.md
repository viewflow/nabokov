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

## Readability (NB1–NB2)

Readability uses the Automated Readability Index (ARI):
`grade = round(letters/words × 4.71 + words/sentences × 0.5 − 21.43)`. Thresholds come
from the reading-level target (`--target`):

- `NORMAL` (default)
- `ACCESSIBLE`
- `TECHNICAL`
- `ESSAY` — voice-friendly: tolerates the longer sentences literary prose sustains
  deliberately, and carries the loosest style budgets (see below)
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
| `NB302` | passive-voice | green | A passive construction, via spaCy dependency parse (`auxpass`), incl. the "by …" agent. | "The report **was written by the team**." |
| `NB303` | qualifier | blue | A weakening/hedging phrase from the qualifier list. "just" is only flagged in hedge positions ("it's **just** a way to…") — restrictive "just one", the imperative opener "Just tell me…", and temporal "I'd just read" are precision devices and skipped. | "**I think** we should wait." |
| `NB304` | nominalization | blue | The action hidden in a noun behind a light verb (dependency-matched, so articles/adjectives/inflection don't matter; the noun alone is never flagged). The message suggests the verb. | "**came to an agreement**" → agreed |
| `NB305` | dummy-subject | blue | An expletive subject burying the real one (spaCy `expl`). Locative "there" is untouched. | "**There are** many resorts in Colorado." → "Colorado has…" |
| `NB306` | repeated-word | blue | The same word twice in a row — the lexical illusion that hides on a line wrap. Grammatical doubles ("had had", "that that"), proper-noun pairs ("Pago Pago"), and emphasis runs of 3+ ("no no no") are skipped. | "Paris in **the the** spring" |
| `NB307` | uncomparable | blue | A degree word on an absolute adjective — the quality either holds or it doesn't. Approximators stay legal ("almost impossible"), and soft absolutes (essential, universal, ideal, ultimate, absolute) accept comparison — "the most essential feature" is ordinary prose; only intensifiers fire on them ("really essential"). | "**very unique**", "**most perfect**" |
| `NB401` | complex-phrase | magenta | A wordy phrase with a simpler alternative (the message shows the suggestion). | "**in order to**" → "to" |

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
| `NB502` | ai-puffery | warning | Buzzword vocabulary (lemma-matched). A repeated lemma is topic vocabulary and drops to info; literal senses ("test harness") are exempt. | delve, tapestry, embark, synergy … |
| `NB503` | ai-editorializing | info | Promotional / "importance" / vague-attribution phrases. | "**plays a crucial role**", "**experts argue**" |
| `NB504` | ai-filler | warning | Chatbot filler, sycophancy, signposting. Reported speech ("asked **a** great question") is exempt. | "**Great question!**", "**let's dive in**" |
| `NB505` | ai-transition | info | Overused formal transitions — human formal prose uses them too, so advisory. | "**Moreover**", "**In conclusion**" |
| `NB506` | ai-em-dash | warning | Em-dash *density* above the human range (> 12 per 1000 words). Counts `—`, spaced `–`, and the spaced hyphen; list bullets don't count. One finding per document. | "It was fast — clean — simple — done." |
| `NB507` | ai-rule-of-three | info | 3+ consecutive short *verbless* fragments on one line. Fragments with a verb are human staccato and exempt. | "The jokes. The wins. The team." |
| `NB508` | ai-emoji | warning | Emoji as formatting (≥ 3 in the document). One finding per document. | "✅ fast ✅ safe 🚀 shipped" |
| `NB509` | ai-monotonous-rhythm | info / warning | Flat sentence rhythm (low burstiness). Per-target threshold; robotic flatness escalates to warning. The finding anchors at the flattest run of near-equal sentences. See the CV with `--stats`. | uniform mid-length sentences throughout |
| `NB510` | ai-intensifier | info | Weak intensifiers / weasel words. Emphatic "very" ("the very first time") and idioms ("quite a few") are exempt. | "**very**", "**really**", "**basically**" |
| `NB511` | ai-participial-closer | info | Empty present-participle "significance" closer. | "…, **highlighting its importance**." |
| `NB512` | ai-repeated-opener | info | 3+ sentences in a row opening with the same word. | "It … It … It …" |
| `NB513` | ai-curly-quote | info | Curly quotes in the *minority* against straight quotes — a pasted-in snippet. All-curly typography is exempt. | straight text with a stray “curly” pair |
| `NB514` | ai-title-case-heading | info | Title Case headings (a capitalized function word gives it away). | "## Getting Started **With** Django" |
| `NB515` | ai-predicate-hyphen | info | A hyphenated compound used predicatively should drop the hyphen. | "the team is **cross-functional**" |
| `NB516` | ai-bold-listicle | info | A stack (≥ 3) of `**Label:**` bold-header bullets, or a bold label ended with a period. One finding per stack. | "- **First:** … - **Second:** …" |
| `NB517` | ai-vocab-cluster | info | Generic-praise words that are normal alone but cluster: 2+ *distinct* list words in one paragraph. | "our **significant** and **innovative** platform" |
| `NB518` | ai-adjective-triad | info | Balanced adjective triples at 1.5+/1000 words (min 2) — the tricolon is legitimate rhetoric, so only the density is the tell. A copula-colon launch ("…is: X, Y, and Z") fires alone. | "**innovative, transformative, and groundbreaking**" |
| `NB519` | ai-artifact | warning | Fingerprints: chat citation tokens, AI-tool URL parameters, unfilled placeholders, knowledge-cutoff disclaimers, invisible characters (zero-width space/joiners, mid-text BOM), and mixed-script homoglyph swaps ("dеtection" with a Cyrillic е). Ordinary multilingual text is exempt: NBSP, whole-script words, and Cyrillic suffixes on Latin brands don't fire. No density gating. | "**citeturn0search0**", "**[Your Name]**" |
| `NB520` | ai-hedge-stack | warning | A modal stacked with a hedge adverb — the two hedges cancel out; keep one. | "**could potentially** create" |
| `NB521` | ai-paragraph-opener | warning | The same coordinating conjunction opening 3+ paragraphs (and ≥ 10% of them). | "**And** … ¶ **And** … ¶ **And** …" |
| `NB522` | ai-engagement-bait | info | A closing second-person superlative question — reply bait. Flags *bait*, not AI: humans growth-hack too. | "**What's the most unexpected place you've found genuine customer insight?**" |
| `NB523` | ai-anaphora-triad | info | The same quantifier (more/every/each…) opening three coordinated phrases. A pair or a varied list is exempt. | "**more code reviews, more reports, and more style guides**" |
| `NB524` | ai-contrast-heading | info / warning | The "X, not Y" heading. One is advisory (human titles use it); 2+ in a document escalate to warning. Running text is `NB501`'s territory. | "## **Pin decisions, not knowledge**" |
| `NB525` | ai-hook-question | info | A verbless 2–4-word question answered by the next sentence. Real questions ("Why? Because…") and fragments with a verb are exempt. | "**The best part? It's free.**" |
| `NB526` | ai-false-range | info | "from X to Y" where the endpoints aren't on any scale (both abstract per the concreteness norms). Proper nouns, numbers, concrete pairs, and motion-verb transfers are exempt. | "everything **from strategy to execution**" |
| `NB527` | ai-uniform-paragraphs | info | Every paragraph the same number of sentences (CV < 0.35 over ≥ 6 prose paragraphs). All-one-sentence documents are exempt. One finding per document. | eight paragraphs, three sentences each |
| `NB528` | ai-low-lexical-diversity | info / warning | Narrow, repetitive vocabulary: moving-average TTR (window 100) below 0.55 on ≥ 120 words; below 0.45 escalates to warning. Names the most-repeated content words. See the value with `--stats` (`diversity`). One finding per document. | the same nouns and verbs cycling through every sentence |

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

## Semantic density (NB6) — empty prose

| Code | Name | Sev | Flags | Example |
|------|------|-----|-------|---------|
| `NB601` | low-concreteness | info | A paragraph whose nouns and verbs average far toward the abstract end of the Brysbaert et al. (2014) concreteness norms (~37k lemmas, rated 1 = abstract … 5 = concrete by thousands of raters). Grammatical prose that names nothing you can see or touch — corporate mush and LLM filler score here. Calibrated on the essayist corpus: all 810 paragraphs of PG, Orwell, Housel, Sivers, SSC, V. Nabokov, and patio11 score above the threshold. Needs ≥ 12 rated words to judge. | "The strategic integration of innovative paradigms requires the optimization of dynamic synergies…" (2.1/5) |

The fix is never mechanical: add a concrete example, number, or image, or ask the
author for one. The [nabokov-editor skill](../skills/nabokov-editor/SKILL.md) treats
this as an approval-gated change, since inventing detail is worse than abstraction.

---

## Severities & exit codes

`NB101` (over `--max-grade`) is the only error. `NB2xx` and the confident `NB5xx`
tells are warnings; `NB301`/`NB302`/`NB303`/`NB401` are `info` within their style
budget and `warning` over it (see *Style budgets* above); `NB202` drops to `info`
when the whole document reads fine for its target; the advisory `NB5xx` checks are
`info`. Exit `0` = clean, `1` = findings (`--exit-zero` to soften), `2` = usage
error.

## Data

The word lists, complex-phrase dictionary, and readability thresholds live in
`../src/nabokov/data/`. The AI-writing signal lists live in
`../src/nabokov/data/ai_writing.json`.
