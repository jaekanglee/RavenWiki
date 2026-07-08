#!/bin/bash
# cron-cleanser.sh — 주기적 Raven 볼트 큐레이션 및 린트 취합 스크립트
#
# Usage: ./cron-cleanser.sh [vault_name]

set -e

# 기본 경로 설정
RAVEN_DIR="/Users/jaekanglee/Dev/Project/Raven"
VAULT_NAME="${1:-default}"

echo "[$(date)] Raven Cron Cleanser 시작 (Vault: ${VAULT_NAME})"

# 1. Raven 환경 체크 및 빌드
cd "${RAVEN_DIR}"
PYTHON_BIN="python3"
if [ -f "scripts/.venv/bin/python3" ]; then
    PYTHON_BIN="scripts/.venv/bin/python3"
fi

echo "[$(date)] 1. 볼트 빌드 및 린트 결과 수집..."
"${PYTHON_BIN}" -m raven.cli build --vault "${VAULT_NAME}" --lint || true

# 2. 린트 이슈 스캔 및 에이전트 해결용 이슈 발행
echo "[$(date)] 2. 린트 이슈 스캔 및 에이전트 해결용 이슈 발행..."
PYTHONPATH=. "${PYTHON_BIN}" scripts/cron-cleanser.py "${VAULT_NAME}"

# 3. 정적 파일 갱신
echo "[$(date)] 3. 대시보드용 정적 JSON 익스포트..."
"${PYTHON_BIN}" -m raven.cli export --vault "${VAULT_NAME}"

echo "[$(date)] Raven Cron Cleanser 완료!"
