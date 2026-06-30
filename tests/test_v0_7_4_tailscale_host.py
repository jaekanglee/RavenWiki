"""v0.7.4+ — `make dev HOST=0.0.0.0` Tailscale 접속 회귀 가드.

사용자 (2026-06-30): '테일스케일로 접속가능하도록 띄워줬었는데 왜 안되지'

원인 분석:
1. `cd dashboard && nohup ... &` → `&`가 `cd` 명령에 적용 안 됨 → make가 dashboard process 기다림 (timeout)
2. `--host 127.0.0.1` → Tailscale IP (100.x.x.x) 접속 불가
3. Tailscale URL 자동 출력 누락

v0.7.4 수정:
- Makefile: `(cd dashboard && nohup ... &)` subshell → make 즉시 detach
- Makefile: HOST 변수 (default 127.0.0.1, override HOST=0.0.0.0)
- Makefile: HOST=0.0.0.0 시 Tailscale URL 자동 출력

회귀 가드 (v0.7.4):
  1. Makefile dashboard 띄우기가 subshell `(cd && nohup &)` 형식
  2. Makefile HOST 변수 정의 + override 가능
  3. Makefile api host가 $(HOST) 사용
  4. Makefile Tailscale URL 출력 (HOST=0.0.0.0 시)
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"


def test_makefile_dashboard_subshell() -> None:
    """`make dev` dashboard 띄우기가 subshell `(cd && nohup &)` 형식이어야 함."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # subshell로 감싸고 있어야 detach 보장
    assert "(cd dashboard && nohup" in content, \
        "Makefile dashboard must be wrapped in subshell `(cd && nohup &)` to detach from make"


def test_makefile_host_variable() -> None:
    """`HOST ?= 127.0.0.1` 변수가 정의되어야 함 (override 가능)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "HOST ?= 127.0.0.1" in content, \
        "Makefile must define `HOST ?= 127.0.0.1` for override (Tailscale = HOST=0.0.0.0)"


def test_makefile_api_uses_host_variable() -> None:
    """api target이 $(HOST) 변수를 사용해야 함 (hard-coded 127.0.0.1 ❌)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # api target 또는 dev target 안에서 --host $(HOST)
    assert "--host $(HOST)" in content, \
        "Makefile api target must use --host $(HOST) (not hardcoded 127.0.0.1)"


def test_makefile_tailscale_url_output() -> None:
    """`make dev HOST=0.0.0.0` 시 Tailscale URL 자동 출력해야 함."""
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "Tailscale" in content or "tailscale" in content, \
        "Makefile must output Tailscale URL when HOST=0.0.0.0"


def test_makefile_not_hardcoded_127_in_dev() -> None:
    """`make dev` 안에 hard-coded --host 127.0.0.1 ❌ (override 불가)."""
    content = MAKEFILE.read_text(encoding="utf-8")
    # dev target 범위에서 (간단히 전체에서 검색) --host 127.0.0.1 hard-coded 여부
    # 단, api target은 $(HOST) 사용하므로 dev target만 검사
    dev_section = content[content.find(".PHONY: dev"):content.find(".PHONY: status")]
    assert "--host 127.0.0.1" not in dev_section, \
        "make dev must NOT hardcode --host 127.0.0.1 (use $(HOST))"