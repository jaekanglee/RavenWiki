# raven v0.6.29 — SelectField 공통 컴포넌트

> **핵심**: 인라인 `<label><span/><select/></label>` 패턴을 `<SelectField>` 공통 컴포넌트로 추출. TextField와 동일 API. 2개 select 인스턴스 교체.

릴리스 일자: 2026-06-29
이전: v0.6.28 (Button)

---

## 한 줄 요약

`dashboard/src/components/ui/SelectField.tsx` 신규 — label + options + helper/error + native select 위임. NewPageButton (문서 분류) + NewPageInline (type) 교체.

## 1. SelectField API

```tsx
const TYPE_OPTIONS = [
  { value: "concept", label: "일반 노트" },
  { value: "person", label: "사람" },
  ...
];

<SelectField
  label="문서 분류"
  value={type}
  onChange={(e) => setType(e.target.value)}
  options={TYPE_OPTIONS}
  required
  helper="문서 종류"
  error={err}
/>
```

TextField와 동일:
- label/required/helper/error
- native select attrs 위임 (value, onChange, disabled)
- `input-base` 클래스 (좌우 패딩 14px)

## 2. 변경 사항

### 2-1. `dashboard/src/components/ui/SelectField.tsx` (신규)

`forwardRef` + `useId` + `options.map(opt => <option>)` 패턴.

### 2-2. `dashboard/src/components/NewPageButton.tsx` (-25 / +9)

- 인라인 `<select>` 8개 옵션 + label 패턴 → `<SelectField options={TYPE_OPTIONS}>`
- TYPE_OPTIONS 상수 추출

### 2-3. `dashboard/src/components/NewPageInline.tsx` (-17 / +5)

- type select → `<SelectField>`
- TYPE_OPTIONS = TYPES.map() 변환
- path select는 dynamic placeholder/loading logic 때문에 그대로 (별도 패턴)

## 3. 회귀 가드 (`dashboard/tests/SelectField.test.tsx`, 5 tests)

1. label + options 렌더
2. required 시 `*` 표시
3. helper 텍스트
4. error 메시지
5. .input-base 클래스 보장

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **20 파일 / 102 tests + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |

## 5. 효과

| 항목 | 효과 |
|---|---|
| 인라인 `<label><select/>` 패턴 | 2곳 → 0곳 |
| 코드 라인 | -42 / +14 |
| TextField/SelectField 일관성 | ✅ |

## 6. 누적 공통 컴포넌트 (v0.6.20~29)

| 컴포넌트 | 용도 |
|---|---|
| `<TextField>` | 입력 (label + input + helper + error) |
| `<SelectField>` | 선택 (label + select + options + helper + error) |
| `<PageMetaRow>` | 페이지 메타 |
| `<Modal>` | 모달 컨테이너 |
| `<Button>` | 버튼 (variant/size/fullWidth) |

**AGENTS.md §13.1 완전 반영** — input/select/button 모두 공통 컴포넌트.

## 7. 후속 작업

- NewPageInline path select도 SelectField로 통일 (loading/placeholder 처리 추가 필요)
- HomePage/NewVaultWizard의 btn 인스턴스 교체
- 자가 사용 위임