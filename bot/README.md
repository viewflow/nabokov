# nabokov editor bot

Telegram bot [@nabokov_editor_bot](https://t.me/nabokov_editor_bot): de-slops
and enlivens texts using the [nabokov](https://github.com/viewflow/nabokov)
prose linter plus DeepSeek.

Flow: send a text (≤600 words) → pick a mode (editor / copywriter) and
creativity (normal / raised temperature) with inline buttons → the bot lints
the text (English only — the linter is English), rewrites it via DeepSeek
(which can call the linter as a tool to check itself, and can ask you a
clarifying question with buttons), and replies with the result plus the
AI-likeness score before/after.

Quota: admin (`kmmbvnr`) unlimited; everyone else 3 free texts, then packs of
13 texts for 50 Telegram Stars.

## Run

```sh
cp .env.example .env  # TELEGRAM_BOT_TOKEN, DEEPSEEK_API_KEY
uv sync
uv run nabokov download-model
make run
```

## Deploy

```sh
cp .env deploy/.env
make deploy           # jack.lan, systemd unit nabokov-bot
make update           # code refresh only
```
