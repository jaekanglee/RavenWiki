# raven — top-level Makefile
# v0.7.13+ — Docker 우선. 로컬 host 실행은 deprecated (Docker compose로 통일).
# Self-documenting: `make` or `make help` lists targets.
#
# Conventions:
#   - All commands run from project root.
#   - Docker compose 셋업: cp .env.example .env && make docker-up
#   - 로컬 host 실행 (Docker 미사용, deprecated): make install && scripts/.venv/bin/python -m raven.cli ...
#   - PYTHONPATH=. so `python -m raven.*` works without install.

SHELL := /bin/bash
VENV := scripts/.venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

# Default target — show help when user just runs `make`
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ────────────────────────── setup ──────────────────────────

.PHONY: install
install: ## Create venv + install raven + dev deps (local dev only — prefer Docker)
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e .
	$(PIP) install --quiet pytest typer fastapi uvicorn 'httpx<0.28' pydantic python-frontmatter
	@echo "✅ installed ($(VENV))"

.PHONY: venv-check
venv-check: ## Fail loudly if venv missing (so other targets work)
	@test -d $(VENV) || (echo "❌ run 'make install' first"; exit 1)

# ────────────────────────── Docker (v0.7.12+ 표준) ──────────────────────────
# v0.7.13+: 로컬 host 실행 target (dev/status/stop/mcp/api/dashboard) 제거됨.
# Docker compose로 통일. 호스트에서 직접 띄울 일 없음 (Docker만).

.PHONY: docker-build docker-up docker-down docker-logs docker-ps
docker-build: ## Build Raven Docker image (multi-stage: dashboard + Python runtime)
	@if [ ! -f .env ]; then \
		echo "📋 .env 없음. .env.example → .env 복사. RAVEN_VAULTS_DIR 조정 후 사용."; \
		cp .env.example .env; \
	fi
	# v0.7.17+: 순차 빌드 강제 (병렬 image 빌드 시 같은 tag 충돌 ❌)
	$(MAKE) --no-print-directory docker-build-api
	$(MAKE) --no-print-directory docker-build-mcp-http
	$(MAKE) --no-print-directory docker-build-dashboard
	@echo ""
	@echo "✅ raven:latest built (3 services: api, mcp-http, dashboard)"

docker-build-api: ## Build api service image only
	docker compose build api

docker-build-mcp-http: ## Build mcp-http service image only
	docker compose build mcp-http

docker-build-dashboard: ## Build dashboard service image only
	docker compose build dashboard

docker-up: ## Start 4 services (API + MCP HTTP + Dashboard, stdio is docker exec)
	@if [ ! -f .env ]; then \
		echo "📋 .env 없음. .env.example → .env 복사. RAVEN_VAULTS_DIR 조정 후 사용."; \
		cp .env.example .env; \
	fi
	docker compose up -d
	@echo ""
	@echo "🟢 Raven Docker stack running:"
	@echo "   • API    → http://localhost:8765        (curl http://localhost:8765/api/vaults)"
	@echo "   • MCP    → http://localhost:8766/mcp    (MCP HTTP client config)"
	@echo "   • UI     → http://localhost:5173        (Dashboard)"
	@echo "   • CLI    → docker compose exec api docker-entrypoint.sh cli <args>"
	@echo "   • MCP stdio → docker compose exec api docker-entrypoint.sh mcp-stdio"
	@echo "🛑 down: make docker-down  |  logs: make docker-logs  |  ps: make docker-ps"

docker-down: ## Stop and remove Raven Docker containers
	docker compose down

docker-logs: ## Follow logs from all Raven services
	docker compose logs -f

docker-ps: ## Show Raven container status
	docker compose ps

# ────────────────────────── test ──────────────────────────

.PHONY: test
test: venv-check ## Run full pytest suite
	$(PY) -m pytest tests/ -q

.PHONY: test-quick
test-quick: venv-check ## Run pytest with stop-on-first-failure
	$(PY) -m pytest tests/ -q -x

.PHONY: test-one
test-one: venv-check ## Run a single pytest file (usage: make test-one F=tests/test_foo.py)
	$(PY) -m pytest $(F) -v

# ────────────────────────── cleanup ──────────────────────────

.PHONY: clean
clean: ## Remove build artifacts (wiki.db, __pycache__, .pytest_cache) — KEEPS vault content
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache
	@echo "✅ clean (vault content preserved)"

.PHONY: nuke
nuke: ## ⚠️ Remove venv + ALL build artifacts (asks for confirmation)
	@echo "⚠️  This will remove scripts/.venv + __pycache__ + .pytest_cache"
	@read -p "Continue? [y/N] " r && [[ $$r =~ ^[Yy]$$ ]]
	rm -rf $(VENV) .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	@echo "✅ nuked"

# ────────────────────────── run / stop shortcuts ──────────────────────────

.PHONY: up down restart rebuild
up: docker-up ## Start Raven via Docker compose (all services including Dashboard)
down: docker-down ## Stop Raven via Docker compose
restart: down up ## Restart Raven via Docker compose
rebuild: docker-build restart ## Rebuild Docker images and restart all services

.PHONY: run-local stop-local restart-local
run-local: venv-check ## Start Raven locally in the background (API + Dashboard dev server)
	@mkdir -p tmp
	@if [ -f tmp/api.pid ] || [ -f tmp/dashboard.pid ]; then \
		echo "⚠️  Already running? Run 'make stop-local' first."; \
		exit 1; \
	fi
	@echo "🚀 Starting API server in background..."
	@PYTHONPATH=. $(PY) -m raven.api > tmp/api.log 2>&1 & echo $$! > tmp/api.pid
	@echo "🚀 Starting Dashboard Vite dev server in background..."
	@cd dashboard && npm run dev > ../tmp/dashboard.log 2>&1 & echo $$! > ../tmp/dashboard.pid
	@sleep 2
	@echo ""
	@echo "🟢 Raven local host stack running:"
	@echo "   • API        → http://127.0.0.1:8765"
	@echo "   • Dashboard  → http://localhost:5173"
	@echo "   • Logs       → tail -f tmp/api.log tmp/dashboard.log"
	@echo "🛑 To stop: make stop-local"

stop-local: ## Stop local background processes (API + Dashboard)
	@echo "🛑 Stopping local background processes..."
	@if [ -f tmp/api.pid ]; then \
		kill $$(cat tmp/api.pid) 2>/dev/null || true; \
		rm -f tmp/api.pid; \
	fi
	@if [ -f tmp/dashboard.pid ]; then \
		kill $$(cat tmp/dashboard.pid) 2>/dev/null || true; \
		rm -f tmp/dashboard.pid; \
	fi
	@echo "🔴 Stopped."

restart-local: stop-local run-local ## Restart local background processes