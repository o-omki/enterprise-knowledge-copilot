PYTHON ?= python

.PHONY: install install-dev format lint type-check test dev pre-commit-install ingest-docs run-evals worker eval-serving load-test load-test-report dashboards observability-check tf-init tf-validate tf-plan tf-apply tf-destroy

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


eval-all:
	@echo "Running ALL evaluations..."
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli run-all
	@echo "All evaluations complete."

eval-retrieval:
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli run --runner retrieval

eval-reranking:
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli run --runner reranking

eval-generation:
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli run --runner generation

eval-safety:
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli run --runner safety

eval-latency:
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli run --runner latency

eval-serving:
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli run --runner serving

eval-regression:
	@echo "Running regression check against baseline..."
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli compare

eval-freeze-baseline:
	@echo "Freezing current results as new baseline..."
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli freeze-baseline

generate-eval-dataset:
	@echo "Generating golden QA evaluation dataset..."
	PYTHONPATH=. $(PYTHON) -m apps.evals.cli generate-dataset

# Legacy aliases (deprecated — use eval-* targets above)
run-evals: eval-all

worker:
	poetry run celery -A apps.worker.celery_app worker --loglevel=info

frontend:
	@echo "Starting Next.js frontend..."
	cd apps/frontend && npm run dev

load-test:
	@echo "Running load test suite..."
	PYTHONPATH=. $(PYTHON) scripts/load_test.py

load-test-report:
	@echo "Generating load test report..."
	PYTHONPATH=. $(PYTHON) scripts/load_test_report.py

dashboards:
	@echo "Grafana: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "Jaeger: http://localhost:16686"

observability-check:
	@echo "Checking observability stack health..."
	curl -sf http://localhost:9090/-/healthy && echo "Prometheus: OK" || echo "Prometheus: FAIL"
	curl -sf http://localhost:3001/api/health && echo "Grafana: OK" || echo "Grafana: FAIL"
	curl -sf http://localhost:16686/ && echo "Jaeger: OK" || echo "Jaeger: FAIL"

tf-init:
	terraform -chdir=infra/terraform init

tf-validate:
	terraform -chdir=infra/terraform validate

tf-plan:
	terraform -chdir=infra/terraform plan

tf-apply:
	terraform -chdir=infra/terraform apply

tf-destroy:
	@echo "WARNING: Running terraform destroy will tear down the infrastructure."
	@read -p "Are you sure? [y/N]: " ans && [ $${ans:-N} = y ]
	terraform -chdir=infra/terraform destroy

