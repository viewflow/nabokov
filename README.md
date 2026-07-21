# nabokov

A console linter for English prose. Hard sentences, adverbs, passive voice: one
warning per line.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Built with spaCy](https://img.shields.io/badge/nlp-spaCy-09a3d5)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Code gets review. Prose gets a shrug. nabokov catches hard-to-read sentences, adverbs,
passive voice, wordy phrases, and qualifiers, plus opt-in checks for the tells of AI
writing. A readability grade comes with the report. Findings print as warnings you can
pipe into an editor or CI. Each check is a rule with its own code, so you switch checks
on and off the way you do with `flake8`.

## Try it

```sh
uvx nabokov draft.md          # one command, no setup; fetches the model on first run
```

## Why

Code has linters, but prose rarely does. Style guides live in people's heads. nabokov
moves them into your terminal. It points at the sentence that reads hard and says why.

The rule set is inspired by the [Hemingway Editor](https://hemingwayapp.com/).
Detection runs on spaCy. Passive voice comes from a dependency parse, not a
fragile regex.

## Install

Requires Python 3.12 or newer.

```sh
uv tool install nabokov       # or: pipx install nabokov
nabokov download-model        # one-time: fetch the spaCy model (en_core_web_sm)
nabokov draft.md
```

The model is a separate download because PyPI does not allow the direct-URL
dependency it ships as. `nabokov` fetches it on first run; the explicit
`nabokov download-model` (or `python -m spacy download en_core_web_sm`) does it up
front. For local development, `uv sync` installs everything, including the model.

## Usage

```sh
nabokov draft.md                 # colored report for humans
nabokov --format=flake8 x.md     # path:line:col: CODE message
cat notes.txt | nabokov -        # read from stdin
nabokov docs/                    # walk a directory of .txt / .md / .html files
nabokov --max-grade 9 x.md       # exit non-zero if the grade goes over 9
nabokov --select NB302 x.md      # run one rule
nabokov --ignore NB301 x.md      # skip a rule
nabokov --list-rules             # print every code
```

nabokov reads plain text, Markdown, and HTML. For `.md` and `.html` it blanks the
markup: code, tags, and link URLs. It then checks only the visible prose, so findings
point at real writing. For stdin, `--stdin-display-name draft.md` sets the type.

Exit codes follow `flake8`: `0` when clean, `1` when there are findings, `2` on a usage
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

- **NB201 / NB202**: the `very hard` and `hard` reading levels.
- **NB301**: adverbs.
- **NB302**: passive voice.
- **NB303**: qualifiers and hedges.
- **NB401**: wordy phrases, with a simpler suggestion.
- **NB101**: the document grade, reported with `--max-grade`.

## Signs of AI writing (opt-in)

nabokov also spots common LLM tells (`NB5xx`). The lists come from the Wikipedia guide
and community threads. It catches the `it's not X, it's Y` construction and puffery like
`delve` or `tapestry`. Promotional phrases, chatbot filler like `Great question!`, and
overused transitions all trip it. It also flags em-dash and emoji overuse. Rule-of-three
fragments, flat sentence rhythm, and repeated openers round it out.

These checks stay off by default, because they often flag a writer's own voice. Turn
them on with a flag:

```sh
nabokov --ai draft.md         # the core checks plus the AI-writing checks
nabokov --ai-only essay.md    # only the AI-writing checks
```

`--ai` is shorthand for `--extend-select NB5`, and `--ai-only` for `--select NB5`.

## Pair it with the agent skill

The linter catches the mechanical part. Add the `nabokov-editor` skill to your coding
agent and it also fixes the findings, then reads for what rules miss: empty sentences,
invented detail, hollow closers. Fixes keep your meaning. Big edits wait for your
approval.

```sh
# Claude Code
/plugin marketplace add viewflow/nabokov
/plugin install nabokov@viewflow

# Cursor, Codex, Gemini CLI, and other agents (via the skills CLI)
npx skills add viewflow/nabokov
```

Then ask your agent to lint or de-slop a file. Skill details live in
[skills/nabokov-editor/SKILL.md](skills/nabokov-editor/SKILL.md).

## Configuration

Put settings under `[tool.nabokov]` in `pyproject.toml`, or in a `.nabokov.toml`.
nabokov walks up from the current directory to find one. CLI flags win.

```toml
[tool.nabokov]
target = "NORMAL"       # ACCESSIBLE | NORMAL | TECHNICAL
ignore = ["NB301"]      # e.g. stop flagging adverbs
```

Suppress one line inline:

```
This sentence is fine.  <!-- nabokov: ignore NB302 -->
```

## How it works

nabokov scores readability with the Automated Readability Index (ARI). Word
characters drive the grade, so nabokov counts no syllables.

The adverb list, phrase dictionary, and reading-level thresholds combine classic
plain-language word lists with our own additions: extra hedges, more phrase
alternatives, and a fuller set of irregular participles.

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
