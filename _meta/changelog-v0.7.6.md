# raven v0.7.6 — Lite bootstrap `PROJECT-WORKFLOW.md` 강화 (사람/에이전트 이중 헤더 + type 8종 템플릿)

> **핵심**: 사용자 정정 (2026-06-30) — "문서 내부 섹션 타이틀은 사람이 읽을 수 있는 네이밍 + 에이전트가 읽는 네이밍 둘 다 해야 할 것 같은데. 너무 에이전트 위주만 ❌"
>
> v0.7.6: Lite bootstrap `PROJECT-WORKFLOW.md` 본문 강화 — **사람/에이전트 이중 헤더 정책** (이모지 한글 + 영문 ID), **BLUF 강조**, **type 8종 템플릿**, **일관성 체크리스트**. 옛 Runtime Inputs (`project name` / `vault path` / `current task`) → 새 본문으로 대체.
>
> **Phase B 완료** — Dashboard 뷰어 (v0.7.5) + 문서 일관성 (v0.7.6) = 사용자 두 문제 해결.

릴리스 일자: 2026-06-30
이전: v0.7.5 (Dashboard @uiw/react-md-editor)

---

## 한 줄 요약

Lite bootstrap `PROJECT-WORKFLOW.md`를 사람 친화적 이모지 한글 + 영문 ID 이중 헤더로 재작성. 4가지 결정 (결론/분업/트리거/금지) + type 8종 템플릿 + 일관성 체크리스트 + 7개 권장 폴더 구조.

## 1. 변경 사항

### 1-1. `raven/core/templates/agent/PROJECT-WORKFLOW.md` (재작성)

**Before (v0.7.3, 사용자 commit 9d2c8a5)**:
- Runtime Inputs / Start Every Session / Tool Use / Report Back (영문 only, 에이전트 위주)
- 1910 bytes, 단순 가이드

**After (v0.7.6+)**:
- 7742 bytes, 사람/에이전트 이중 헤더
- 7개 섹션:
  - 📌 1. 작성 가이드 — BLUF (Bottom Line Up First) → 4가지 결정 (결론/분업/트리거/금지)
  - 📝 2. 페이지 작성 템플릿 (Type 8종) — concept / decision / journal / rule / person / tool / comparison / query / project
  - ✅ 3. 일관성 체크리스트 (5개: BLUF, frontmatter, type, wikilink, 저장 신호)
  - 🔗 4. 참고 (References)
  - 💡 5. 예시
  - 📌 6. 작성자 가이드 — 사람/에이전트 이중 헤더 정책
  - ⚠️ 7. 폴더 구조 권장 (vault 자유지만 일관성)

**이중 헤더 패턴** (사용자 north star 정확 반영):
```
## 📌 결론 (Conclusion)
> 📝 사람: 페이지 첫 줄에 무엇인지 1줄.
> 🤖 Agent: `[BLUF] {결론 1문장}` 패턴 권장.
```

### 1-2. `raven/core/templates/agents/` 디렉토리 삭제

옛 path `templates/agents/PROJECT-WORKFLOW.md` (사용자 commit 9d2c8a5가 일시적으로 박음) 삭제.
**정합성**: `templates/agent/` 한 곳에만 박힘 (vault.py + verify.py path 일치).

### 1-3. `raven/core/vault.py` `sync_meta()` — Tier 1 leak 방지

**Before (v0.7.5)**:
```python
else:  # full set
    file_map = {
        "_meta/system/SCHEMA.md":     ...,
        "_meta/system/OPERATIONS.md": "templates/system/OPERATIONS.md",  # Tier 1
        "_meta/agent/README.md":      "templates/agent/README.md",        # Tier 1
        "_meta/agent/TOOLS.md":       ...,
        "_meta/agent/WORKFLOW.md":    ...,
        "_meta/agent/SAFETY.md":      ...,
        "log.md":                      ...,
        "raven-policy.md":             "templates/wikisys-policy.md",     # Tier 1
    }
```

**After (v0.7.6+)**:
```python
else:  # full set
    # v0.7.6+: Tier 1 internal sync ❌ (Lite bootstrap 정책 일관성)
    # full 옵션은 deprecated (lite와 동일하게 처리)
    file_map = {  # Lite 5종만
        "_meta/system/SCHEMA.md":          ...,
        "_meta/system/RULES.md":           ...,
        "_meta/system/AGENTS.md":          ...,
        "_meta/agents/PROJECT-WORKFLOW.md": "templates/agent/PROJECT-WORKFLOW.md",
        "log.md":                          ...,
    }
```

→ **`sync_meta(full=True)` = `sync_meta(lite=True)`** (Tier 1 leak 방지). 옛 옵션 의도 (Tier 1 internal sync) 제거.

### 1-4. `tests/test_v0_7_1_lite_bootstrap_surface.py` (확장)

신규 회귀 가드 2개:
- `test_lite_project_workflow_has_dual_audience_headings` — 사람/에이전트 이중 헤더 정책
- `test_lite_project_workflow_is_only_in_agent_template` — path 정합성 (`agent/`만, `agents/` ❌)

기존 테스트 갱신:
- `test_lite_project_workflow_is_user_surface` — 옛 `project name` / `vault path` 키워드 → 새 `BLUF` / `concept` / `🤖` / `📝` 키워드 (의미 변동 반영)
- `test_lite_project_workflow_has_bluf_guidance` — BLUF / type 8종 / 체크리스트 / 저장 신호 4가지 검증

### 1-5. `tests/test_cli.py`, `tests/test_vault_create.py` (옛 정책 갱신)

옛 `test_cli_meta_sync_full_with_force` + `test_sync_meta_full_copies_raven_internals` 의도 (Tier 1 internal sync) → 새 정책 (Lite 5종만 sync) 반영:
- 옛 assertion (Tier 1 internal 파일 존재) → 새 assertion (Tier 1 internal 파일 ❌)
- Lite 5종은 그대로 검증

### 1-6. 기존 vault 동기화

- `~/Raven/raven-dev/_meta/agents/PROJECT-WORKFLOW.md` — 새 템플릿으로 갱신 (.bak 백업 보존)

→ **harumoa vault는 운영자 사용 중** → 동기화 ❌ (사용자 vault 데이터 write 정책)

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **468 passed, 1 skipped** (v0.7.5: 465 → v0.7.6: 468, +3) |
| test_v0_7_1_lite_bootstrap_surface | ✅ 11 tests (이전 9 → 11, +2) |
| test_cli_meta_sync_full_with_force | ✅ 새 정책 (Lite 5종 only) 검증 |
| test_sync_meta_full_copies_raven_internals | ✅ Tier 1 leak ❌ 검증 |
| raven-dev vault PROJECT-WORKFLOW.md | ✅ 새 템플릿 동기화 |

## 3. 의도

사용자 (2026-06-30):
> "Dashboard에서 만들어진 문서 보는데 1) 너무 조잡함 마크다운 뷰어가 2) 문서 내용이 너무 제각각 중구난방임"

→ **Phase A (v0.7.5)**: 마크다운 뷰어 교체 — @uiw/react-md-editor. **조잡함 해결**.
→ **Phase B (v0.7.6)**: 문서 일관성 — Lite bootstrap PROJECT-WORKFLOW.md에 사람/에이전트 이중 헤더 + BLUF + type 8종 템플릿. **중구난방 해결 (가이드)**.

**사용자 정정 #2 (이중 헤더)**:
> "내부 섹션 타이틀은 사람이 읽을 수 있는 네이밍 + 에이전트가 읽는 네이밍 둘 다 해야. 너무 에이전트 위주만 ❌"

→ **이중 헤더 패턴**: `## 📌 결론 (Conclusion)`. 사람 친화 이모지 + 한글 + 에이전트용 영문 ID. 한 헤더에 두 의미.

## 4. 정책 일관성 (v0.7.6+)

| 정책 | 옛 (v0.7.5) | 새 (v0.7.6+) |
|---|---|---|
| Lite bootstrap 5종 | SCHEMA/RULES/AGENTS/AGENTS.md/PROJECT-WORKFLOW/log | **유지** |
| sync_meta lite | Lite 5종 | **유지** |
| **sync_meta full** | Tier 1 internal 포함 (9종) | **Lite 5종과 동일** (Tier 1 leak ❌) |
| 프로젝트워크플로우 헤더 | Runtime Inputs (영문 only) | **이중 헤더** (사람 + 에이전트) |
| vault mode | display-only metadata | **유지** |
| Tier 1 leak lint #14 | critical default | **유지** |

## 5. 다음 단계

- **v0.7.7 (후보)**: harumoa 운영자가 만든 페이지 (5phase-workflow, harumoa concept) 자동 검증 + wiki.db 빌드 + lint. 운영자 자유 존중 (vault 데이터 write ❌) → 가이드만.
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → Lite bootstrap 5종 → docs/vault-patterns.md 순서 정립.

## 6. 호환성

- ✅ **v0.7.5 사용자**: PROJECT-WORKFLOW.md 위치 변경 (templates/agent/), 본문 강화. 기능 영향 ❌.
- ✅ **Lite bootstrap 신규 vault**: 5종 자동 복사 (Tier 1 internal ❌).
- ✅ **기존 vault (raven-dev)**: PROJECT-WORKFLOW.md 새 템플릿으로 갱신. .bak 백업 보존.
- ✅ **사용자 vault (harumoa)**: 운영자 사용 중. 동기화 ❌.
- ⚠️ **sync_meta full 옵션**: 동작 변경 (Tier 1 internal ❌). 옛 정책 의존 코드/테스트는 v0.7.6+ 정책에 맞게 갱신됨.
- ⚠️ **옛 Runtime Inputs 키워드**: 새 본문에서 제거. test_lite_project_workflow_is_user_surface 갱신됨.