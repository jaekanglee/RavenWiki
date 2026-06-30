"""v0.7.15+ — Docker 셋업 사용성 회귀 가드.

사용자 (2026-06-30):
  'make docker-up 했더니 invalid spec: :/vaults (empty section between colons)'
  '왜 이래?'

v0.7.15 정책:
  - make docker-up = .env 부재 시 자동 복사 (make docker-build와 동일)
  - 사용자가 .env 만들 필요 ❌ (docker-build를 안 거쳤어도 docker-up 가능)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"


def _extract_target_body(content: str, target_name: str) -> str:
    """Makefile에서 target 본문 추출 (간단한 라인 기반 파서)."""
    lines = content.splitlines()
    in_target = False
    body_lines = []
    for line in lines:
        if line.startswith(f"{target_name}:"):
            in_target = True
            continue
        if in_target:
            # 빈 줄 또는 다음 target 시작 → 종료
            if line.strip() == "" and body_lines:
                # body_lines 비어있지 않으면 빈 줄에서 끊기
                if len(body_lines) > 0 and not body_lines[-1].startswith("\t"):
                    break
            # 다음 target (들여쓰기 없음)
            if line and not line.startswith("\t") and not line.startswith(" "):
                if ":" in line and not line.startswith("#"):
                    break
            body_lines.append(line)
    return "\n".join(body_lines)


def test_makefile_docker_up_creates_env() -> None:
    """v0.7.15+: make docker-up = .env 부재 시 자동 cp .env.example .env."""
    content = MAKEFILE.read_text(encoding="utf-8")
    body = _extract_target_body(content, "docker-up")
    assert ".env.example" in body, \
        "docker-up must auto-create .env from .env.example (v0.7.15+)"
    assert "test -f .env" in body or "[ ! -f .env ]" in body or "if [ ! -f" in body, \
        "docker-up must check .env existence first"


def test_makefile_docker_build_creates_env() -> None:
    """v0.7.12+: make docker-build = .env 부재 시 자동 cp .env.example .env."""
    content = MAKEFILE.read_text(encoding="utf-8")
    body = _extract_target_body(content, "docker-build")
    assert ".env.example" in body, \
        "docker-build must auto-create .env from .env.example"
    assert "test -f .env" in body or "[ ! -f .env ]" in body or "if [ ! -f" in body, \
        "docker-build must check .env existence first"