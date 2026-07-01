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


def test_mcp_http_entrypoint_only_known_flags() -> None:
    """v0.7.36 회귀 가드: docker-entrypoint.sh mcp-http 분기의
    실제 exec 라인(raven.mcp.cli 호출)이 wiki-mcp가 인식 못하는 옵션을
    던지지 않아야 함. Typer가 모르는 옵션 → exit 2 → container Restarting.

    uvicorn 옵션(`forwarded_allow_ips=`, `proxy_headers=`,
    `TrustedHostMiddleware`)은 raven/mcp/cli.py가 내부에서 박아 호출함 (v0.7.23+).
    """
    content = ENTRYPOINT.read_text(encoding="utf-8")

    # mcp-http 분기 안에서 실제 raven.mcp.cli를 호출하는 exec 라인 추출
    exec_lines = [
        line.strip()
        for line in content.splitlines()
        if "raven.mcp.cli" in line and line.strip().startswith("exec")
    ]
    assert exec_lines, (
        "docker-entrypoint.sh mcp-http branch must exec `python -m raven.mcp.cli`"
    )

    forbidden = (
        "--forwarded-allow-ips",
        "--proxy-headers",
        "--forwarded_allow_ips",   # Typer는 underscores 안 받음
        "--proxy_headers",
    )
    for exec_line in exec_lines:
        for flag in forbidden:
            assert flag not in exec_line, (
                f"docker-entrypoint.sh mcp-http exec line must NOT pass {flag!r} "
                f"to wiki-mcp — Typer doesn't recognize it (cli.py already "
                f"sets these uvicorn options internally).\n"
                f"  offending line: {exec_line}"
            )

    # 그리고 cli.py 자체에 인식 가능한 uvicorn 옵션이 박혀 있는지 sanity check
    cli_content = MCP_CLI.read_text(encoding="utf-8")
    assert "forwarded_allow_ips" in cli_content, (
        "raven/mcp/cli.py must set forwarded_allow_ips for Tailscale host trust"
    )
    assert "proxy_headers=True" in cli_content, (
        "raven/mcp/cli.py must set proxy_headers=True"
    )