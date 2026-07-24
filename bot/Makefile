.PHONY: run deploy update test

run:
	uv run python main.py

deploy:
	ansible-playbook -i deploy/inventory.ini deploy.yml

# Refresh code only
update:
	ansible-playbook -i deploy/inventory.ini --tags=update deploy.yml

test:
	uv run pytest
