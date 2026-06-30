# Raven Dockerfile — multi-vault wiki engine + CLI + API + Dashboard + MCP
# v0.7.12+ — Docker 셋업 (사용자: 다른 PC 환경에서도 동일하게)
#
# 전략: 두 stage 빌드
#   stage 1: dashboard build (Node 20) → 정적 산출물
#   stage 2: runtime (Python 3.11-slim + 정적 dashboard + FastAPI/uvicorn)
#
# 4 진입점 (모두 background):
#   - CLI:  on-demand (docker exec)
#   - API:  :8765 (HTTP)
#   - MCP:  :8766 (HTTP transport) + stdio (docker exec)
#   - UI:   :5173 (Vite preview, 정적 빌드 서빙)

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

# Python deps 먼저 복사 (cache)
COPY pyproject.toml ./
COPY scripts/ ./scripts/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

# Dashboard 정적 빌드 (stage 1에서) 복사
COPY --from=dashboard-build /app/dashboard/dist ./dashboard/dist

# Raven 코드 (CLI / API / MCP / core)
COPY raven/ ./raven/
COPY dashboard/public ./dashboard/public
COPY dashboard/index.html ./dashboard/

# 환경변수 기본값 (.env로 override 가능)
ENV HOST=0.0.0.0 \
    PORT_API=8765 \
    PORT_MCP_HTTP=8766 \
    PORT_DASHBOARD=5173 \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Default vault 위치 (volume mount로 override)
ENV RAVEN_VAULTS_DIR=/vaults

USER raven

# 포트 노출 (compose가 실제 매핑)
EXPOSE 8765 8766 5173

# Health check — API 서버가 살아있는지 curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8765/api/vaults || exit 1

# Entrypoint: scripts/docker-entrypoint.sh
COPY scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["api"]  # 기본 = API 시작. 다른 진입점은 환경변수로 전환.
