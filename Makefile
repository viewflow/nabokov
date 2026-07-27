.PHONY: deploy-web deploy-web-app deploy-bot update-bot bot-run bot-test \
	bot-lock bot-lock-check test lint format typecheck prose check versions release

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
deploy-bot: bot-lock-check
	ansible-playbook -i ansible/inventory.ini ansible/bot.yml $(ANSIBLE_ARGS)

# Bot code + deps refresh only (rsync, uv sync, restart).
update-bot: bot-lock-check
	ansible-playbook -i ansible/inventory.ini --tags=update ansible/bot.yml $(ANSIBLE_ARGS)

# The bot installs nabokov from the git commit recorded in bot/uv.lock, so
# shipping new bot code does NOT pull a new linter. Re-point the lock at the
# pushed release commit (the dependency is unpinned, so this resolves remote
# HEAD — push first), then commit bot/uv.lock.
bot-lock:
	cd bot && uv lock --upgrade-package nabokov

# Guards both deploys: a lock still on the previous release means the bot would
# run yesterday's rules against today's code. 26.7.9 shipped that way.
bot-lock-check:
	uv run python scripts/check_versions.py --bot-lock

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

# The linter ships to PyPI, the skills ship through git (npx skills add, and the
# Claude plugin marketplace). Nothing ties the two channels together, so a user
# can end up with skill instructions describing rules their linter has never
# heard of — and that fails SILENTLY: the agent asks for a rule that does not
# exist, gets nothing, and reports a clean file. Every version must move at once.
versions:
	uv run python scripts/check_versions.py

# Gate a release. Publish to PyPI and push git together — a push without a
# release reopens exactly the skew this exists to prevent.
release: versions check
	rm -rf dist
	uv build
	@echo
	@echo "Built. Now publish and push TOGETHER:"
	@echo "    uv publish && git push && git push --tags"
	@echo
	@echo "Then re-point the bot at the pushed commit and ship it:"
	@echo "    make bot-lock && git commit -am 'bot: bump lock' && git push"
	@echo "    make deploy-web-app && make update-bot"
