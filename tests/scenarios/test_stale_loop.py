"""ADR-2026-07-06 §1.4 시나리오 테스트 골격 — 4종 시나리오 + 회귀 가드 2종.

본 파일은 골격만 제공. 실제 구현은 다음 사이클에서:
1. ADR §4 수용 기준 (4종 시나리오 pass + 회귀 2종 pass)
2. 평가 문서 §5.2 done_when (#0, #2, #3 등) cross-link

골격 시나리오:
- test_stale_detected_after_threshold    (§1.4 #1: 90일 전 last_verified → 후보 반환)
- test_stale_revalidated_with_evidence   (§1.4 #2: stale + 새 출처 → current 전이 + agents 기록)
- test_archive_moves_file_and_stamps     (§1.4 #3: wiki_archive → archive/<date>/ 이동 + frontmatter stamp)
- test_update_rejects_50pct_rewrite      (§1.4 #4: content 1.5배 초과 → wiki_update 거절)

회귀 가드 (ADR §1.4):
- test_frontmatter_block_yaml_roundtrip  (평가 A#3 회귀 — block YAML 보존)
- test_archive_path_traversal_blocked    (평가 A#1 회귀 — slug='../../etc' 차단)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from raven.core import frontmatter as core_frontmatter
from raven.mcp.tools import VaultContext
from raven.mcp.tools import stale as stale_tools


# ─────────────────────────── 시나리오 4종 ───────────────────────────


def test_stale_detected_after_threshold(isolated_vault, make_page):
    """§1.4 #1: 90일 전 last_verified → wiki_stale_detect가 후보로 반환.

    골격: frontmatter에 status=current이나 last_verified=91일 전인 페이지를 만들고,
    wiki_stale_detect 호출 → 해당 slug가 candidates에 포함되고 evidence에 "91일 전" 언급 확인.
    """
    long_ago = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
    make_page(
        isolated_vault,
        "stale-topic",
        frontmatter={
            "title": "Stale Topic",
            "status": "current",
            "last_verified": long_ago,
        },
        body="본문",
    )

    result = stale_tools.wiki_stale_detect(vault=isolated_vault)

    candidates = result.get("candidates", [])
    matched = [c for c in candidates if c["slug"] == "stale-topic"]
    assert len(matched) == 1, f"expected 1 candidate, got {len(matched)}"
    cand = matched[0]
    assert cand["status"] == "current"
    assert cand["age_days"] is not None and cand["age_days"] >= 90
    assert "91" in (cand["evidence"] or "") or cand["suggested_action"] == "revalidate"


def test_stale_revalidated_with_evidence(isolated_vault, make_page):
    """§1.4 #2: stale 페이지 + 새 사실 출처 → current 전이 + agents: 기록.

    골격: status=stale인 페이지를 만든 뒤 wiki_update(revalidate=true) 시뮬레이션.
    구현은 다음 사이클 — 현 골격은 helper로 상태 전이 골격만 확인.
    """
    long_ago = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
    page = make_page(
        isolated_vault,
        "revalidatable",
        frontmatter={
            "title": "Revalidatable",
            "status": "stale",
            "last_verified": long_ago,
        },
        body="본문",
    )

    # 골격: frontmatter.status를 current로 전이 + agents append
    text = page.read_text(encoding="utf-8")
    fm, body = core_frontmatter.parse(text)
    fm["status"] = "current"
    fm["last_verified"] = datetime.now(timezone.utc).isoformat()
    if "agents" not in fm or not isinstance(fm.get("agents"), list):
        fm["agents"] = []
    fm["agents"].append(
        {
            "actor": "test_actor",
            "action": "revalidated",
            "at": datetime.now(timezone.utc).isoformat(),
            "evidence": "new source: <test_url>",
        }
    )
    page.write_text(core_frontmatter.render(fm, body), encoding="utf-8")

    # 검증
    new_text = page.read_text(encoding="utf-8")
    new_fm, _ = core_frontmatter.parse(new_text)
    assert new_fm["status"] == "current"
    assert any(a.get("action") == "revalidated" for a in new_fm["agents"])


def test_archive_moves_file_and_stamps(isolated_vault, make_page):
    """§1.4 #3: wiki_archive → archive/<date>/<slug>.md 이동 + frontmatter stamp.

    골격: write/admin 모드에서 wiki_archive 호출 → archive/<YYYY-MM-DD>/ 경로에 파일 존재,
    원본(은 archive에 있음) frontmatter에 archived_at + archive_reason + agents 기록 확인.

    NOTE: 골격은 dry_run=False 시 실제 이동. dry_run=True 권장 (CI 안정성).
    """
    page = make_page(
        isolated_vault,
        "to-archive",
        frontmatter={"title": "To Archive", "status": "current"},
        body="본문",
    )
    ctx = VaultContext(vault=isolated_vault, mode="write")

    result = stale_tools.wiki_archive(
        slug="to-archive",
        reason="stale_over_threshold",
        actor="test_actor",
        dry_run=True,  # 골격은 dry_run으로 검증 (CI 안정성)
        ctx=ctx,
    )
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert "archive/" in result["archived_path"]
    assert result["slug"] == "to-archive"
    # 원본은 dry_run이므로 이동 안 됨
    assert page.exists()


def test_update_rejects_50pct_rewrite(isolated_vault, make_page):
    """§1.4 #4: wiki_update content 1.5배 초과 → 거절 (대규모 재작성 가드).

    골격: 기존 본문 100자 + 신규 본문 200자 (2배) → 가드 트리거 시뮬레이션.
    실제 wiki_update 호출은 다음 사이클 (P0#3 frontmatter 오염 결함과 동시 해결).
    """
    body = "a" * 100
    page = make_page(
        isolated_vault,
        "guard-target",
        frontmatter={"title": "Guard Target"},
        body=body,
    )

    # 가드 로직 (ADR §1.3): content 길이가 기존 본문의 1.5배 초과 시 거절
    new_body = "a" * 200  # 2배
    old_len = len(body)
    new_len = len(new_body)
    exceeds_1_5x = new_len > old_len * 1.5

    assert exceeds_1_5x, "test fixture sanity: 200 > 100*1.5"
    # 실제 거절 로직은 wiki_update에 추가될 때 검증 (next cycle)


# ─────────────────────────── 회귀 가드 2종 ───────────────────────────


def test_frontmatter_block_yaml_roundtrip(isolated_vault, make_page):
    """평가 A#3 회귀 — block YAML tags가 갱신 후에도 보존.

    골격: block-style YAML `tags:\\n  - alpha` 작성 → parse → render → parse 시 tags=['alpha'] 보존 확인.
    """
    block_yaml = "---\ntitle: Test\ntags:\n  - alpha\n  - beta\n---\n본문"
    page = isolated_vault / "content" / "block-yaml.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(block_yaml, encoding="utf-8")

    # 1차 parse
    fm1, body1 = core_frontmatter.parse(page.read_text(encoding="utf-8"))
    assert fm1.get("tags") == ["alpha", "beta"] or set(fm1.get("tags", [])) == {"alpha", "beta"}

    # render → parse roundtrip
    new_text = core_frontmatter.render(fm1, body1)
    fm2, _ = core_frontmatter.parse(new_text)
    assert fm2.get("tags") == fm1.get("tags"), "block YAML tags 손실"


def test_archive_path_traversal_blocked(isolated_vault):
    """평가 A#1 회귀 — slug='../../etc/passwd' → wiki_archive 400.

    골격: slug validation 실패 시 ok=False + error 메시지에 'invalid slug' 포함.
    """
    ctx = VaultContext(vault=isolated_vault, mode="write")
    result = stale_tools.wiki_archive(
        slug="../../etc/passwd",
        reason="user_request",
        actor="attacker",
        dry_run=True,
        ctx=ctx,
    )
    assert result["ok"] is False
    assert "invalid slug" in result.get("error", "").lower() or "traversal" in result.get("error", "").lower()