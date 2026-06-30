"""v0.6.36+ — vendor-neutral 정책 회귀 가드.

Raven north star (Karpathy LLM Wiki): 에이전트 vendor에 종속되지 않는다.
"Codex" / "Claude" / "Antigravity" / "Hermes" 등 특정 vendor명을 정책
문서나 라이브 README에 박지 않는다 (예시는 OK, 정책/문서 본문 ❌).

회귀 가드 (5개):
  1. agent/README.md 외부 LLM cross-check 섹션에 vendor명 0회
  2. raven/agents/__init__.py docstring에 vendor명 0회
  3. raven/__init__.py module docstring에 vendor명 0회
  4. raven/mcp/cli.py + README에 vendor명 0회 (transport 설명)
  5. README.md 메인 파일에 vendor명 박힘 감지 (예외: changelog/decisions/raw 보존)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

# 정책 위반 검출 대상 vendor명 (case-sensitive, 단어 경계)
VENDOR_NAMES = (
    "Codex",
    "Antigravity",
    "agy",
)

# 정책/라이브 README는 OK, 보존 영역(예외) 정의
EXEMPT_DIRS = (
    "_meta/raw",            # Karpathy 원본 (불변)
    "_meta/decisions",      # ADR 본문 (결정 근거로 vendor명 OK)
    "_meta/changelog",      # changelog 역사 보존
    "raven/curator",        # v3 합의안 docstring (역사)
)

# vendor 예시로만 쓰이는 경우 OK (e.g., "(예: Codex)")
# 단, "Codex CLI" / "Antigravity CLI" 같은 정책 표기는 ❌
POLICY_FORBIDDEN_PATTERNS = [
    re.compile(r"\bCodex\s+CLI\b"),
    re.compile(r"\bAntigravity\s+CLI\b"),
    re.compile(r"\bHermes\s+CLI\b"),
    re.compile(r"\bClaude\s+CLI\b"),
]


def _is_exempt(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel.startswith(ex) for ex in EXEMPT_DIRS)


def _scan_file_for_vendor_names(path: Path) -> list[tuple[str, str]]:
    """파일에서 vendor명 발견 시 (line_no, line) 리스트 반환."""
    if not path.exists() or not path.is_file():
        return []
    findings: list[tuple[str, str]] = []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    for i, line in enumerate(content.splitlines(), start=1):
        for vendor in VENDOR_NAMES:
            if vendor in line:
                findings.append((f"L{i}: '{vendor}'", line.strip()[:120]))
    return findings


def _scan_file_for_policy_patterns(path: Path) -> list[tuple[str, str]]:
    """정책 표기 패턴 (e.g. 'Codex CLI') 발견 시."""
    if not path.exists() or not path.is_file():
        return []
    findings: list[tuple[str, str]] = []
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    for i, line in enumerate(content.splitlines(), start=1):
        for pat in POLICY_FORBIDDEN_PATTERNS:
            if pat.search(line):
                findings.append((f"L{i}: '{pat.pattern}'", line.strip()[:120]))
    return findings


# ---------------------------------------------------------------------------
# 5개 회귀 가드
# ---------------------------------------------------------------------------


def test_agent_readme_external_delegation_section_is_vendor_neutral() -> None:
    """agent/README.md 외부 LLM cross-check 섹션에 vendor명 0회."""
    target = ROOT / "raven" / "core" / "templates" / "agent" / "README.md"
    findings = _scan_file_for_vendor_names(target)
    findings += _scan_file_for_policy_patterns(target)
    assert not findings, (
        f"agent/README.md 외부 위임 섹션에 vendor명 박힘 ❌ (north star 위반):\n"
        + "\n".join(f"  {loc}: {line}" for loc, line in findings)
    )


def test_raven_agents_init_is_vendor_neutral() -> None:
    """raven/agents/__init__.py docstring에 vendor명 0회."""
    target = ROOT / "raven" / "agents" / "__init__.py"
    findings = _scan_file_for_vendor_names(target)
    assert not findings, (
        f"raven/agents/__init__.py docstring에 vendor명 박힘 ❌ (north star 위반):\n"
        + "\n".join(f"  {loc}: {line}" for loc, line in findings)
    )


def test_raven_root_init_is_vendor_neutral() -> None:
    """raven/__init__.py module docstring에 vendor명 0회."""
    target = ROOT / "raven" / "__init__.py"
    findings = _scan_file_for_vendor_names(target)
    assert not findings, (
        f"raven/__init__.py module docstring에 vendor명 박힘 ❌ (north star 위반):\n"
        + "\n".join(f"  {loc}: {line}" for loc, line in findings)
    )


def test_raven_mcp_transport_is_vendor_neutral() -> None:
    """raven/mcp/cli.py + README.md에 vendor명 0회 (transport 설명)."""
    findings: list[tuple[str, str]] = []
    for rel in ("raven/mcp/cli.py", "raven/mcp/README.md"):
        findings += _scan_file_for_vendor_names(ROOT / rel)
    assert not findings, (
        f"raven/mcp/에 vendor명 박힘 ❌ (north star 위반):\n"
        + "\n".join(f"  {loc}: {line}" for loc, line in findings)
    )


def test_root_readme_vendor_neutral_in_policy_sections() -> None:
    """README.md 정책/라이브 본문에 vendor명 박힘 감지.

    예외:
      - changelog/decisions/raw 영역 (역사 보존)
      - 'vendor-neutral' 같은 정책 자체를 언급하는 메타 단어 (OK)
    """
    target = ROOT / "README.md"
    findings = _scan_file_for_vendor_names(target)
    # 'vendor-neutral' 자체는 OK (정책 메타)
    findings = [(loc, line) for loc, line in findings if "vendor-neutral" not in line.lower()]
    assert not findings, (
        f"README.md에 vendor명 박힘 ❌ (north star 위반):\n"
        + "\n".join(f"  {loc}: {line}" for loc, line in findings)
    )