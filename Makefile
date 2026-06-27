# raven — top-level Makefile
# Self-documenting: `make` or `make help` lists targets.
#
# Conventions:
#   - All commands run from project root.
#   - Venv is scripts/.venv (auto-created by `make install`).
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
install: ## Create venv + install raven + dev deps
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e .
	$(PIP) install --quiet pytest typer fastapi uvicorn 'httpx<0.28' pydantic python-frontmatter
	@echo "✅ installed ($(VENV))"

.PHONY: venv-check
venv-check: ## Fail loudly if venv missing (so other targets work)
	@test -d $(VENV) || (echo "❌ run 'make install' first"; exit 1)

# ────────────────────────── dev (api + dashboard) ──────────────────────────

.PHONY: api
api: venv-check ## Run raven API on 127.0.0.1:8765 (foreground, Ctrl+C to stop)
	PYTHONPATH=. $(PY) -m raven.api --host 127.0.0.1 --port 8765

.PHONY: dashboard
dashboard: ## Run vite dev on localhost:5173 (foreground, Ctrl+C to stop)
	cd dashboard && npm run dev

.PHONY: dev
dev: venv-check ## Run API + dashboard (reuses running API; Ctrl+C stops only dashboard)
	@echo "🚀 raven API → http://127.0.0.1:8765"
	@echo "🌐 dashboard  → http://localhost:5173/"
	@echo "   (Ctrl+C stops dashboard. API is shared — \`make stop\` to kill it.)"
	@echo ""
	@if lsof -ti :8765 >/dev/null 2>&1; then \
	    echo "✅ API already running on 8765 — reusing"; \
	else \
	    echo "🔌 starting API in background (detached from this shell)..."; \
	    nohup env PYTHONPATH=. $(PY) -m raven.api --host 127.0.0.1 --port 8765 >/tmp/raven-api.log 2>&1 </dev/null & \
	    disown 2>/dev/null || true; \
	    for i in 1 2 3 4 5; do \
	        sleep 1; \
	        if lsof -ti :8765 >/dev/null 2>&1; then \
	            echo "✅ API ready (pid $$(lsof -ti :8765 | head -1))"; \
	            break; \
	        fi; \
	        if [ $$i -eq 5 ]; then \
	            echo "❌ API failed to start — see /tmp/raven-api.log"; exit 1; \
	        fi; \
	    done; \
	fi
	@echo ""
	cd dashboard && npm run dev

.PHONY: status
status: ## Show whether API (8765) and dashboard (5173) are running
	@echo "API (8765):"
	@lsof -i :8765 2>/dev/null | tail -n +2 || echo "  (not listening)"
	@echo "Dashboard (5173):"
	@lsof -i :5173 2>/dev/null | tail -n +2 || echo "  (not listening)"

.PHONY: stop
stop: ## Kill any running API / dashboard processes (best-effort)
	@lsof -ti :8765 2>/dev/null | xargs -r kill 2>/dev/null || true
	@lsof -ti :5173 2>/dev/null | xargs -r kill 2>/dev/null || true
	@echo "✅ stopped (best-effort)"

# ────────────────────────── test ──────────────────────────

.PHONY: test
test: venv-check ## Run all tests
	$(PY) -m pytest tests/ -v

.PHONY: test-quick
test-quick: venv-check ## Run tests with minimal output
	$(PY) -m pytest tests/ -q

.PHONY: test-one
test-one: venv-check ## Run a single test file (usage: make test-one F=tests/test_slug.py)
	$(PY) -m pytest $(F) -v

# ────────────────────────── raven cli shortcuts ──────────────────────────

WIKI := PYTHONPATH=. $(PY) -m raven.cli

.PHONY: raven
raven: venv-check ## Run raven CLI (usage: make raven ARGS="vault list")
	$(WIKI) $(ARGS)

.PHONY: vault-list
vault-list: venv-check ## Show registered vaults
	$(WIKI) vault list

.PHONY: where
where: venv-check ## Show raven config (vaults root, active vault)
	$(WIKI) where

.PHONY: link-check
link-check: venv-check ## Check wikilinks in default vault (override: make link-check V=default)
	$(WIKI) link check --vault $(or $(V),default)

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
