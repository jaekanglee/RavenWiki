# Raven Dockerfile — multi-vault wiki engine + CLI + API + Dashboard + MCP
# v0.7.17+ — 빌드 단순화 (editable install ❌, 의존성 직접 install)
#
# 전략: 두 stage 빌드
#   stage 1: dashboard build (Node 20) → 정적 산출물
#   stage 2: runtime (Python 3.11-slim + 정적 dashboard)
#
# 4 진입점 (모두 background):
#   - CLI:  on-demand (docker exec)
#   - API:  :8765 (HTTP)
#   - MCP:  :8766 (HTTP transport) + stdio (docker exec)
#   - UI:   :5173 (정적 http.server)

# ──────────────────────────────────────────────────────────────────────
# Stage 1: Dashboard build (Node 20)
# ──────────────────────────────────────────────────────────────────────
FROM node:20-slim AS dashboard-build

WORKDIR /app/dashboard

COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY dashboard/ ./
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# ──────────────────────────────────────────────────────────────────────
# Stage 2: Runtime (Python 3.11-slim)
# ──────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# systemd-less: 의존성 최소화
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

# 비대자 user (security best practice)
RUN useradd --create-home --uid 1000 --shell /bin/bash raven

WORKDIR /app

# v0.7.17+: editable install ❌ (scripts/pyproject.toml 의존성 build fail).
# → 의존성을 Dockerfile에 직접 박아 install (단순, 결정적).
# → 본체 raven 패키지는 PYTHONPATH=/app + entrypoint로 직접 실행.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        'python-frontmatter>=1.1.0' \
        'mcp[cli]>=1.0' \
        'fastapi>=0.100' \
        'uvicorn[standard]>=0.20' \
        'pydantic>=2.0' \
        'typer>=0.9' \
        'pytest>=7.0' \
        'httpx<0.28' \
        'starlette>=0.30'

# Dashboard 정적 빌드 (stage 1에서) 복사
COPY --from=dashboard-build /app/dashboard/dist ./dashboard/dist

# Raven 코드 (CLI / API / MCP / core)
# v0.7.17+: USER raven 전환 후에도 파일 읽기 가능하도록 --chown 사용
COPY --chown=raven:raven raven/ ./raven/
COPY --chown=raven:raven dashboard/public ./dashboard/public
COPY --chown=raven:raven dashboard/index.html ./dashboard/
COPY --chown=raven:raven scripts/docker-entrypoint.sh /usr/local/bin/
COPY --chown=raven:raven scripts/spa_server.py /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh /usr/local/bin/spa_server.py

# 환경변수 기본값 (.env로 override 가능)
ENV HOST=0.0.0.0 \
    PORT_API=8765 \
    PORT_MCP_HTTP=8766 \
    PORT_DASHBOARD=5173 \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

ENV RAVEN_VAULTS_DIR=/vaults

USER raven

# 포트 노출 (compose가 실제 매핑)
EXPOSE 8765 8766 5173

# Health check — API 서버가 살아있는지 curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8765/api/vaults || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["api"]  # 기본 = API 시작. 다른 진입점은 환경변수로 전환.