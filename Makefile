# ==============================================================================
# SovereignForge & PrivyCode — Developer & Ops Makefile
# ==============================================================================

.PHONY: help dev test e2e benchmark package-ext docker-build gcp-plan gcp-apply clean

help:
	@echo "SovereignForge & PrivyCode Developer Commands:"
	@echo "  make dev          - Start PostgreSQL, Redis, and seed database"
	@echo "  make test         - Run full Pytest unit test suite (18 tests)"
	@echo "  make e2e          - Run end-to-end integration test suite (7 flows)"
	@echo "  make benchmark    - Run latency & token throughput benchmark CLI"
	@echo "  make package-ext  - Compile and package VS Code extension into .vsix"
	@echo "  make docker-build - Build production multi-stage Docker container images"
	@echo "  make gcp-plan     - Run Terraform plan for GCP infrastructure"
	@echo "  make gcp-apply    - Deploy Terraform infrastructure to GCP"
	@echo "  make clean        - Clean cache files and build artifacts"

dev:
	docker compose up -d postgres redis
	@sleep 2
	PYTHONPATH=. ./.venv/bin/python packages/db/seed.py
	@echo "✓ Database seeded. Run 'PYTHONPATH=. uvicorn apps.api.main:app --port 8000' to start Gateway."

test:
	PYTHONPATH=. ./.venv/bin/pytest tests/
	node apps/vscode-extension/out/test/symbolGraph.test.js

e2e:
	PYTHONPATH=. ./.venv/bin/python tests/test_e2e_flow.py

benchmark:
	PYTHONPATH=. ./.venv/bin/python services/benchmark/main.py

package-ext:
	cd apps/vscode-extension && npm run compile && ./node_modules/.bin/vsce package --no-dependencies

docker-build:
	docker build -f deploy/docker/Dockerfile.gateway -t sovereignforge/gateway:latest .
	docker build -f deploy/docker/Dockerfile.worker -t sovereignforge/worker:latest .

gcp-plan:
	cd deploy/gcp/terraform && terraform init && terraform plan

gcp-apply:
	cd deploy/gcp/terraform && terraform init && terraform apply -auto-approve

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf apps/vscode-extension/out/test/
