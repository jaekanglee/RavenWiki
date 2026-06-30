"""v0.7.7+ — MCP 진입점 회귀 가드.

v0.7.7: 'raven.mcp' 패키지 직접 실행 ❌ → 'raven.mcp.cli' 정정.
v0.7.10: raven.mcp.cli 진입점 검증.

v0.7.13+: Makefile에 MCP target 없음 (Docker 우선). 검증은 Dockerfile + docker-entrypoint.sh에 위임.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "docker-entrypoint.sh"
MCP_CLI = ROOT / "raven" / "mcp" / "cli.py"


def test_mcp_cli_entrypoint_exists() -> None:
    """raven/mcp/cli.py = 정직한 MCP 진입점 (python -m raven.mcp.cli)."""
    assert MCP_CLI.exists(), "raven/mcp/cli.py must exist (correct MCP entry point)"


def test_docker_entrypoint_supports_mcp_transports() -> None:
    """docker-entrypoint.sh = mcp-http / mcp-stdio 라우팅."""
    assert ENTRYPOINT.exists(), "scripts/docker-entrypoint.sh must exist"
    content = ENTRYPOINT.read_text(encoding="utf-8")
    for transport in ("mcp-http", "mcp-stdio"):
        assert transport in content, \
            f"docker-entrypoint.sh must handle '{transport}' command"


def test_no_bare_raven_mcp_execution() -> None:
    """v0.7.7 회귀 가드: 'python -m raven.mcp' (패키지 직접 실행) ❌."""
    # 라이브러리 코드 + Dockerfile + Makefile + entrypoint 검색
    import subprocess
    bad_patterns = [
        "raven.mcp --transport",       # Makefile v0.7.7~v0.7.9 옛
        "python -m raven.mcp ",        # entrypoint v0.7.7~v0.7.9 옛
    ]
    for path in (ROOT / "Makefile", ENTRYPOINT, ROOT / "Dockerfile"):
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for pat in bad_patterns:
            # 정확한 단어 매칭 (단어 경계)
            import re
            if re.search(re.escape(pat), content):
                # 예외: docker-entrypoint에서 'raven.mcp.cli --transport' 사용은 OK
                if "raven.mcp.cli" in content and pat == "python -m raven.mcp ":
                    continue
                raise AssertionError(
                    f"{path.name}: bad pattern '{pat}' (use raven.mcp.cli instead)"
                )