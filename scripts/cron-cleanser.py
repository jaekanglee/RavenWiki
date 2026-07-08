#!/usr/bin/env python3
# cron-cleanser.py — 주기적 Raven 볼트 큐레이션 및 린트 취합 파이썬 스크립트
#
# Usage: python3 cron-cleanser.py [vault_name]

import sys
from raven.core.vault import resolve_active_vault
from raven.core.lint import run_all
from raven.core.contracts import write_page

def main():
    vault_name = sys.argv[1] if len(sys.argv) > 1 else "default"
    try:
        vault = resolve_active_vault(vault_name)
    except Exception as e:
        print(f"   - 볼트 로드 실패: {e}")
        return 1

    res = run_all(vault)
    issues_found = [iss for iss in res.get("issues", []) if iss.get("severity") in ["critical", "warning"]]

    if not issues_found:
        print("   - 발견된 린트 무결성 오류가 없습니다. 클렌징 생략.")
        return 0

    created_count = 0
    for iss in issues_found:
        check_id = iss.get("id", "?")
        slug = iss.get("slug", "")
        msg = iss.get("message", "")
        
        if not slug:
            continue
            
        clean_check_id = check_id.replace("#", "")
        clean_slug = slug.replace("/", "-")
        # content/ 경로를 확실하게 붙여서 contracts/write_page에 들어오도록 함
        issue_slug = f"content/issues/issue-lint-{clean_check_id}-{clean_slug}"
        
        issue_path = vault.root / f"{issue_slug}.md"
        if issue_path.exists():
            continue
            
        title = f"Lint {check_id} 위반 조치 요청 — {slug}"
        content = f"""# {title}

> {msg}

## 상태
- status: draft
- progress: open

## 문제 상황
- 감지된 린트 규칙: {check_id}
- 대상 문서: [[{slug}]]
- 상세 내용: {msg}

## 원인 분석
에이전트가 린트 가이드를 위반하여 SoT 무결성을 해치고 있습니다.

## 해결 방안
- 해당 대상 문서의 {check_id} 규칙 위반 원인을 제거합니다.
- 수리 후 `wiki_lint()`가 통과하는지 재검증합니다.
"""
        # contracts.write_page가 content/가 있으면 이를 safe_path로 잘 resolve함
        write_page(
            vault, 
            issue_slug, 
            content, 
            title=title, 
            type="issue", 
            tags=["system", "issue", "lint-auto"],
            overwrite=True
        )
        created_count += 1
        print(f"   - [이슈 발행] {title}")

    print(f"   - 총 {created_count}개의 새로운 조치 요청 이슈를 발행했습니다.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
