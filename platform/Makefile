.PHONY: setup test lint api agent frontend docker bridge clean

VENV := .venv
PY := $(VENV)/bin/python

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[api,dev]"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check core api agents persistence tests

api:
	$(PY) -m uvicorn masld_api.app:create_app --factory --reload --port 8000

agent:
	$(PY) -m masld_platform.cli agent

frontend:
	cd frontend && npm install && npm run dev

docker:
	docker compose -f infra/docker-compose.yml up --build

bridge:
	$(PY) -m masld_platform.cli bridge-sync

clean:
	rm -rf .pytest_cache .ruff_cache dist build *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
