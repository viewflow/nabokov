.PHONY: deploy deploy-app test lint format typecheck check

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

check: lint typecheck test
