# Changelog v0.7.94 — Lite bootstrap 3종 diff (vault vs raven install 템플릿)

> **BLUF**: 운영자가 "내 vault의 Lite bootstrap 3종이 왜 mismatch?" 즉시 진단 가능. **drawer 안에 Preview/Diff 토글** (compact mode 한정, Jira/Notion split view). unified diff는 **Python `difflib` 표준 라이브러리** (외부 의존성 0, AGENTS.md §10 "의존성 추가 without 승인 ❌" 정합). 200줄 초과 truncation. 화이트리스트 3종 fail-closed 동일. 회귀 639/639 PASS (v0.7.93 baseline 631 + 8 신규).

이전 changelog: `_meta/changelog-v0.7.93.md`

---

## §0 — 변경 요약 (3 파일 수정 + 1 신설)

| 파일 | 변경 | LOC |
|---|---|---|
| `raven/api/server.py` | `GET /api/vaults/{name}/guide-diff/{kind:path}` endpoint + `_LITE_TEMPLATE_MAP` + `_LITE_TEMPLATE_SRC` 화이트리스트 + `difflib.unified_diff` 통합 | +127 |
| `dashboard/src/lib/api.ts` | `fetchGuideDiff()` + `LiteGuideDiffLine` + `LiteGuideDiffResult` 타입 | +27 |
| `dashboard/src/components/GuidesViewer.tsx` | viewMode state (preview/diff) + `DiffView` / `DiffLineRow` 컴포넌트 + Preview/Diff 토글 (compact 한정) + diff 로딩 useEffect | +200 |
| `tests/test_v0_7_94_guide_diff.py` (신설) | 회귀 8 tests (정상 / identical / 403 / 404 / truncation) | +218 |
| `_meta/changelog-v0.7.94.md` (신설) | 본 changelog | — |

---

## §1 — 무엇을 만들었나

### 1.1 API contract

```
GET /api/vaults/{name}/guide-diff/{kind}
```

**URL 디자인 결정 (v0.7.94 cycle 중 발견)**: 처음엔 `/api/vaults/{name}/guide/{kind:path}/diff` 로 design 했으나, FastAPI `{kind:path}` 가 `/diff` 까지 흡수 (`_meta/agents/SCHEMA.md/diff` 전체가 kind로 매칭) → `/guide-diff/{kind:path}` 로 변경. **테스트에서 발견 + 즉시 fix** (TDD 정합).

응답 shape:
```json
{
  "ok": true,
  "vault": "...",
  "kind": "_meta/agents/SCHEMA.md",
  "identical": false,
  "template_path": "/.../raven/core/templates/agent/SCHEMA.md",
  "diff_lines": [
    {"tag": " ", "content": "..."},  // 동일 라인
    {"tag": "-", "content": "..."},  // 템플릿에만
    {"tag": "+", "content": "..."}   // vault에만
  ],
  "stats": {"added": 1, "removed": 1, "equal": 50},
  "truncated": false,
  "truncation_note": null
}
```

### 1.2 Frontend — drawer 안 Preview/Diff 토글

GuidesViewer 헤더 우측 (compact mode = drawer):
- 기존: `↻ 새로고침` `✕ 닫기`
- v0.7.94+: + **`[Preview] [Diff]` 토글** (segmented control)

Diff 선택 시:
- `fetchGuideDiff` 자동 호출
- `DiffView` 컴포넌트 렌더 — 상단 stats (`+1 / -1 / vs raven 설치 템플릿`), unified diff 본문
- `identical=true` 면 ✓ success 배너
- 200줄 초과 시 truncation warning

CSS 토큰 활용: `var(--color-success-bg/text)` / `var(--color-danger-bg/text)` / `var(--color-warning-bg/text)` (Dashboard globals.css 기존 토큰, 신규 0).

### 1.3 `difflib` 표준 (외부 의존성 0)

`difflib.unified_diff` — Python 표준 라이브러리. AGENTS.md §10 "의존성 추가 without 사용자 승인 ❌" 정합. **의존성 0 추가**.

Truncation 200줄 — `difflib`은 200줄+ diff에서 가독성 급감 (PROJECT-WORKFLOW.md 333줄 → diff 200줄+). 200줄 cap + "전체 비교는 CLI `diff` 사용" 안내.

## §2 — 왜 drawer 한정인가 (page vs drawer)

사용자 워크플로우:
- **page** (`/guides`): 자유 vault 변경 + 비교 — standalone. drawer 토글 불요.
- **drawer** (VaultManage 우측): mismatch 진단이 **즉시 가치** — "이 vault만 보고 끝" — compact mode 한정 토글이 surgical.

→ 토글은 `compact &&` 조건. page에서는 항상 Preview (MarkdownView). drawer에서만 Preview/Diff 선택.

## §3 — 403 / 404 / 200 / truncation 매트릭스

| 시나리오 | 응답 |
|---|---|
| 화이트 kind (3종) + vault 존재 + 파일 존재 | **200**, identical or diff_lines |
| 화이트 kind + vault 부재 | **404** "vault not found" |
| 화이트 kind + vault 존재 + 파일 부재 | **404** "guide file not present" |
| 비화이트 kind (e.g. `_meta/system/...`) | **403** "not in whitelist" (Tier 1 leak 방지) |
| 비화이트 kind (e.g. `content/note.md`) | **403** (가이드 surface = Lite bootstrap만) |
| diff > 200줄 | **200**, `truncated: true` + `truncation_note` |
| raven install template 부재 (corruption) | **500** (즉시 알림) |

## §4 — 검증

### 4.1 신규 가이드 diff 테스트

```
tests/test_v0_7_94_guide_diff.py:: 8/8 PASS
  ├─ test_diff_schema_returns_modified        PASS
  ├─ test_diff_project_workflow_200            PASS
  ├─ test_diff_log_md_200                      PASS
  ├─ test_diff_identical_returns_no_changes    PASS  (SCHEMA/WORKFLOW만)
  ├─ test_diff_rejects_non_whitelist_403       PASS
  ├─ test_diff_rejects_content_path_403        PASS
  ├─ test_diff_404_for_unknown_vault           PASS
  └─ test_diff_truncates_at_200_lines          PASS
```

**identical 픽스처 한계 명시**: `log.md` 는 v0.7.65+ Lite bootstrap 정책상 `ensure_log()` 가 vault create 시 자동 append entry를 박음 (silent write 방지, README §8/§9). 따라서 template과 byte-equal 일 수 없음 → SCHEMA/PROJECT-WORKFLOW 만 identical 검증. 정책 정합.

### 4.2 회귀

```
$ pytest tests/ -q --ignore=tests/curator
639 passed, 1 skipped, 1 warning in 40.38s
```

(v0.7.93 baseline 631 + 8 신규 = 639, 0 회귀)

### 4.3 Dashboard build

```
$ cd dashboard && npm run build
✓ built in 1.82s
```

## §5 — AGENTS.md / SCHEMA.md / Lite bootstrap 정책 영향

- **AGENTS.md §4 (Lite bootstrap 정책)**: 변경 없음. 3종 그대로, **diff endpoint 는 진단용 (read-only)**. `ensure_log()` 자동 append 정책 (§4 silent write 방지) 보존.
- **AGENTS.md §10 (의존성 정책)**: 정합. `difflib` 표준 라이브러리 사용, 신규 의존성 0.
- **SCHEMA.md**: 변경 없음.
- **NORTH STAR (원문 보존 + 증분 누적)**: 보존. `wiki_update` 1.5배 차단 / 권한 / Tier 1 leak 방지 모두 그대로.

## §6 — 후속 작업 (deferred)

- **diff endpoint MCP 표면** (`wiki_get_guide_diff`): v0.7.91 `wiki_get_guide` 패턴 따라 추가 검토. 에이전트가 "내 vault 지침이 mismatch?" 진단 가능.
- **diff view drawer 외부 확장** (다른 Lite bootstrap 정책 위반 파일 진단): 범위 확장 시 ADR 검토.
- **CLI `raven guide diff`**: 운영자가 터미널에서 동일 diff 가능. dashboard drawer 가치 보강.
