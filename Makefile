.PHONY: deploy deploy-app test lint format typecheck prose check

# Full deploy: app on jack.lan + nginx edge on viewflow.io
deploy:
	ansible-playbook -i ansible/inventory.ini ansible/deploy.yml

# App-only refresh (skip the edge)
deploy-app:
	ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --limit app

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
