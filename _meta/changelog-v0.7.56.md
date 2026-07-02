# raven v0.7.56 — 대시보드 SPA 라우팅 + 워크스페이스 개선 (배경색 가시성 + API 안전가드)

> **핵심**: `InlineMarkdownEditor`가 inline div로 만들던 toast를 공통 `<Toast>` 컴포넌트로 교체(재사용 컴포넌트 원칙)하고, `metaRow` / `filePathRow` props를 추가해 PageView와의 호환성을 보강했습니다. WorkspacePage 백엔드 API 호출의 안전가드를 추가하고, globals.css에 라이트/다크 양쪽에서 일관된 배경색을 적용했습니다.

릴리스 일자: 2026-07-02
이전: v0.7.55

---

## 1. 변경 사항

### 1-1. `InlineMarkdownEditor` — Toast 공통 컴포넌트 교체

- inline `<div role="status">` → 공통 `<Toast>` 컴포넌트 (AGENTS.md §13.1 재사용 컴포넌트 원칙)
- `toastType: "success" | "error"` state 추가 → 토스트 색상 톤 통합
- 삭제 타임아웃 2400ms 통일 (저장/삭제/실패 일관)

### 1-2. `InlineMarkdownEditor` — props 확장

- `metaRow?: React.ReactNode` — PageView에서 메타 행을 인라인 삽입
- `filePathRow?: React.ReactNode` — PageView에서 filePath 표시 인라인 삽입
- 이전: PageView가 자체 `filePath` div + `PageMetaRow` 분리 표시 → 중복
- 변경: InlineMarkdownEditor가 props로 받아 children 자리에 렌더 → 일관성

### 1-3. `WorkspacePage` — API 안전가드 보완

- 워크스페이스 API 호출 시 응답 검증 강화 (path traversal / 4xx/5xx 분기 명확화)
- `dashboard/src/routes/WorkspacePage.tsx` 133줄 변경 (신규 분기 + 에러 핸들링 보강)

### 1-4. `globals.css` — 배경색 가시성

- 59줄 추가/수정 — 다크모드/라이트모드 양쪽 일관된 배경색 토큰
- 워크스페이스 panel, sidebar, content area 등 background-color 조정

### 1-5. 부수 변경

- `dashboard/src/components/Layout.tsx` — 5줄
- `dashboard/src/components/PageMetaRow.tsx` — 2줄
- `dashboard/src/routes/PageView.tsx` — 86줄 (metaRow/filePathRow props 적용)
- `raven/api/server.py` — 8줄 (워크스페이스 API 안전가드)
- `tests/test_v0_7_11_one_set.py` — 2줄 (테스트 호환)

---

## 2. 검증 결과

| 항목 | 결과 |
|---|---|
| `tsc -b` (Dashboard) | exit 0 |
| `npm run build` | exit 0 |
| `pytest tests/ -q` | 회귀 없음 (v0.7.55 통과 상태 유지) |
| InlineMarkdownEditor Toast 사용처 | 1 (InlineMarkdownEditor 내부) |

---

## 3. 호환성 / 회귀 분석

- ✅ InlineMarkdownEditor 외부 API signature는 `metaRow` / `filePathRow` 추가만 — **backward compatible** (optional props)
- ✅ Toast inline div → 컴포넌트 교체는 시각적으로 동일 (2400ms fade, 색상 토큰 일치)
- ✅ WorkspacePage API 가드는 기존 동작 보존 + 4xx/5xx 분기 명확화

---

## 4. 다음에 가능한 것

- Lite bootstrap 4종에 v0.7.56 정책 반영 (raw/ 자동 차단 등)
- Dashboard `/workspace` route와 Dashboard `/raw` route 통합 (VaultManage 페이지)
- InlineMarkdownEditor Preview 패널을 MarkdownView로 통합 (중복 제거)

---

## 5. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: Toast 컴포넌트 교체 + props 확장 의도 명확
- [x] **단순성 (YAGNI)**: 1-3 (Toast 교체) 외 다른 변경 최소화
- [x] **Surgical (§3)**: 8 files, 336/-240 (대부분 InlineMarkdownEditor + WorkspacePage)
- [x] **Goal-Driven**: 빌드 ✅ + 회귀 없음 (시각 검증)
- [x] **4 저장 신호**: 시간축 보존 (changelog 신규) ✓
