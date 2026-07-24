.PHONY: deploy-web deploy-web-app deploy-bot update-bot bot-run bot-test \
	test lint format typecheck prose check

# ─────────────────────────────────────────────────────────────────────────
# Deploy (two separate playbooks, both under ansible/, shared inventory.ini).
# On the home LAN jack.lan resolves directly. From outside, append the
# reverse-tunnel overrides to any deploy target:
#     make deploy-web-app ANSIBLE_ARGS="-e ansible_host=viewflow.io -e ansible_port=22022 -e ansible_user=root"
# ─────────────────────────────────────────────────────────────────────────
ANSIBLE_ARGS ?=

# Web demo: nabokov-web on jack.lan + nginx TLS edge on viewflow.io.
deploy-web:
	ansible-playbook -i ansible/inventory.ini ansible/deploy.yml $(ANSIBLE_ARGS)

# Web app only (skip the edge/TLS play).
deploy-web-app:
	ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --limit app $(ANSIBLE_ARGS)

# Telegram bot @nabokov_editor_bot on jack.lan (full run).
deploy-bot:
	ansible-playbook -i ansible/inventory.ini ansible/bot.yml $(ANSIBLE_ARGS)

# Bot code + deps refresh only (rsync, uv sync, restart).
update-bot:
	ansible-playbook -i ansible/inventory.ini --tags=update ansible/bot.yml $(ANSIBLE_ARGS)

# ─────────────────────────────────────────────────────────────────────────
# Bot local dev (bot/ is its own uv project).
# ─────────────────────────────────────────────────────────────────────────
bot-run:
	cd bot && uv run python main.py

bot-test:
	cd bot && uv run pytest

# ─────────────────────────────────────────────────────────────────────────
# Linter package (this repo).
# ─────────────────────────────────────────────────────────────────────────
test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

# The skills must pass their own linter: no very-hard sentences, document
# grade <= 9 (roughly B1/B2 reading level).
prose:
	uv run nabokov --select NB201 --max-grade 9 \
		skills/nabokov-editor/SKILL.md skills/nabokov-copywriter/SKILL.md

check: lint typecheck prose test
