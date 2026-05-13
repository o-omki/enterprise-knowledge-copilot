PYTHON ?= python

.PHONY: install install-dev format lint type-check test dev pre-commit-install ingest-docs run-evals

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

format:
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m ruff format .

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format . --check

type-check:
	$(PYTHON) -m mypy apps packages

test:
	$(PYTHON) -m pytest -q

dev:
	$(PYTHON) -m uvicorn apps.api.app.main:app --reload --host 0.0.0.0 --port 8000

pre-commit-install:
	pre-commit install

ingest-docs:
	@echo "Running document ingestion..."
	PYTHONPATH=. $(PYTHON) scripts/ingest_docs.py
	@echo "Document ingestion complete."


run-evals: eval-retrieval
	@echo "All evaluations complete."

eval-retrieval:
	@echo "Running retrieval evaluation..."
	PYTHONPATH=. $(PYTHON) benchmarks/retrieval/eval_retrieval.py
	@echo "Retrieval evaluation complete."
