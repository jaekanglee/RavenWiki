"""v0.7.14+ — Docker 컨테이너 down/up 시 vault 데이터 영속성 보장 회귀 가드.

사용자 (2026-06-30):
  '도커 내렸다 올렸다 한다고 db나 문서들 초기화되면 안된다'

v0.7.14 정책:
  - bind mount (${RAVEN_VAULTS_DIR}:/vaults) — 호스트 외부 경로 직접 연결
  - 컨테이너 down/up 시 vault 데이터 보존 (wiki.db, .vault.json, content/ 등)
  - 다른 PC에서도 호스트의 동일 경로 mount = 동일하게 동작

영속 대상 (모두 vault 안):
  - content/      — 사용자 마크다운
  - .vault.json   — vault 메타
  - wiki.db       — sqlite 인덱스 (regenerable)
  - .mcp/         — MCP runtime state
  - backups/      — 백업
  - logs/         — 서비스 로그

회귀 가드 (v0.7.14):
  1. docker-compose.yml = bind mount ${RAVEN_VAULTS_DIR}:/vaults (api 서비스)
  2. docker-compose.yml = bind mount ${RAVEN_VAULTS_DIR}:/vaults (mcp-http 서비스)
  3. .env.example = RAVEN_VAULTS_DIR = 호스트 외부 경로
  4. 옛 vault-data Docker volume ❌ (bind mount와 충돌, 데이터 loss 위험)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE_HOUSE = ROOT / ".env.example.house"
ENV_EXAMPLE_COMPANY = ROOT / ".env.example.company"


def test_api_service_uses_bind_mount() -> None:
    """api 서비스 = bind mount ${RAVEN_VAULTS_DIR}:/vaults (영속성)."""
    content = COMPOSE.read_text(encoding="utf-8")
    # api 서비스 안에 bind mount 박힘
    api_section = _extract_service_section(content, "api")
    assert "${RAVEN_VAULTS_DIR}:/vaults" in api_section, \
        "api service must bind mount ${RAVEN_VAULTS_DIR}:/vaults for persistence"


def test_mcp_service_uses_bind_mount() -> None:
    """mcp-http 서비스 = bind mount (api와 동일, 영속성)."""
    content = COMPOSE.read_text(encoding="utf-8")
    mcp_section = _extract_service_section(content, "mcp-http")
    assert "${RAVEN_VAULTS_DIR}:/vaults" in mcp_section, \
        "mcp-http service must bind mount ${RAVEN_VAULTS_DIR}:/vaults for persistence"


def test_env_example_default_vault_path() -> None:
    """.env.example.* = RAVEN_VAULTS_DIR = 호스트 외부 경로 (사용자 vault 위치)."""
    for path in (ENV_EXAMPLE_HOUSE, ENV_EXAMPLE_COMPANY):
        content = path.read_text(encoding="utf-8")
        assert "/Users/jaekanglee/Raven" in content or "${HOME}/Raven" in content, \
            f"{path.name} must default to ~/Raven (외부 vault 경로)"


def test_no_named_docker_volume() -> None:
    """v0.7.12+: 옛 'vault-data' Docker named volume ❌ (bind mount로 대체).

    named volume은 docker compose down -v 시 데이터 손실. bind mount는 안전.
    """
    content = COMPOSE.read_text(encoding="utf-8")
    # named volume 'vault-data' 정의 ❌
    assert "vault-data:" not in content or \
           "named volume" not in content.lower(), \
        "v0.7.14+: 'vault-data' named Docker volume must NOT exist (use bind mount)"
    # top-level volumes 정의 ❌ (named volume 없음)
    top_volumes_match = "volumes:\n  vault-data:" in content
    assert not top_volumes_match, \
        "v0.7.14+: top-level 'volumes: vault-data:' block must be removed"


def test_persistence_comment_in_compose() -> None:
    """docker-compose.yml = vault 영속성 주석 명시."""
    content = COMPOSE.read_text(encoding="utf-8")
    assert "영속" in content or "persistence" in content.lower() or \
           "bind mount" in content.lower(), \
        "docker-compose.yml must explain vault persistence (bind mount)"


def _extract_service_section(content: str, service_name: str) -> str:
    """YAML에서 특정 service의 section 추출 (간단한 파서)."""
    lines = content.splitlines()
    in_section = False
    section_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{service_name}:"):
            in_section = True
            continue
        if in_section:
            # 다음 service 시작 또는 top-level 키 (volumes/networks)
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                if ":" in line and not stripped.startswith("-"):
                    break
            section_lines.append(line)
    return "\n".join(section_lines)