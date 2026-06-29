# raven v0.6.28 — Button 공통 컴포넌트 + 4 모달 교체

> **핵심**: 모달 안 인라인 버튼 (취소/저장/삭제) 반복 패턴을 `<Button>` 공통 컴포넌트로 추출. variant (primary/secondary/danger/ghost) + size (sm/md/lg) + fullWidth.

릴리스 일자: 2026-06-29
이전: v0.6.27 (Modal 통일 4/4)

---

## 한 줄 요약

`dashboard/src/components/ui/Button.tsx` 신규 — variant/size/fullWidth 옵션 + native button attrs 위임. 4개 모달의 취소/저장/삭제 버튼 8개 교체 (-90 / +30줄).

## 1. Button API

```tsx
<Button variant="primary" onClick={save}>저장</Button>
<Button variant="secondary" onClick={() => setOpen(false)}>취소</Button>
<Button variant="danger" onClick={del}>삭제</Button>
<Button variant="ghost" size="sm">세부 옵션</Button>
<Button fullWidth>메인 CTA</Button>
```

| variant | class | 용도 |
|---|---|---|
| primary | btn-primary | 메인 액션 (저장, 만들기) |
| secondary | btn-secondary | 보조 액션 (취소) |
| danger | btn-primary + 빨간 배경 | 위험 액션 (삭제) |
| ghost | btn-tertiary | 텍스트만 (토글, 링크) |

| size | height | 용도 |
|---|---|---|
| sm | 34px | 보조 토글 |
| md | 40px | 기본 — 모달 버튼 |
| lg | 48px | 메인 CTA |

## 2. 변경 사항

### 2-1. `dashboard/src/components/ui/Button.tsx` (신규)

- `forwardRef` + native button attrs 위임
- variant → className 매핑 + danger만 inline 빨간 배경

### 2-2. `dashboard/src/components/DeleteButton.tsx` (-18 / +6)

취소(`secondary`) + 삭제(`danger`) 버튼 교체.

### 2-3. `dashboard/src/components/EditButton.tsx` (-18 / +6)

취소 + 저장(`primary`) 교체.

### 2-4. `dashboard/src/components/NewFolderButton.tsx` (-18 / +6)

동일.

### 2-5. `dashboard/src/components/NewPageButton.tsx` (-18 / +6)

동일.

## 3. 회귀 가드 (`dashboard/tests/Button.test.tsx`, 7 tests)

1. label 렌더
2. variant="primary" → btn-primary class
3. variant="secondary" → btn-secondary class
4. variant="danger" → 빨간 inline 배경
5. disabled → click handler 무력화
6. size="sm" → height 34px
7. fullWidth → width 100%

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **19 파일 / 97 tests pass + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke | 모달 버튼 className btn-secondary + btn-primary, height 40px 양쪽 |

## 5. 효과

| 항목 | 효과 |
|---|---|
| 4 모달 버튼 라인 | -72 / +24 (-48줄) |
| 인라인 `<button className="btn-..." style={...}>` | 16개 → 8개 |
| 새 버튼 작성 비용 | ~3줄 (`<Button variant="primary">...</Button>`) |
| 일관성 | 4 모달 모두 동일 variant 규약 |

## 6. 누적 공통 컴포넌트 (v0.6.20~28)

- `<TextField>` — 입력
- `<PageMetaRow>` — 페이지 메타
- `<Modal>` — 모달 컨테이너
- `<Button>` — 버튼

**AGENTS.md §13.1 원칙 코드에 완전 반영** — 인라인 label/input/button 반복 ❌.

## 7. 후속 작업

- `<SelectField>` 공통 컴포넌트 (select 인풋)
- HomePage/NewPageInline/NewVaultWizard의 btn 인스턴스도 Button 교체 (별도 패치)
- 자가 사용 위임 (wiki-self-user)