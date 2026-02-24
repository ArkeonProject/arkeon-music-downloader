PY := python3
PIP := pip

.PHONY: help setup install dev fmt lint type test run docker-build docker-up docker-logs docker-down pre-commit

help:
	@echo "Targets: setup install dev fmt lint type test run docker-build docker-up docker-logs docker-down pre-commit"

setup:
	cd backend && $(PY) -m venv venv
	cd backend && . venv/bin/activate && $(PIP) install --upgrade pip

install:
	cd backend && . venv/bin/activate && $(PIP) install -r requirements.txt

dev:
	cd backend && . venv/bin/activate && $(PIP) install -r requirements.txt && $(PIP) install -e '.[dev]'

fmt:
	cd backend && . venv/bin/activate && black src tests scripts --line-length 88

lint:
	cd backend && . venv/bin/activate && flake8 src tests --max-line-length=88

type:
	cd backend && . venv/bin/activate && mypy src

test:
	cd backend && . venv/bin/activate && PYTHONPATH=src pytest -q

run:
	cd backend && . venv/bin/activate && uvicorn src.youtube_watcher.api.main:app

docker-build:
	docker-compose -f docker-compose.dev.yml build

docker-up:
	docker-compose -f docker-compose.dev.yml up -d

docker-logs:
	docker-compose -f docker-compose.dev.yml logs -f --tail=100

docker-down:
	docker-compose -f docker-compose.dev.yml down

pre-commit:
	. venv/bin/activate; pre-commit install
	. venv/bin/activate; pre-commit run --all-files || true
