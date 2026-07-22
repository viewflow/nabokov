# nabokov

A console linter for English prose: readability, and the tells of AI writing.
One warning per line, toggled like `flake8`.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Built with spaCy](https://img.shields.io/badge/nlp-spaCy-09a3d5)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Code gets review. Prose gets a shrug. nabokov catches hard sentences, adverbs,
passive voice, wordy phrases, and qualifiers. Every report carries a readability
grade. Opt-in checks catch the tells of AI writing: puffery like `delve`, chatbot
filler, em-dash pileups, flat robotic rhythm. Findings print as warnings you pipe
into an editor or CI. Each check is a rule with its own code, so you toggle them
like `flake8`.

## Try it

```sh
uvx nabokov draft.md          # one command, no setup; fetches the model on first run
```

Point it at a paragraph of AI slop and it answers:

```
$ nabokov --ai release-notes.md
release-notes.md:1:14: NB502 AI tell: puffery 'leverages'
release-notes.md:1:51: NB502 AI tell: puffery 'transformative'
release-notes.md:1:75: NB501 AI tell: negation-contrast 'It's not just an update, it's'
release-notes.md:1:107: NB502 AI tell: puffery 'paradigm'
release-notes.md:1:127: NB302 passive voice: 'was celebrated by the whole team'

5 issues in 1 file
```

<strong><a href="https://nabokov.viewflow.io/#live" target="_blank" rel="noopener">Or try it in your browser →</a></strong> (no install).

## Why

Code has linters, but prose rarely does. Style guides live in people's heads. nabokov
moves them into your terminal. It points at the sentence that reads hard and says why.

## Install

Requires Python 3.12 or newer.

```sh
uv tool install nabokov       # or: pipx install nabokov
nabokov download-model        # one-time: fetch the spaCy model (en_core_web_sm)
nabokov draft.md
```

That spaCy model is why nabokov is accurate. It reads grammar, not patterns: it
tells a verb from a noun and follows sentence structure, so it raises far fewer
false alarms than a regex linter. nabokov fetches it on the first run, and
`nabokov download-model` does it up front. For local development, `uv sync` pulls
everything.

## Usage

```sh
nabokov draft.md                 # colored report for humans
nabokov --format=flake8 x.md     # path:line:col: CODE message
cat notes.txt | nabokov -        # read from stdin
nabokov docs/                    # walk a directory of .txt / .md / .html files
nabokov --max-grade 9 x.md       # exit non-zero if the grade goes over 9
nabokov --target essay draft.md  # judge against the ESSAY reading level
nabokov --select NB302 x.md      # run one rule
nabokov --ignore NB301 x.md      # skip a rule
nabokov --stats x.md             # document metrics: grade, sentence length, burstiness
nabokov --list-rules             # print every code
```

`--stats` prints one metrics line per file (also in `--format json` as `summary`).
Burstiness is the sentence-length coefficient of variation. High means varied,
human rhythm. Low means flat and machine-uniform. Diff it between two drafts to
catch a rewrite that got polished flat.

nabokov reads plain text, Markdown, and HTML. For `.md` and `.html` it blanks the
markup: code, tags, and link URLs. It then checks only the visible prose, so findings
point at real writing. For stdin, `--stdin-display-name draft.md` sets the type.

Exit codes follow `flake8`: `0` when clean, `1` on findings, `2` on a usage
error.

## Output formats

Choose one with `--format`:

- **Color** (`--format=color`) highlights snippets and adds a grade summary. It is the terminal default.
- **Flake8** (`--format=flake8`) prints one finding per line, for editors and CI.
- **JSON** (`--format=json`) returns diagnostics plus the document grade.
- **GitHub** (`--format=github`) emits workflow annotations for GitHub Actions.

## Rules

Run `nabokov --list-rules` to see them all. The full reference lives in
[docs/RULES.md](docs/RULES.md).

| Code | What it flags |
|------|---------------|
| `NB201` / `NB202` | The `very hard` and `hard` reading levels. |
| `NB203` | A main clause buried after 20+ words of build-up (advisory). |
| `NB301` | Adverbs. |
| `NB302` | Passive voice. |
| `NB303` | Qualifiers and hedges. |
| `NB304` | Nominalizations behind light verbs: "came to an agreement" → *agreed*. |
| `NB305` | Dummy subjects: "There are many resorts in Colorado" → "Colorado has…". |
| `NB306` | Repeated words: "Paris in the the spring". |
| `NB307` | Uncomparables: "very unique", "most perfect". |
| `NB401` | Wordy phrases, with a simpler suggestion. |
| `NB601` | Abstract, "empty prose" paragraphs, scored against the Brysbaert concreteness norms (advisory). |
| `NB101` | The document grade, reported with `--max-grade`. |

## Reading-level targets

One bar does not fit every text. `--target` sets the level nabokov holds a sentence
to (case-insensitive):

- `accessible`: plain language; sentences count as `hard` from grade 8, `very hard` from 12.
- `normal`: the default; `hard` from grade 10, `very hard` from 14.
- `technical`: docs for expert readers; `hard` from grade 14, `very hard` from 18.
- `essay`: essays, blog posts, opinion pieces. The TECHNICAL thresholds, plus the
  loosest style budgets for a writer's voice.
- `social`: short-form posts. Plain-language thresholds. Staccato fragments
  and repeated openers are the genre's voice, not AI tells.
- `email`: business email. A high-trust audience, so the tightest style budgets
  of any target.

```sh
nabokov --target technical api-guide.md
nabokov --target essay draft.md
```

Each target also carries style budgets, counted per 1000 words. Adverbs, passive
voice, qualifiers, and wordy phrases stay `info` within budget. Over budget, they
become warnings. To make a target stick, set `target` in your
config instead of passing the flag each run (see below).

## Signs of AI writing (opt-in)

nabokov also spots common LLM tells (`NB5xx`). The lists come from the Wikipedia guide
and community threads. It catches the `it's not X, it's Y` construction and puffery like
`delve` or `tapestry`. Promotional phrases, chatbot filler like `Great question!`, and
overused transitions all trip it. It also flags em-dash and emoji overuse. Rule-of-three
fragments, flat sentence rhythm, and repeated openers round it out. It even puts a
number on the flat rhythm: `--stats` prints the burstiness, a measure of
sentence-length variation. Watch it to catch a rewrite going machine-even.

These checks stay off by default, because they often flag a writer's own voice. Turn
them on with a flag:

```sh
nabokov --ai draft.md         # the core checks plus the AI-writing checks
nabokov --ai-only essay.md    # only the AI-writing checks
```

`--ai` is shorthand for `--extend-select NB5`, and `--ai-only` for `--select NB5`.

## Pair it with the agent skills

The linter catches the mechanical part. Two sibling skills teach an agent to act on it.

**`nabokov-editor`** fixes the findings, then reads for what rules miss: empty
sentences, invented detail, hollow closers. Fixes keep your meaning. Big edits wait
for your approval.

**`nabokov-copywriter`** does the opposite move. A clean draft can still be flat, so
this skill *adds*. You pick a goal (sell, reach, provoke, or build trust), and it
rebuilds the draft toward it: rhythm, a concrete scene, a proven structure, a call to
action. It works from your real facts and asks when a scene needs a detail it doesn't
have, then re-lints so the polish never slides back into slop.

```sh
# Claude Code
/plugin marketplace add viewflow/nabokov
/plugin install nabokov@viewflow

# Cursor, Codex, Gemini CLI, and other agents (via the skills CLI)
npx skills add viewflow/nabokov
```

Then ask your agent to de-slop a file, or to make copy land. Skill details live in
[skills/nabokov-editor/SKILL.md](skills/nabokov-editor/SKILL.md) and
[skills/nabokov-copywriter/SKILL.md](skills/nabokov-copywriter/SKILL.md).

## Configuration

Put settings under `[tool.nabokov]` in `pyproject.toml`, or in a `.nabokov.toml`.
nabokov walks up from the current directory to find one. CLI flags win.

```toml
[tool.nabokov]
target = "NORMAL"       # ACCESSIBLE | NORMAL | TECHNICAL | ESSAY | SOCIAL | EMAIL
ignore = ["NB301"]      # e.g. stop flagging adverbs

[tool.nabokov.budgets]  # optional: per-1000-word style budgets (see docs/RULES.md)
NB301 = 20              # adverbs stay advisory (info) up to this density
```

Suppress one line inline:

```
This sentence is fine.  <!-- nabokov: ignore NB302 -->
```

## How it works

nabokov scores readability with the Automated Readability Index (ARI). Word
characters drive the grade, so nabokov counts no syllables.

The adverb list and the phrase dictionary began as classic lists for plain
language. We added extra hedges and more phrase alternatives. A fuller set of
irregular participles feeds the passive check.

spaCy handles the parsing. Passive voice reads the `auxpass` dependency. Adverbs read
the part-of-speech tag plus the `-ly` suffix. The pipeline loads once and runs on every
file.

## Development

```sh
uv run pytest               # the test suite
uv run ruff check .         # lint
uv run ruff format .        # format
uv run pyright              # type-check
```

The [nabokov-editor skill](skills/nabokov-editor/SKILL.md) drives the linter inside an agent loop. It
detects issues, rewrites while preserving meaning, and asks before any large change.

## License

MIT.

## Credits

Inspired by the [Hemingway Editor](https://hemingwayapp.com/). Parsing uses
[spaCy](https://spacy.io/). The name is a nod to a writer who cared about sentences.
