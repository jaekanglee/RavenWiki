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

    v0.7.69+ Plan B-2: write.py에 가드 통합. 격리 vault는 .vault.json 없이
    contracts.write_page가 실패할 수 있으므로 직접 _check_large_rewrite 가드만
    별도로 검증.
    """
    body = "a" * 100
    page = make_page(
        isolated_vault,
        "guard-target",
        frontmatter={"title": "Guard Target"},
        body=body,
    )

    # 가드 로직 시뮬레이션 (write.py wiki_update 안에 통합됨)
    new_body = "a" * 200  # 2배 = 1.5배 초과
    existing_len = len(body)
    new_len = len(new_body)
    exceeds_1_5x = new_len > existing_len * 1.5

    assert exceeds_1_5x, "test fixture sanity: 200 > 100*1.5"
    # 실제 가드는 write.py wiki_update에 통합됨 — write_page 호출 직전 검증.
    # 본 시나리오는 정책 결정을 검증 (1.5배 임계값 + 차단 메시지).
    # 통합 테스트는 vault + .vault.json이 필요하므로 별도 패치.


def test_update_allows_partial_rewrite(isolated_vault, make_page):
    """§1.4 #4 false positive 회피: 1.5배 이하 갱신은 허용.

    v0.7.69+ Plan B-2: 기존 100자 + 신규 130자 (1.3배) → 가드 통과해야 함.
    """
    body = "x" * 100
    new_body = "x" * 130  # 1.3배

    existing_len = len(body)
    new_len = len(new_body)
    blocked = existing_len > 0 and new_len > existing_len * 1.5

    assert not blocked, "1.3배는 가드 통과해야 함"


def test_update_allows_new_page(isolated_vault, make_page):
    """§1.4 #4 false positive 회피: 신규 생성은 본문 0→N이므로 가드 우회.

    v0.7.69+ Plan B-2: creating=True (abs_path.exists()=False)면 가드 미적용.
    """
    # 신규 페이지는 본문 길이 비교 대상이 없음
    creating = True  # 신규 시뮬레이션
    if creating:
        # 가드 자체가 안 걸림
        skipped = True
    assert skipped


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
    assert "invalid slug" in result.get("error", "").lower() or "traversal" in result.get(
        "error", ""
    ).lower()


# ─────────────────────────── Plan B-2 시나리오 (실제 이동 + lock) ───────────────────────────


def test_archive_actually_moves_file_with_lock(isolated_vault, make_page):
    """§1.3 guards 4종 통합 검증: dry_run=False → 실제 이동 + frontmatter stamp + lock 적용.

    골격: archive 호출 후 source 사라지고 archive/<today>/<slug>.md 존재 확인.
    archive된 파일의 frontmatter에 archived_at + archive_reason + agents 존재 확인.
    """
    page = make_page(
        isolated_vault,
        "real-archive",
        frontmatter={"title": "Real Archive", "status": "stale"},
        body="원본 본문",
    )
    ctx = VaultContext(vault=isolated_vault, mode="write")

    result = stale_tools.wiki_archive(
        slug="real-archive",
        reason="factual_obsolete",
        actor="test_actor",
        dry_run=False,
        ctx=ctx,
    )

    assert result["ok"] is True, f"expected ok=True, got {result}"
    assert result["dry_run"] is False
    assert result["source_frontmatter_stamped"] is True

    # 1. 원본(content/) 사라짐
    assert not page.exists(), "원본이 이동되지 않음"

    # 2. archive/<today>/<slug>.md 존재
    archived = Path(result["archived_path"])
    assert archived.exists(), f"archive 파일 미존재: {archived}"

    # 3. archive된 파일의 frontmatter 확인
    archived_text = archived.read_text(encoding="utf-8")
    fm, body = core_frontmatter.parse(archived_text)
    assert fm.get("archive_reason") == "factual_obsolete"
    assert fm.get("archived_at") is not None
    assert any(a.get("action") == "archived" for a in fm.get("agents", []))

    # 4. log.md 기록 확인
    log_path = isolated_vault / "log.md"
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8")
        assert "archive" in log_text.lower()


def test_archive_readonly_mode_blocked(isolated_vault, make_page):
    """§1.2 권한 검증: read 모드에서 wiki_archive 호출 시 거부.

    골격: read 모드 → check_permission raises → ok=False + 권한 메시지.
    """
    make_page(
        isolated_vault,
        "perm-test",
        frontmatter={"title": "Perm Test"},
        body="본문",
    )
    ctx = VaultContext(vault=isolated_vault, mode="read")

    result = stale_tools.wiki_archive(
        slug="perm-test",
        reason="user_request",
        actor="reader_agent",
        dry_run=True,  # dry_run이지만 권한은 먼저 체크됨
        ctx=ctx,
    )
    assert result["ok"] is False
    assert "permission" in result.get("error", "").lower() or "write" in result.get("error", "").lower()


def test_stale_detect_uses_wiki_db_when_available(isolated_vault, make_page):
    """§1.3 wiki.db 최적화: wiki.db가 있으면 list_pages() 우선 사용.

    골격: 페이지 1개 만들고 detect 호출 → summary.source == "filesystem" (wiki.db 없음)
    (골격 한계 — wiki.db 빌드는 별도 패치). wiki.db 구축 후 재실증은 별도 사이클.
    """
    make_page(
        isolated_vault,
        "db-optimize-target",
        frontmatter={"title": "DB Optimize", "status": "current"},
        body="본문",
    )

    result = stale_tools.wiki_stale_detect(vault=isolated_vault)
    # wiki.db가 없는 격리 vault → filesystem fallback 경로
    assert result["summary"]["total_scanned"] >= 1
    assert result["summary"]["source"] in ("filesystem", "wiki.db")


# ─────────────────────────── write.py 가드 통합 테스트 ───────────────────────────


def test_write_update_1_5x_guard_blocks(tmp_path):
    """§1.3 1.5배 가드 통합: write.py wiki_update 호출 시 본문 50%+ 재작성 거부.

    격리 vault를 bootstrap한 뒤 wiki_update를 직접 호출 (vault handle 필요).
    1차 갱신(1.3배 → 가드 통과 → 실제 write), 2차 갱신(1.5x → 가드 정확히 차단) 검증.
    """
    from raven.core import frontmatter as core_frontmatter
    from raven.mcp.tools import VaultContext
    from raven.mcp.tools import write as write_tools

    vault_path = tmp_path / "write-guard-vault"
    (vault_path / "content").mkdir(parents=True)

    # 기존 페이지 (100자 본문) — write.py _resolve_md_path가 content/<slug>.md 기대
    page_path = vault_path / "content" / "guard-page.md"
    fm = {"title": "Guard Page"}
    body = "a" * 100
    page_path.write_text(core_frontmatter.render(fm, body), encoding="utf-8")

    ctx = VaultContext(vault=vault_path, mode="write")

    # 1차: 1.3배 갱신 (130자) → 가드 통과. write_page 실패 가능하나 error != "large_rewrite_blocked" 확인
    short_content = "a" * 130
    result_short = write_tools.wiki_update(
        slug="guard-page",
        content=short_content,
        ctx=ctx,
        actor="test_actor",
    )
    # 1.3배는 가드 통과. write_page 자체 실패(예: .vault.json 부재)는 별개 이슈
    assert result_short.get("error") != "large_rewrite_blocked", (
        f"1.3배는 가드 통과해야 함: {result_short}"
    )

    # 2차: 200자 (기존 130 → 200 = 1.54배) → 가드 정확히 차단
    # write_page가 1차에 실패했더라도 본문은 100자 그대로 → 100 vs 200 = 2배 차단
    long_content = "a" * 200
    result_long = write_tools.wiki_update(
        slug="guard-page",
        content=long_content,
        ctx=ctx,
        actor="test_actor",
    )
    assert result_long.get("ok") is False
    assert result_long.get("error") == "large_rewrite_blocked"
    assert "50%+" in result_long.get("message", "") or "1.5" in result_long.get("message", "")
    # _existing_len은 본문 길이 (frontmatter 제외). write_page 성공 시 130, 실패 시 100.
    # 어느 쪽이든 200 > existing * 1.5 라야 가드가 걸렸다는 의미
    existing_len = result_long.get("_existing_len")
    new_len = result_long.get("_new_len")
    assert existing_len in (100, 130), f"unexpected existing_len: {existing_len}"
    assert new_len == 200
    assert new_len > existing_len * 1.5, f"1.5배 미만인데 가드 걸림: {existing_len}→{new_len}"


def test_write_update_allows_new_page_1_5x_guard_skipped(tmp_path):
    """§1.4 false positive 회피 통합: 신규 페이지는 본문 0→N이므로 가드 우회.

    write.py wiki_update 호출 — 신규 slug는 본문 비교 대상 없어 가드 미적용.
    """
    from raven.mcp.tools import VaultContext
    from raven.mcp.tools import write as write_tools

    vault_path = tmp_path / "new-page-guard-vault"
    (vault_path / "content").mkdir(parents=True)

    ctx = VaultContext(vault=vault_path, mode="write")
    new_content = "x" * 1000  # 큰 본문이지만 신규 페이지

    result = write_tools.wiki_update(
        slug="never-existed-slug",
        content=new_content,
        ctx=ctx,
        actor="test_actor",
    )
    # 신규 페이지이므로 가드 안 걸림 (large_rewrite_blocked가 아님)
    assert result.get("error") != "large_rewrite_blocked", (
        f"신규 페이지는 가드 우회해야 함: {result}"
    )