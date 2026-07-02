# raven v0.7.57 — 워크스페이스 리사이저 + diff 배경색 강화 + 에디터 빌드 수정

> **핵심**: WorkspacePage 사이드바에 마우스/터치 드래그 리사이저를 추가(200~800px, leftWidth state + window-level event)하고, diff 라인의 추가/제거 배경색을 강화했습니다(불투명도 0.22). 또한 v0.7.56에서 누락된 `InlineMarkdownEditor`의 `filePathRow` prop 선언으로 TS2322 빌드 에러를 수정했습니다.

릴리스 일자: 2026-07-02
이전: v0.7.56

---

## 1. 변경 사항

### 1-1. `WorkspacePage` — 사이드바 드래그 리사이저

- `leftWidth` state 추가 (기본 360px, 200~800px clamp)
- divider에 `onMouseDown` / `onTouchStart` 바인딩 → window-level `mousemove` / `touchmove` / `mouseup` / `touchend`
- `useCallback` + `useRef`로 핸들러 메모이즈, unmount 시 cleanup
- 107줄 추가 (WorkspacePage)

### 1-2. `globals.css` — diff 배경색 강화

- `.diff-add` / `.diff-remove` 배경색: 추가된 줄 초록, 제거된 줄 붉은
- 불투명도 0.22 → 0.28 (v0.7.55 이전 0.12에서 단계적 강화)
- 38줄 수정 (다크/라이트 양쪽 일관)

### 1-3. 빌드 수정 — `InlineMarkdownEditor` TS2322

- v0.7.56에서 `filePathRow` prop을 **사용**했으나 **선언 안 함** → TS2322 빌드 에러
- v0.7.57에서 `filePathRow?: React.ReactNode` props 추가 (v0.7.56 hotfix 일부)
- v0.7.56의 changelog에 반영 안 됨 → v0.7.57 hotfix로 보강

### 1-4. 부수 변경

- `_meta/changelog-v0.7.9.md` — 18줄 (v0.7.57 hotfix 노트 박음 — 사용자가 v0.7.9의 hotfix 섹션으로 추가)

---

## 2. 검증 결과

| 항목 | 결과 |
|---|---|
| `tsc -b` (Dashboard) | exit 0 (TS2322 해결) |
| `npm run build` | exit 0 |
| `pytest tests/ -q` | 550 passed, 2 skipped |
| 리사이저 동작 | 마우스/터치 드래그 → divider 위치 변경, 200~800px clamp |

---

## 3. 호환성

- ✅ WorkspacePage 기존 사용처 (워크스페이스 조회, 파일 읽기/쓰기) 변경 ❌
- ✅ diff 색상 강화는 시각적, contract 무변경
- ✅ InlineMarkdownEditor props 추가는 backward compatible

---

## 4. 다음에 가능한 것

- **Lite bootstrap 4종 갱신** — v0.7.55 raw/ 정책 + v0.7.57 시각 가이드 (diff 색상 등)
- **리사이저 모바일 지원** — 현재 mouse + touch 지원, 모바일 drawer 패턴 점검
- **diff 색상 토큰화** — `--color-diff-add` / `--color-diff-remove` CSS 변수 분리

---

## 5. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: 리사이저 + diff 색상 + 빌드 수정 의도 명확
- [x] **단순성 (YAGNI)**: 1-3 변경만, 부수 변경 최소
- [x] **Surgical (§3)**: 3 files, 139/-24 (WorkspacePage 107 + globals.css 38)
- [x] **Goal-Driven**: 빌드 ✅ + 회귀 없음
- [x] **4 저장 신호**: 시간축 보존 (v0.7.9 hotfix 섹션에도 추가) ✓
