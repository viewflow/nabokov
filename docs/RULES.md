# nabokov rules

Every check nabokov can emit, with its code, what it flags, and an example. Codes work
like flake8: enable/disable by exact code or prefix with `--select` / `--ignore` /
`--extend-select` / `--extend-ignore`, in `[tool.nabokov]` config, or inline with
`nabokov: ignore NBxxx`.

- **Default run** (`nabokov file`) enables the core checks: `NB201 NB202 NB301 NB302 NB303 NB401`.
- **`NB101`** (readability grade) is emitted only with `--max-grade N`.
- **`NB5xx`** (signs of AI writing) is **off by default** — enable with `--select NB5`
  (AI checks only) or `--extend-select NB5` (alongside the core checks).

Run `nabokov --list-rules` to print this catalog from the tool itself.

---

## Readability (NB1–NB2)

Readability uses the Automated Readability Index (ARI):
`grade = round(letters/words × 4.71 + words/sentences × 0.5 − 21.43)`. Thresholds come
from the reading-level target (`--target`): NORMAL (default), ACCESSIBLE, or TECHNICAL.

| Code | Name | Color | Flags |
|------|------|-------|-------|
| `NB101` | readability | red | The whole-document grade. Emitted as a finding only when it exceeds `--max-grade`. |
| `NB201` | very-hard-sentence | red | A sentence whose reading level is very high (NORMAL: grade ≥ 14, ≥ 14 words). |
| `NB202` | hard-sentence | yellow | A sentence whose reading level is high (NORMAL: grade 10–13, ≥ 14 words). |

Sentences shorter than the target's minimum word count are never flagged.

```
report.md:12:1: NB201 very hard to read (grade 17)
```

## Word & phrase checks (NB3–NB4)

| Code | Name | Color | Flags | Example |
|------|------|-------|-------|---------|
| `NB301` | adverb | blue | An `-ly` adverb spaCy confirms (POS = ADV), minus the exception list. | "He ran **quickly**." |
| `NB302` | passive-voice | green | A passive construction, via spaCy dependency parse (`auxpass`), incl. the "by …" agent. | "The report **was written by the team**." |
| `NB303` | qualifier | blue | A weakening/hedging phrase from the qualifier list. | "**I think** we should wait." |
| `NB401` | complex-phrase | magenta | A wordy phrase with a simpler alternative (the message shows the suggestion). | "**in order to**" → "to" |

```
report.md:3:8: NB302 passive voice: 'was written by the team'
report.md:3:40: NB401 wordy: 'utilize' → use
```

## Signs of AI writing (NB5) — opt-in

Tells drawn from the [Wikipedia "Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
reference plus community lists (Reddit / OpenAI forum threads). These are **tells, not
proof** — enable them deliberately.

Each row has a **severity**: `warning` = a confident tell to fix; `info` = an advisory
"hard part" static isn't sure about (the [nabokov-editor skill](../skills/nabokov-editor/SKILL.md)
leaves those for the LLM to decide). Severity shows in the `json` reporter.

| Code | Name | Sev | Flags | Example |
|------|------|-----|-------|---------|
| `NB501` | ai-negation-contrast | warning | "it's not X, it's Y" / "not only X but Y" antithesis, and "No X, no Y, just Z". | "This **isn't just fast, it's** transformative." |
| `NB502` | ai-puffery | warning | Overused buzzword vocabulary (lemma-matched). | delve, tapestry, embark, labyrinth, synergy … |
| `NB503` | ai-editorializing | info | Promotional / "importance" / vague-attribution phrases. | "**plays a crucial role**", "**experts argue**" |
| `NB504` | ai-filler | warning | Chatbot filler, sycophancy, signposting. | "**Great question!**", "**here's the kicker**", "**let's dive in**" |
| `NB505` | ai-transition | info | Overused formal transitions. | "**Moreover**", "**Furthermore**" |
| `NB506` | ai-em-dash | warning | Em-dash overuse — a *density* above the human range (> 12 per 1000 words; essayists reach ~11). | "It was fast — clean — simple — done." |
| `NB507` | ai-rule-of-three | warning | 3+ consecutive short staccato fragments on one line. | "The jokes. The wins. The team." |
| `NB508` | ai-emoji | warning | Emoji as formatting (≥ 3 in the document). | "✅ fast ✅ safe 🚀 shipped" |
| `NB509` | ai-monotonous-rhythm | info | Flat sentence rhythm (low burstiness / length variety). | uniform mid-length sentences throughout |
| `NB510` | ai-intensifier | info | Weak intensifiers / weasel words. | "**very**", "**really**", "**basically**" |
| `NB511` | ai-participial-closer | info | Empty present-participle "significance" closer. | "…, **highlighting its importance**." |
| `NB512` | ai-repeated-opener | info | 3+ sentences in a row opening with the same word. | "It … It … It …" |
| `NB513` | ai-curly-quote | info | Curly quotes that are the *minority* against straight quotes (inconsistent — a pasted-in LLM snippet). All-curly typography is not flagged. | straight text with a stray “curly” pair |
| `NB514` | ai-title-case-heading | info | Title Case headings (a capitalized function word gives it away). | "## Getting Started **With** Django" |
| `NB515` | ai-predicate-hyphen | info | A hyphenated compound used predicatively should drop the hyphen. | "the team is **cross-functional**" |
| `NB516` | ai-bold-listicle | info | A stack (≥ 3) of `**Label:**` bold-header bullets. | "- **First:** … - **Second:** …" |

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

---

## Severities & exit codes

Findings are advisory warnings; `NB101` (over `--max-grade`) and `NB201` are errors.
Exit `0` = clean, `1` = findings (`--exit-zero` to soften), `2` = usage error.

## Data

The word lists, complex-phrase dictionary, and readability thresholds live in
`../src/nabokov/data/`. The AI-writing signal lists live in
`../src/nabokov/data/ai_writing.json`.
