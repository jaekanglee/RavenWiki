"""v0.7.4+ — Makefile HOST 변수 (Tailscale) 회귀 가드.

사용자 (2026-06-30):
  '테일스케일로 접속가능하도록 띄워줬었는데 왜 안되지'

v0.7.4 정책:
  - HOST 변수 도입 (기본 127.0.0.1, Tailscale = 0.0.0.0)
  - API bind 옵션 (Tailscale IP로 접속 가능)

v0.7.13+ 정책:
  - 로컬 host 실행 = deprecated (Docker 우선)
  - HOST 변수는 .env.example로 이동 (Docker compose용)
  - Makefile에는 HOST 변수가 더 이상 없음 (Docker compose가 처리)

회귀 가드 (v0.7.4):
  1. .env.example = HOST=0.0.0.0 (Tailscale/원격 접속)
  2. .env.example = RAVEN_VAULTS_DIR = 호스트 외부 경로
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"


def test_env_example_has_host_variable() -> None:
    """.env.example = HOST=0.0.0.0 (Tailscale/원격)."""
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "HOST=0.0.0.0" in content, \
        ".env.example must have HOST=0.0.0.0 for Tailscale/원격 접속"


def test_env_example_has_vault_path() -> None:
    """.env.example = RAVEN_VAULTS_DIR = 호스트 외부 경로 ~/Raven."""
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "RAVEN_VAULTS_DIR=" in content, \
        ".env.example must have RAVEN_VAULTS_DIR (호스트 외부 vault 경로)"