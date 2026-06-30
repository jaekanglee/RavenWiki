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

# v0.7.3+: Tailscale 등 원격 접속을 위한 host bind.
# HOST=0.0.0.0 → 모든 인터페이스 (Tailscale 포함). HOST=127.0.0.1 → 로컬만.
# 사용 예: make dev HOST=0.0.0.0
HOST ?= 127.0.0.1

.PHONY: api
api: venv-check ## Run raven API (default: 127.0.0.1:8765, override: HOST=0.0.0.0 for Tailscale)
	PYTHONPATH=. $(PY) -m raven.api --host $(HOST) --port 8765

.PHONY: dashboard
dashboard: ## Run vite dev on localhost:5173 (foreground, Ctrl+C to stop)
	cd dashboard && npm run dev

.PHONY: stop-dev
stop-dev: ## Kill existing dev servers on dynamic PIDs (API + Vite + MCP, best-effort)
	@pids="$$( { \
		lsof -ti :8765 -ti :5173 -ti :5174 2>/dev/null; \
		ps -ef | awk '/[r]aven\.api|[r]aven\.mcp|[n]ode .*\/vite|[v]ite( |$$)/ {print $$2}'; \
	} | sort -u )"; \
	if [ -n "$$pids" ]; then \
		echo "🧹 stopping existing dev servers: $$pids"; \
		kill $$pids 2>/dev/null || true; \
		sleep 1; \
		for pid in $$pids; do \
			if kill -0 $$pid 2>/dev/null; then kill -9 $$pid 2>/dev/null || true; fi; \
		done; \
	else \
		echo "✅ no existing dev servers"; \
	fi

.PHONY: dev
dev: venv-check ## Run product-ready dev stack: CLI + API + Dashboard + MCP (one command = production prep)
	@$(MAKE) --no-print-directory stop-dev
	@echo ""
	@echo "🚀 Raven product-ready dev stack"
	@echo "   (one command → 4 진입점 ready for production prep)"
	@echo ""
	@echo "🔌 starting API in background (detached from this shell)..."
	@nohup env PYTHONPATH=. $(PY) -m raven.api --host $(HOST) --port 8765 >/tmp/raven-api.log 2>&1 </dev/null &
	@for i in 1 2 3 4 5; do \
		sleep 1; \
		if lsof -ti :8765 >/dev/null 2>&1; then \
			echo "✅ API ready on http://$(HOST):8765 (pid $$(lsof -ti :8765 | head -1))"; \
			break; \
		fi; \
		if [ $$i -eq 5 ]; then \
			echo "❌ API failed to start — see /tmp/raven-api.log"; exit 1; \
		fi; \
	done
	@echo ""
	@echo "🔌 starting MCP in background (stdio transport, default vault)..."
	@nohup env PYTHONPATH=. $(PY) -m raven.mcp >/tmp/raven-mcp.log 2>&1 </dev/null &
	@sleep 1
	@echo "✅ MCP ready (pid $$(pgrep -f 'raven.mcp' | head -1), logs: /tmp/raven-mcp.log)"
	@echo ""
	@echo "🌐 starting Dashboard in background (detached)..."
	@(cd dashboard && nohup npm run dev >/tmp/raven-dashboard.log 2>&1 </dev/null &)
	@for i in 1 2 3 4 5; do \
		sleep 1; \
		if lsof -ti :5173 >/dev/null 2>&1 || lsof -ti :5174 >/dev/null 2>&1; then \
			port=$$(lsof -ti :5173 >/dev/null 2>&1 && echo 5173 || echo 5174); \
			echo "✅ Dashboard ready on http://localhost:$$port (pid $$(lsof -ti :$$port | head -1))"; \
			break; \
		fi; \
		if [ $$i -eq 5 ]; then \
			echo "❌ Dashboard failed to start — see /tmp/raven-dashboard.log"; \
		fi; \
	done
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🟢 4 진입점 ready:"
	@echo "   • CLI    → make raven ARGS=\"vault list\"  (또는 scripts/.venv/bin/python -m raven.cli)"
	@echo "   • API    → http://$(HOST):8765         (POST /api/vaults/{n}/pages)"
	@echo "   • MCP    → stdio (default vault)         (logs: /tmp/raven-mcp.log)"
	@echo "   • UI     → http://localhost:5173         (또는 :5174)"
	@echo ""
	@if [ "$(HOST)" = "0.0.0.0" ]; then \
		echo "🔗 Tailscale/원격 접속: http://$(shell tailscale ip -4 2>/dev/null | head -1):8765"; \
	fi
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🛑 stop: make stop  |  status: make status  |  logs: tail -f /tmp/raven-{api,mcp,dashboard}.log"

.PHONY: status
status: ## Show whether API (8765), Dashboard (5173), MCP (stdio) are running
	@echo "API (8765):"
	@lsof -i :8765 2>/dev/null | tail -n +2 || echo "  (not listening)"
	@echo "Dashboard (5173):"
	@lsof -i :5173 2>/dev/null | tail -n +2 || echo "  (not listening)"
	@echo "MCP (stdio):"
	@pid=$$(pgrep -f 'raven.mcp' | head -1); \
	if [ -n "$$pid" ]; then echo "  pid: $$pid (logs: /tmp/raven-mcp.log)"; else echo "  (not running)"; fi
	@echo ""
	@echo "Tip: make dev = CLI + API + Dashboard + MCP 4 진입점 ready (v0.7.3+)"

.PHONY: stop
stop: ## Kill any running API / dashboard / MCP processes (best-effort, never kills this make wrapper)
	@$(MAKE) --no-print-directory stop-dev
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
