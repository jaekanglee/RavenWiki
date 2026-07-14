"""v0.7.114+ lite bootstrap freshness 도구 (ADR-2026-07-08).

vault의 `_meta/agents/` 부속 3종 (SCHEMA.md / PROJECT-WORKFLOW.md / log.md)의
SHA256 hash와 cache_hash 비교. mismatch 시 silent warn (강제 read ❌).

또한 설치된 raven 패키지 템플릿 vs vault 부속 diff 가능 (기존 wiki_get_guide_diff
확장). `_meta/agents/.guide-version` 자동 stamp는 raven build 시 갱신.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

LITE_BOOTSTRAP_FILES = ("SCHEMA.md", "RAVEN-CONTRACT.md")
_LOG_MD_NAME = "log.md"


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
    except OSError:
        return None
    return h.hexdigest()[:16]  # 64-bit prefix, 충분한 충돌 저항


def _log_md_stats(path: Path) -> dict:
    if not path.exists():
        return {"lines": 0, "mtime": None, "exists": False}
    try:
        st = path.stat()
        text = path.read_text(encoding="utf-8", errors="replace")
        return {
            "lines": text.count("\n"),
            "mtime": st.st_mtime,
            "exists": True,
        }
    except OSError:
        return {"lines": 0, "mtime": None, "exists": False}


_LITE_BOOTSTRAP_KEYS = ("SCHEMA", "RAVEN-CONTRACT")


def _parse_cache_hash(raw: Optional[str]) -> dict:
    """agent가 보낸 cache_hash 파싱. 두 가지 형식 모두 지원:

    1. 명시 key=value: 'SCHEMA=abc,RAVEN-CONTRACT=def'  (권장)
    2. 순서 고정 단순: 'abc,def'  (SCHEMA, RAVEN-CONTRACT 순서)

    """
    if not raw:
        return {}
    out: dict = {}
    pairs = [p.strip() for p in raw.split(",") if p.strip()]
    if all("=" in pair for pair in pairs):
        # 명시 key=value
        for pair in pairs:
            k, v = pair.split("=", 1)
            out[k.strip()] = v.strip()
    else:
        # 순서 고정 fallback
        for i, key in enumerate(_LITE_BOOTSTRAP_KEYS):
            if i < len(pairs):
                out[key] = pairs[i]
    return out


def _load_version_stamp(vault_root: Path) -> dict:
    """_meta/agents/.guide-version 자동 stamp 파일 읽기.

    예:
        SCHEMA.md: abc123def456
        PROJECT-WORKFLOW.md: 789ghi012jkl
        log.md: 1234:1718000000.0
    """
    p = vault_root / "_meta" / "agents" / ".guide-version"
    if not p.exists():
        return {}
    out = {}
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    except OSError:
        return None  # type: ignore[return-value]
    return out


def write_version_stamp(vault_root: Path) -> bool:
    """_meta/agents/.guide-version 자동 stamp.

    Tier 2 Raven 제품 영역 (ADR-2026-07-08 §2.3).
    raven build / meta sync hook에서만 호출. 에이전트 write 금지.
    """
    agents = vault_root / "_meta" / "agents"
    if not agents.exists():
        return False
    lines: list[str] = []
    for fname in LITE_BOOTSTRAP_FILES:
        h = _sha256(agents / fname)
        # 정규화: SCHEMA.md → SCHEMA (헤더 형식과 일치)
        key = fname.replace(".md", "")
        if h:
            lines.append(f"{key}: {h}")
    log_stats = _log_md_stats(vault_root / _LOG_MD_NAME)
    if log_stats.get("exists"):
        lines.append(f"log.md: {log_stats['lines']}:{log_stats['mtime']}")
    try:
        (agents / ".guide-version").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False



def _format_hash_for_header(guides: dict) -> str:
    """응답 헤더 X-Guide-Hash: SCHEMA=abc,PROJECT-WORKFLOW=def 형식."""
    parts = []
    for key in _LITE_BOOTSTRAP_KEYS:
        info = guides.get(key, {})
        h = info.get("vault_hash") if isinstance(info, dict) else None
        if h:
            parts.append(f"{key}={h}")
    return ",".join(parts)


def check_freshness(vault_root: Path, cache_hash: Optional[str] = None) -> dict:
    """lite bootstrap 3종 freshness 검사.

    Args:
        vault_root: Vault 절대경로 (예: /Users/.../Raven/raven-dev)
        cache_hash: agent가 이전 호출에서 받은 hash.
            'SCHEMA:abc,PROJECT-WORKFLOW:def' 또는 None.

    Returns:
        {
          "vault": "raven-dev",
          "guides": {
            "SCHEMA": { "vault_hash": "...", "cache_match": bool|None, "lines": int },
            "PROJECT-WORKFLOW": { ... },
            "log": { "lines": int, "mtime": float|None },
          },
          "stale": bool,
          "stale_kinds": ["SCHEMA", "PROJECT-WORKFLOW"],
          "installed_hashes": { "SCHEMA": "...", "PROJECT-WORKFLOW": "..." },
        }
    """
    agents = vault_root / "_meta" / "agents"
    guides: dict = {}
    cache = _parse_cache_hash(cache_hash)

    # SCHEMA + PROJECT-WORKFLOW — 헤더 키 형식과 일치 (확장자 제거)
    for fname in LITE_BOOTSTRAP_FILES:
        path = agents / fname
        h = _sha256(path)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").count("\n") if path.exists() else 0
        except OSError:
            lines = 0
        key = fname.replace(".md", "")
        cache_h = cache.get(key)
        guides[key] = {
            "vault_hash": h,
            "cache_match": (h == cache_h) if (h and cache_h) else None,
            "lines": lines,
            "exists": path.exists(),
        }

    # log.md
    log_stats = _log_md_stats(vault_root / _LOG_MD_NAME)
    guides["log"] = log_stats

    # stamp
    stamp = _load_version_stamp(vault_root)

    stale_kinds = [k for k, v in guides.items() if isinstance(v, dict) and v.get("cache_match") is False]
    return {
        "vault": vault_root.name,
        "guides": guides,
        "stamp": stamp,
        "stale": bool(stale_kinds),
        "stale_kinds": stale_kinds,
    }
