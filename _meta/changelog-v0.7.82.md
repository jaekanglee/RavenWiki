# Changelog v0.7.82 — VaultManage banner 자세히 모달 + DashboardDigest 검토 (2026-07-06)

> **BLUF**: 사용자 진단 흐름 (1+2 묶음) — VaultManage bulk banner가 *어떤 파일이* 불일치하는지 안 보여 UX 단절. `<Modal>` 컴포넌트(v0.6.26+) 활용하여 mismatch/missing/empty 파일 목록 모달. DashboardDigest 잔여 ✓/⚠는 검토 결과 *text 안쪽*이라 skip.
>
> 이전 changelog: `_meta/changelog-v0.7.81.md`

---

## §0 — commit 1개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `563555b` | A. VaultManage banner 자세히 모달 | `dashboard/src/routes/VaultManage.tsx` | +108/−1 |

---

## A. VaultManage banner 자세히 모달 (`563555b`)

### 진단 배경

v0.7.75 banner는 *vault 이름 + 'X개 일치하지 않음' + 일괄 업뎃 버튼*만 노출. 운영자가 *어떤 파일이* 불일치하는지 보려면 verify-all 응답 JSON을 다른 곳에서 봐야 했음 — UX 단절.

### 변경

| 영역 | 변경 |
|---|---|
| `bootstrapDetail` state | `useState<string \| null>(null)` (vault 이름 보관) |
| `Modal` 컴포넌트 import | v0.6.26+ |
| banner 버튼 추가 | `'자세히 →'` (pillSecondary) — 첫 mismatched vault 모달 오픈 |
| Modal 내용 | vault 이름 + status chip + summary + 파일 목록 3종 |
| Modal 액션 | `[닫기]` / `[이 vault 지침 업뎃]` |

### Modal 표시 항목

- **Mismatch 파일** (monospace, danger color) — `wiki_lint`가 보고한 hash 불일치 파일
- **Missing 파일** (monospace, danger color) — Lite bootstrap 3종 중 없는 것
- **Empty 파일** (monospace, muted color) — `log.md` 등 append-only 빈 상태
- 모두 비어있으면 "모든 Lite bootstrap 파일이 원본 템플릿과 일치합니다" success 메시지

### §13 적용

- §13.1: `<Modal>` / `<Button>` 컴포넌트 (v0.6.26+, v0.6.28+)
- §13.2: 색/배경 CSS 변수만, 구조(grid/flex/gap) 인라인

### data-testid

- `bulk-bootstrap-detail` — banner 자세히 버튼
- `bootstrap-detail-update` — 모달 내 업뎃 버튼

**검증**: tsc -b --noEmit clean.

---

## DashboardDigest 잔여 ✓/⚠ 검토 (skip, 보고만)

사용자 요청 2번: `DashboardDigest.tsx line 295 ✓/⚠ 잔여`.

### 검토 결과

```tsx
title={lint.ok ? "✓ critical 없음" : `⚠ critical ${counts.critical}건`}
```

→ ✓/⚠가 *digest 카드 title 텍스트 안쪽*. v0.7.71 v0.7.72 사이클에서 정한 정책:

> "Toast 메시지 안 ✓/⚠는 의도적 — `✅ 보관소 검증 성공` 같은 *메시지 text 안쪽*은 OK"

`DashboardDigest.tsx`의 `title` prop도 동일 패턴 — **카드 제목 텍스트로 사용**.

§P (ui-ux 스킬 §P, "이모지 ❌, Lucide SVG")는 *아이콘 역할*에 적용. text 안쪽 + 단일 문자 표시는 §P 적용 외.

### 결론

- 변경 불필요
- 만약 *아이콘으로 분리*하고 싶다면 `<LucideIcon.Check />` / `<AlertTriangle />`로 분리 가능하지만 over-scope (text 안에 이미 충분)

→ **skip**.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` (dashboard) | clean |
| `git push origin master` | 완료 |

---

## §2 — 외부 운영자 walkthrough

> "운영자가 VaultManage 페이지 진입"

1. 진입 시 자동 verify-all → 불일치 vault 있으면 banner 노출
2. banner에 vault 이름 + 'X개 일치하지 않음' + 일괄 업뎃 버튼 + **자세히 →**
3. **자세히 →** 클릭 → `<Modal>` 열림
4. Modal에서 mismatch 파일 목록 확인 (예: `_meta/agents/PROJECT-WORKFLOW.md`)
5. **[이 vault 지침 업뎃]** 클릭 → 모달 닫히고 일괄 업뎃 함수 호출
6. 업뎃 후 자동 재검증 → banner 사라짐

---

## §3 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.75 | VaultManage 자동 verify-all + banner 일괄 업뎃 |
| v0.7.81 | HTTP-only 재설계 (3 파일) |
| v0.7.82 | **banner 자세히 모달 + DashboardDigest 검토 (skip)** |

→ v0.7.75 banner UX 단절 해소. 운영자가 *어떤 파일이* 불일치하는지 즉시 확인 가능.