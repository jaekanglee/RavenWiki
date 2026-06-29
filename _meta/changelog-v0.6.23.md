# raven v0.6.23 — TextField 사용처 확장 (3 컴포넌트)

> **핵심**: v0.6.20 TextField의 surgical 확장으로 남은 3개 사용처(NewVaultWizard/DeleteButton/NewPageInline) 교체. 인라인 label+input 반복 제거 + 좌우 패딩 일관성.

릴리스 일자: 2026-06-29
이전: v0.6.22 (folder hover menu)

---

## 한 줄 요약

`NewVaultWizard` 1개 + `DeleteButton` 1개 + `NewPageInline` 2개 = **총 4개 인라인 input**을 `<TextField>`로 교체. select 인풋은 TextField 미지원 — 그대로 유지.

## 1. 사용자 원칙 적용 (v0.6.20 §13)

AGENTS.md §13.1: "인라인 `<label><span/><input/></label>` 패턴 ❌". surgical — 한 컴포넌트씩 점진 도입.

## 2. 변경 사항

### 2-1. `dashboard/src/components/NewVaultWizard.tsx` (-21 / +10)

- **Step 1의 "이름 *" 입력** → `<TextField required>`
- autoFocus + onKeyDown (Enter → onNext) 그대로 위임
- Step 2의 "경로 (자동)" readOnly input은 inline 유지 (회색 monospace + uppercase label = 다른 시각 의도)

### 2-2. `dashboard/src/components/DeleteButton.tsx` (-19 / +5)

- **"확인 — slug 입력"** → `<TextField>`
- monospace font는 style prop으로 전달

### 2-3. `dashboard/src/components/NewPageInline.tsx` (-25 / +18)

- **title *, tags** 2개 input → `<TextField required>` / `<TextField>`
- path/type select 2개는 그대로 (TextField는 select 미지원)
- "new-dir" 인라인 input은 label 없음 → 그대로 유지

## 3. 범위 결정

| 사용처 | 교체 | 이유 |
|---|---|---|
| NewPageButton.tsx (v0.6.19) | ✅ 이미 완료 | — |
| NewFolderButton.tsx (v0.6.20) | ✅ 이미 완료 | — |
| NewVaultWizard.tsx 이름 | ✅ 이번 | label 있는 input |
| NewVaultWizard.tsx 경로(자동) | ❌ 유지 | readOnly + 다른 시각 (monospace 회색) |
| DeleteButton.tsx slug 확인 | ✅ 이번 | label 있는 input |
| NewPageInline.tsx title | ✅ 이번 | label 있는 input |
| NewPageInline.tsx tags | ✅ 이번 | label 있는 input |
| NewPageInline.tsx path/type | ❌ 유지 | select |
| NewPageInline.tsx new-dir | ❌ 유지 | label 없는 인라인 |

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **16 파일 / 82 tests pass** (회귀 0) |
| tsc -b | **exit 0** |

## 5. 후속 작업 (별도 패치)

- **DeleteButton Portal 미적용** (v0.6.18 모달 Portal 패턴) — 같은 버그 가능성
- **NewPageInline Portal 미적용** — 동일
- **EditButton Portal 미적용** — 미확인
- **SelectField 공통 컴포넌트** (select 인풋용) — 사용자 원칙 §13.1

## 6. 효과

| 항목 | 효과 |
|---|---|
| 인라인 label+input 라인 | -65 / +33 (-32줄) |
| 좌우 패딩 일관성 | 5개 사용처 모두 14px 보장 |
| 코드 추적성 | 한 곳(TextField) 수정 → 5개 사용처 자동 반영 |