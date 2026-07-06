"""stale.py — ADR-2026-07-06 §1.3 stale loop tools (MCP 골격).

Tools (신규):
    wiki_stale_detect — stale 후보 + evidence + suggested_action 반환 (read-only)
    wiki_archive      — 페이지를 archive/<YYYY-MM-DD>/<slug>.md로 이동 + frontmatter stamp

NOTE (v0.7.69+ 골격):
- 본 모듈은 인터페이스 골격만 제공. 실제 구현은 별도 사이클에서 ADR §4 수용 기준
  (tests/scenarios/test_stale_loop.py 4종 pass)에 따라 채워짐.
- ADR-2026-07-06 §1.3 "도구(Tooling)" 결정 그대로 따름.
- 기존 write.py의 wiki_delete는 archive 액션이지만 destructive — 본 wiki_archive는
  "정합화 루프의 일부"로 별도 권한 (단일 에이전트 호출 가능, ADR §1.2).
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from raven.core import archive as archive_module
from raven.core import frontmatter as core_frontmatter
from raven.core import slug as slug_module
from raven.core.contracts import rename_page
from raven.core.registry import VaultMeta
from raven.core.slug import SlugError
from raven.core.vault import Vault
from raven.mcp import db
from raven.mcp.tools import (
    VaultContext,
    PermissionError_,
    append_log_entry,
    check_lock,
    check_permission,
    normalize_actor,
    now_iso,
)


# ─────────────── shared helpers ───────────────


# ADR §1.1 4상태 정의
VALID_STATUSES = {"current", "stale", "contested", "archived"}

# ADR §1.4 시나리오 1의 임계값
DEFAULT_STALE_DAYS = 90


def _is_stale_candidate(
    frontmatter: dict,
    *,
    age_threshold_days: int,
    now: datetime,
) -> tuple[bool, str | None]:
    """ADR §1.4: 90일+ 미검증 또는 status=stale 명시 시 stale 후보.

    Returns:
        (is_candidate, evidence) — evidence는 사람이 검토할 수 있는 사유 1줄.

    골격 한계: 본 골격은 frontmatter의 `last_verified` 또는 `status`만 본다.
    실제 구현은 §1.4의 "사실 변경 감지"(outbound link 깨짐 등)도 포함해야 함.
    """
    status = frontmatter.get("status")
    if status == "stale":
        return True, "status: stale 명시"
    if status == "archived":
        return False, None  # archived는 stale 후보 아님
    last_verified = frontmatter.get("last_verified")
    if last_verified is None:
        return False, None
    try:
        last_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
        age_days = (now - last_dt).days
        if age_days >= age_threshold_days:
            return True, f"last_verified {age_days}일 전 (임계값 {age_threshold_days})"
    except (ValueError, AttributeError):
        return False, None
    return False, None


def _suggest_action(
    evidence: str | None,
    frontmatter: dict,
) -> Literal["update", "archive", "revalidate"]:
    """ADR §1.3 evidence + frontmatter 보고 suggested_action 결정.

    골격 정책:
    - evidence에 "임계값" 언급 → "revalidate" (검증 후 current 복귀 후보)
    - evidence에 "명시" 언급 → "update" (status: stale 직접 표기)
    - 그 외 → "archive" (사실 변경 의심)
    """
    if evidence is None:
        return "archive"
    if "임계값" in evidence:
        return "revalidate"
    return "update"


def _stamp_archived(
    source: Path,
    *,
    reason: str,
    actor: str,
) -> bool:
    """ADR §1.3: archive 액션 시 원본 frontmatter에 archived_at + reason stamp.

    골격 한계: 원본 파일의 frontmatter에 stamp만 추가, 실제 이동은 호출자가 처리.
    """
    if not source.exists():
        return False
    text = source.read_text(encoding="utf-8")
    fm, body = core_frontmatter.parse(text)
    if fm is None:
        fm = {}
    fm["archived_at"] = now_iso()
    fm["archive_reason"] = reason
    if "agents" not in fm or not isinstance(fm.get("agents"), list):
        fm["agents"] = []
    fm["agents"].append(
        {
            "actor": actor,
            "action": "archived",
            "at": now_iso(),
            "evidence": reason,
        }
    )
    new_text = core_frontmatter.render(fm, body)
    source.write_text(new_text, encoding="utf-8")
    return True


# ─────────────── 1. wiki_stale_detect (read) ───────────────


def wiki_stale_detect(
    *,
    vault: Path,
    age_threshold_days: int = DEFAULT_STALE_DAYS,
    include_self_verified: bool = False,
) -> dict:
    """ADR §1.3 stale 후보 감지 (read-only).

    Args:
        vault: vault 경로.
        age_threshold_days: ADR §1.4 임계값 (기본 90일).
        include_self_verified: True면 current + last_verified 있는 페이지도 포함 (디버깅용).

    Returns:
        {
            "candidates": [
                {
                    "slug": str,
                    "status": "stale"|"current"|...,
                    "last_verified_at": str|None,
                    "age_days": int|None,
                    "evidence": str|None,
                    "suggested_action": "update"|"archive"|"revalidate",
                }
            ],
            "summary": {"total_scanned": int, "stale_count": int, ...}
        }

    골격 한계: 현 구현은 registry에 등록된 단일 vault의 모든 markdown을 스캔한다.
    실제 구현은 wiki.db의 pages 테이블 조회로 최적화 필요 (B#8 lint 캐싱과 동시).
    """
    now = datetime.now(timezone.utc)
    candidates = []
    total_scanned = 0

    # v0.7.69+ 골격: registry.list_vaults()를 통한 단일 vault 가정
    # (vault 인자가 Path로 직접 주어지므로 registry 우회)
    if not vault.exists():
        return {
            "candidates": [],
            "summary": {"total_scanned": 0, "stale_count": 0, "error": "vault not found"},
        }

    # 페이지 enumerate (content_root 기준)
    content_root = vault / "content"
    if not content_root.exists():
        return {
            "candidates": [],
            "summary": {"total_scanned": 0, "stale_count": 0},
        }

    for md_path in content_root.rglob("*.md"):
        total_scanned += 1
        try:
            text = md_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        fm, _body = core_frontmatter.parse(text)
        if fm is None:
            fm = {}

        is_cand, evidence = _is_stale_candidate(
            fm, age_threshold_days=age_threshold_days, now=now
        )
        if not is_cand and not include_self_verified:
            continue

        slug = md_path.relative_to(content_root).with_suffix("").as_posix()
        last_verified = fm.get("last_verified")
        age_days = None
        if last_verified is not None:
            try:
                last_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
                age_days = (now - last_dt).days
            except (ValueError, AttributeError):
                pass

        candidates.append(
            {
                "slug": slug,
                "status": fm.get("status", "current"),
                "last_verified_at": last_verified,
                "age_days": age_days,
                "evidence": evidence,
                "suggested_action": _suggest_action(evidence, fm),
            }
        )

    return {
        "candidates": candidates,
        "summary": {
            "total_scanned": total_scanned,
            "stale_count": len(candidates),
            "age_threshold_days": age_threshold_days,
        },
    }


# ─────────────── 2. wiki_archive (write / admin) ───────────────


def wiki_archive(
    *,
    slug: str,
    reason: str = "stale_over_threshold",
    actor: str | None = None,
    dry_run: bool = False,
    ctx: VaultContext,
) -> dict:
    """ADR §1.3 격리 액션 — archive/<YYYY-MM-DD>/<slug>.md로 이동.

    Args:
        slug: 격리할 페이지의 slug.
        reason: "stale_over_threshold"|"user_request"|"factual_obsolete" (ADR §1.3 명시).
        actor: 호출자 식별.
        dry_run: True면 실제 이동 없이 결과만 반환.
        ctx: VaultContext (mode 검증).

    Returns:
        {
            "ok": bool,
            "archived_path": str|None,
            "source_frontmatter_stamped": bool,
            "dry_run": bool,
            "evidence": {...},
        }

    골격 한계:
    - ADR §1.3 "guards" 4종 (slug validate / FileLock / provenance / idempotent) 중
      slug validate + provenance + idempotent 골격만 구현. FileLock은 core/lock.py와
      통합이 필요하여 별도 패치.
    - ADR §1.2 권한 — write 또는 admin 모드 요구 (check_permission으로 위임).
    """
    actor = normalize_actor(actor)

    # ADR §1.3 guards: slug validate (path traversal 차단 — SlugError raise)
    try:
        slug_module.validate(slug, vault_root=ctx.vault)
    except SlugError as slug_err:
        return {
            "ok": False,
            "error": f"invalid slug: {slug_err}",
            "slug": slug,
        }

    # ADR §1.2 권한 검증 (check_permission raises PermissionError_)
    try:
        check_permission("wiki_archive", ctx.mode)
    except PermissionError_ as perm_err:
        return {
            "ok": False,
            "error": str(perm_err),
            "required_mode": "write or admin",
            "current_mode": ctx.mode,
        }

    # ADR §1.2 "본문 50%+ 재작성" 무관 (archive는 본문 손실 ❌, 이동 ⭕)
    # 단 archive 대상 검증: source 파일 존재 확인
    source = ctx.vault / "content" / f"{slug}.md"
    if not source.exists():
        return {
            "ok": False,
            "error": "source not found",
            "slug": slug,
            "expected_path": str(source),
        }

    # archive 경로: <vault>/archive/<YYYY-MM-DD>/<slug>.md
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_path = ctx.vault / "archive" / today / f"{slug}.md"

    result = {
        "ok": True,
        "slug": slug,
        "archived_path": str(archive_path),
        "source_frontmatter_stamped": False,
        "dry_run": dry_run,
        "evidence": {
            "reason": reason,
            "actor": actor,
            "at": now_iso(),
        },
    }

    if dry_run:
        return result

    # ADR §1.3: 실제 이동 + stamp
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 원본 frontmatter stamp (이동 전에 해야 안전 — 실패 시 복원 가능)
    stamped = _stamp_archived(source, reason=reason, actor=actor)

    # 2. 이동 (shutil.move는 cross-filesystem 지원)
    shutil.move(str(source), str(archive_path))

    # 3. log.md 기록 (append_log_entry: subject 필수)
    append_log_entry(
        ctx.vault,
        action="archive",
        subject=f"{slug} → {archive_path.relative_to(ctx.vault)}",
        actor=actor,
        extras=[f"reason: {reason}", f"archived_path: {archive_path}"],
    )

    result["source_frontmatter_stamped"] = stamped
    return result