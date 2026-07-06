# Changelog v0.7.75 — VaultManage 진입 시 자동 verify-all + 일괄 업뎃 (2026-07-06)

> **BLUF**: 사용자 정확한 진단 (2026-07-06) — "VaultManage 페이지에 1) 모든 vault에 일괄 지침/MCP 업뎃 버튼, 2) 페이지 진입 시 vault별 지침 일치여부 자동 검사 + 불일치 vault 표시". per-feature commit 2개.
>
> 이전 changelog: `_meta/changelog-v0.7.74.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `4ec4bcd` | A. 백엔드 `POST /api/vaults/verify-all` 추가 | `raven/api/server.py` | +52 |
| `5a1599a` | B. VaultManage — 진입 시 자동 verify-all + 일괄 업뎃 banner + vault row chip | `dashboard/src/routes/VaultManage.tsx` | +154/−1 |

---

## §A — 진단 배경

**사용자 정확한 진단 (2026-07-06)**:
> 1. "VaultManage 페이지에 모든 vault에 일괄 지침/MCP 업뎃 버튼"
> 2. "눌러야 검사하는게 아니라 페이지 진입 시 vault별 지침 일치여부 검사해서 안맞는 vault 표디해줬음 함"

**RAG 발견**:
- 기존 `POST /api/vaults/{name}/verify` (단일 vault, 409 on mismatch) — `/verify-all` 없음
- 기존 `POST /api/vaults/{name}/bootstrap` (단일 vault 갱신) — 일괄 갱신 endpoint 없음
- 기존 VaultManage 페이지: vault별 verify/bootstrap 버튼 (L96, 467) 있지만 **자동 검사/일괄 액션 없음**

---

## A. 백엔드 `POST /api/vaults/verify-all` (`4ec4bcd`)

신규 endpoint. 모든 등록 vault에 대해 `Vault.verify_bootstrap()` 호출 → per-vault 결과 + aggregate 반환.

### 응답 스키마

```json
{
  "ok": true,                  // 모든 vault 일치 시 true
  "total": 3,
  "ok_count": 2,
  "mismatch_count": 1,
  "results": [
    {
      "name": "vault-a",
      "ok": true,
      "mismatched_files": [],
      "missing_files": [],
      "empty_files": [],
      "summary": "ok"
    },
    {
      "name": "vault-b",
      "ok": false,
      "mismatched_files": ["_meta/agents/PROJECT-WORKFLOW.md"],
      "missing_files": [],
      "empty_files": [],
      "summary": "1 mismatch, 0 missing"
    }
  ]
}
```

### 정책

- **per-vault mismatch 시 409 ❌** — list view로 렌더링되어야 하므로 try/except로 흡수
- per-vault error (corrupt vault, missing dir)는 `{"name": ..., "ok": false, "error": ...}` 반환
- 기존 endpoint (`/verify`, `/bootstrap`) 변경 없음 — backward compatible

**검증**: import OK.

---

## B. VaultManage UI (`5a1599a`)

### 자동 검사

- `loadBootstrapStatus()` 함수 — `verify-all` 호출 후 `bootstrapStatus` state에 저장
- `loadVaults()` 끝에서 자동 호출 → **사용자 누름 불필요, 진입 즉시 검사**
- 페이지 이미 떠 있는 동안 verify 실패는 silent (페이지 로딩 차단 안 함)

### 일괄 업뎃

- `handleBulkUpdateBootstrap()` — `bootstrapStatus[name].ok === false`인 vault들에 대해 per-vault `POST /bootstrap` 루프
- 성공/실패 카운트 Toast 표시
- 업뎃 후 자동 `loadBootstrapStatus()` 재호출

### UI 표시

**상단 banner** — 진입 시 자동 노출:
- 배경 `var(--color-surface-soft)` + warning border
- "⚠ N개 vault의 지침이 원본 템플릿과 일치하지 않습니다"
- 불일치 vault 이름 나열 + 부연 설명
- 우측 `<Button variant="pillPrimary">🔄 N개 vault 일괄 업뎃</Button>`
- `bulkUpdating` 동안 disabled + "업뎃 중…" 라벨

**vault row chip** — 각 vault의 mode chip 옆:
- 일치 시: `✓ 지침 일치` (success 배경/텍스트)
- 불일치 시: `⚠ 지침 불일치` (danger 배경/텍스트)
- `title` attr에 summary 표시 (hover 시 mismatch/missing 파일 목록)

### §13 적용

- **§13.1**: `<Button>` 컴포넌트 (v0.6.28+) 사용
- **§13.2**: 색/배경 모두 CSS 변수 (`var(--cds-support-success)`, `var(--cds-danger)` 등)

### data-testid (테스트 selector)

- `bulk-bootstrap-banner` — banner 전체
- `bulk-bootstrap-update` — 업뎃 버튼
- `bootstrap-status-<vault-name>` — 각 vault row chip

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `python -c "from raven.api.server import app"` | import OK |
| `tsc -b --noEmit` (dashboard) | clean |
| `git push origin master` | 완료 |

---

## §2 — 외부 에이전트 walkthrough (사용자 시나리오)

> "사람 운영자가 VaultManage 페이지 진입"

1. 페이지 로드 → vault list + **즉시 verify-all 자동 호출**
2. 모두 일치 시: banner 안 보임, 모든 vault row에 `✓ 지침 일치`
3. 일부 불일치 시:
   - 상단 banner: "⚠ 2개 vault의 지침이 원본과 일치하지 않습니다 (raven-dev, archive)"
   - 해당 vault row: `⚠ 지침 불일치` chip (빨강)
   - 일괄 업뎃 버튼 노출
4. 클릭 → per-vault `POST /bootstrap` 루프 → 업뎃 + 재검증 → banner 사라짐
5. 일부는 OK, 일부는 partial mismatch 시 Toast로 "성공 N, 실패 M" 안내

---

## §3 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.69-73 | Dashboard §13 통일 (5 사이클) |
| v0.7.74 | PROJECT-WORKFLOW.md vault 진입 가이드 강화 + Wizard MCP snippet |
| v0.7.75 | **VaultManage 자동 verify-all + 일괄 업뎃 banner** |

→ "Lite bootstrap 정책" (v0.7.65+) + "M4 Trust & Tier safety" (verify.py) 정신 연속선.
사용자가 일일이 버튼 누르지 않아도 vault 운영자가 *자각* 없이 지문이 outdated인 vault를 발견 가능.