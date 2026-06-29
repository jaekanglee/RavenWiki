# raven v0.6.21 — PageMetaRow + 📑 Index 마커

> **핵심**: 사용자 의도 "Type ADR 자동 표시 + 📑 Index 자동 표시" 재해석. 페이지 메타 row를 `<PageMetaRow>` 공통 컴포넌트로 추출 + slug가 `content/index` 일 때 📑 Index 마커 추가.

릴리스 일자: 2026-06-29
이전: v0.6.20 (TextField)

---

## 한 줄 요약

`dashboard/src/components/PageMetaRow.tsx` 신규 — type chip + 📑 Index 마커 + updated + tags #pill을 한 컴포넌트로. PageView의 인라인 메타 row를 교체. slug가 `content/index` 또는 `index` 일 때 📑 chip 추가.

## 1. 사용자 의도 재해석

사용자 질문: "보통 옵시디언도 있다는 얘기야?" — Obsidian은 **index 자동 생성 ❌** (사용자가 직접 만듦). "Index 자동 표시"의 자연스러운 의미는 페이지 헤더에 시각적 강조. 

결론:
- Type ADR 자동 표시 = 이미 `<span className="chip-strong">{page.type}</span>` 로 표시 중
- 📑 Index 자동 표시 = slug가 `content/index` 일 때 📑 마커 chip 추가

## 2. 변경 사항

### 2-1. `dashboard/src/components/PageMetaRow.tsx` (신규)

```tsx
<PageMetaRow
  type="concept"
  slug="content/index"
  tags="raven, home, index"
  updated="2026-06-29"
/>
```

렌더 결과:
```
[concept] [📑 Index] updated 2026-06-29 [#raven] [#home] [#index]
```

- `isIndexSlug(slug)` — `content/index` 또는 `index` 매칭 (v0.6.15 P15 prefix tolerance)
- 📑 Index chip은 `cds-background-brand` 배경 + `color-primary` 색

### 2-2. `dashboard/src/routes/PageView.tsx` (-25 / +5)

- 인라인 meta row 제거 → `<PageMetaRow>` 한 줄
- `page.slug || page.path` 로 slug fallback

## 3. 회귀 가드 (`dashboard/tests/PageMetaRow.test.tsx`, 6 tests)

1. type chip 렌더
2. slug = `content/index` → 📑 표시
3. slug = `index` → 📑 표시 (prefix tolerance)
4. slug = 다른 거 → 📑 안 표시
5. tags → `#pill` #pill
6. updated 날짜 표시

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **15 파일 / 81 tests pass** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke | `/page/raven-dev/content/index`에서 `concept | 📑 Index | updated 2026-06-29 | #raven #home #index` 확인 |

## 5. 효과

| 항목 | 효과 |
|---|---|
| PageView 라인 수 | -20 (인라인 → 컴포넌트) |
| 다른 페이지 재사용 | 가능 (PageMetaRow export) |
| Index 시각 강조 | 📑 chip으로 vault 진입점 명확화 |

## 6. 후속 작업 후보

- Task 2: folder hover 메뉴 (Sidebar에 인라인 + 버튼)
- Task 3: 남은 3개 사용처 TextField 교체 (NewVaultWizard/NewPageInline/DeleteButton)
- Task 4: MiniMax 회귀 검증
- 다른 페이지(설정, lint page 등)에도 PageMetaRow 재사용