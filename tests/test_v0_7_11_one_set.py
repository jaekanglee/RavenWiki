"""v0.7.7+ — Makefile 회귀 가드 (Docker 우선 정책, v0.7.13+).

사용자 (2026-06-30):
  '도커로만 올리고내릴거니까 나머지 dev이런거 기존레거시는 make스크립트 청상해'

v0.7.13 정책:
  - Makefile = docker-* / install / test / clean / nuke / help 만 (단순)
  - 옛 dev/status/stop/mcp/api/dashboard target 제거
  - 로컬 host 실행 = deprecated (Docker compose로 통일)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"


def test_makefile_has_docker_targets() -> None:
    """v0.7.13+: docker-build/up/down/logs/ps target 존재."""
    content = MAKEFILE.read_text(encoding="utf-8")
    for target in ("docker-build", "docker-up", "docker-down", "docker-logs", "docker-ps"):
        assert target in content, f"Makefile missing {target}"


def test_makefile_legacy_removed() -> None:
    """v0.7.13+: 옛 dev/status/stop/mcp/api/dashboard target ❌ (Docker 우선)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # .PHONY 라인들 파싱
    phony_lines = [
        line.strip() for line in content.splitlines() if line.strip().startswith(".PHONY:")
    ]
    phony_targets = set()
    for line in phony_lines:
        for tok in line.replace(".PHONY:", "").strip().split():
            phony_targets.add(tok)
    # 레거시 target 검증 (대상 목록)
    legacy_targets = ["api", "mcp", "dashboard", "stop-dev", "stop", "status"]
    for legacy in legacy_targets:
        assert legacy not in phony_targets, (
            f"Makefile legacy target '{legacy}' must be REMOVED (Docker 우선, v0.7.13+)"
        )


def test_makefile_no_dev_target() -> None:
    """v0.7.13+: 'dev' target ❌ (Docker 우선, deprecated)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # '.PHONY: dev' 단독 라인 검증 (.PHONY: dev '공백' 분리 패턴)
    assert ".PHONY: dev" not in content or ".PHONY: dev " in content, (
        "Makefile must NOT have standalone '.PHONY: dev' (Docker 우선)"
    )
    # 더 정확하게: dev가 단독 target이 아니어야 함
    phony_lines = [
        line.strip() for line in content.splitlines() if line.strip().startswith(".PHONY:")
    ]
    dev_in_phony = any(
        "dev" in line.replace(".PHONY:", "").strip().split()
        and "docker-" not in line  # docker-dev 변형 가능
        for line in phony_lines
    )
    assert not dev_in_phony, "Makefile must NOT have standalone 'dev' target"


def test_makefile_has_install_and_test() -> None:
    """v0.7.13+: install/test/clean/nuke target 유지 (로컬 fallback)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    for target in ("install", "test", "clean", "nuke"):
        assert target in content, f"Makefile missing {target}"