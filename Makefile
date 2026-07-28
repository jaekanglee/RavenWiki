# raven — top-level Makefile
# v0.7.55+ — Docker deprecated. 기본은 local host stack (raven.sh / restart-all.sh).
# Self-documenting: `make` or `make help` lists targets.
#
# Conventions:
#   - All commands run from project root.
#   - 로컬 host 실행 (기본): make install && ./raven.sh start
#   - Docker (deprecated, 남겨두지만 신규 사용자는 비권장): cp .env.example.house .env && make docker-up
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
install: ## Create venv + install raven + dev deps (v0.7.55+ 기본 경로 — Docker는 deprecated)
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e ./scripts
	$(PIP) install --quiet pytest typer fastapi uvicorn 'httpx<0.28' pydantic python-frontmatter 'mcp[cli]>=1.0' 'starlette>=0.30'
	@echo "✅ installed ($(VENV))"

.PHONY: venv-check
venv-check: ## Fail loudly if venv missing (so other targets work)
	@test -d $(VENV) || (echo "❌ run 'make install' first"; exit 1)

# ────────────────────────── Docker (v0.7.55+ deprecated) ──────────────────────
# v0.7.12~54: Docker compose 표준이었음. v0.7.55+: local host stack(./raven.sh,
# scripts/restart-all.sh)이 기본으로 전환됨 — 아래 target들은 하위 호환/레거시
# 용도로 남겨두지만 신규 사용자는 `./raven.sh start`를 사용할 것.

.PHONY: docker-build docker-up docker-down docker-logs docker-ps
docker-build: ## Build Raven Docker image (multi-stage: dashboard + Python runtime)
	@if [ ! -f .env ]; then \
		echo "📋 .env 없음. .env.example.house → .env 복사. RAVEN_VAULTS_DIR 조정 후 사용."; \
		cp .env.example.house .env; \
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
		echo "📋 .env 없음. .env.example.house → .env 복사. RAVEN_VAULTS_DIR 조정 후 사용."; \
		cp .env.example.house .env; \
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

.PHONY: typecheck
typecheck: ## Typecheck the dashboard (v0.7.67: AGENTS.md §6 referenced this before it existed)
	cd dashboard && npx tsc -b --noEmit

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

.PHONY: up down restart status
up: venv-check ## Start Raven locally in the background (API + Dashboard dev server)
	@./raven.sh start

down: ## Stop local background processes (API + Dashboard)
	@./raven.sh stop

restart: ## Restart local background processes
	@./raven.sh restart

status: ## Show status of local background processes
	@./raven.sh status

.PHONY: docker-restart rebuild restart-all
docker-restart: docker-down docker-up ## Restart Raven via Docker compose
rebuild: docker-build docker-restart ## Rebuild Docker images and restart Docker containers
# v0.7.60+: Docker 무관. local host stack (./raven.sh)을 완전히 내리고
#           모든 캐시(Vite pre-bundle / python __pycache__ / pytest / 구 로그)를
#           비운 뒤 재시작. 디자인 시스템 토큰, CSS, node_modules 의존성 변경
#           후 UI가 stale하게 갱신 안 될 때 사용. 기본 재시작은 `make restart`.
restart-all: ## Full local restart: wipe caches (Vite/__pycache__/pytest/logs) + restart
	@bash scripts/restart-all.sh

# ────────────────────────── desktop ──────────────────────────

.PHONY: desktop-dev desktop-rebuild desktop-bundle desktop-build desktop-dmg desktop-release

desktop-dev: desktop-bundle-check ## Run desktop app in dev mode with live reload
	cd dashboard && npm run desktop:dev

desktop-bundle-check: ## Ensure desktop bundle resources exist
	@if [ ! -d desktop/src-tauri/resources/raven ] || [ ! -d desktop/src-tauri/resources/python ]; then \
		echo "📦 번들 자원(desktop/src-tauri/resources)이 준비되어 있지 않아 prepare-bundle.sh를 먼저 실행합니다..."; \
		$(MAKE) desktop-bundle; \
	fi

desktop-rebuild: desktop-build ## Rebuild desktop app (.app binary) from latest source
	@echo "✅ Rebuilt desktop app: desktop/src-tauri/target/release/raven-desktop"

desktop-bundle: ## Prepare bundled Python + Raven source for Tauri .app
	@bash scripts/prepare-bundle.sh

desktop-build: desktop-bundle ## Build Tauri desktop app (release binary + .app)
	cd dashboard && npm ci && npm run build
	cd desktop/src-tauri && cargo build --release
	@echo "✅ Binary: desktop/src-tauri/target/release/raven-desktop"

desktop-dmg: desktop-build ## Build DMG installer from release binary
	@bash scripts/make-dmg.sh
	@echo "✅ DMG: desktop/src-tauri/target/release/bundle/dmg/Raven_0.1.0_aarch64.dmg"

desktop-release: desktop-dmg ## Build DMG + signed auto-update artifact, upload both to GitHub Release (requires gh CLI + TAURI_SIGNING_PRIVATE_KEY)
	@TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.1.0"); \
	VERSION=$${TAG#v}; \
	DMG="desktop/src-tauri/target/release/bundle/dmg/Raven_0.1.0_aarch64.dmg"; \
	bash scripts/sign-update.sh "$$VERSION" "jaekanglee/RavenWiki"; \
	ARTIFACT="desktop/src-tauri/target/release/bundle/updater/Raven.app.tar.gz"; \
	MANIFEST="desktop/src-tauri/target/release/bundle/updater/latest.json"; \
	echo "📦 Uploading $$DMG + $$ARTIFACT + $$MANIFEST to release $$TAG ..."; \
	gh release upload "$$TAG" "$$DMG" "$$ARTIFACT" "$$MANIFEST" --clobber; \
	echo "✅ Release $$TAG updated (auto-update manifest included)"
# ────────────────────────── mobile ──────────────────────────

.PHONY: deploy-dev deploy-prod

deploy-dev: ## Deploy mobile Dev build via Fastlane
	cd mobile && bundle exec fastlane distribute_dev

deploy-prod: ## Deploy mobile Prod build via Fastlane
	cd mobile && bundle exec fastlane distribute_prod

desktop-install: ## Rebuild from current source and (re)install Raven.app to /Applications (no clone/pull)
	@bash scripts/install-desktop.sh
