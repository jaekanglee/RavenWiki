---
title: Changelog v0.7.115
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.115 — Dashboard 라이트 모드 표/인라인 코드 톤 통일

## 무엇을 했는가

- **문제**: `@uiw/react-md-editor`가 inject하는 GitHub 기본 스타일 때문에 라이트 모드에서:
  - 표: 파란 링크 + 줄무늬 + 회색 톤 → 라이트 캔버스와 어긋남
  - 인라인 코드: 어두운 slate-800 배경 + sky-300(#7dd3fc) 파란 글씨 → 다크 톤이 라이트에 박힘
- **원인**: `globals.css`는 `.prose table` / `.prose code`만 정의하고 `wmde-markdown` 셀렉터는 빠져 있었음. v0.7.56+ pre 강제 override만 있었지 표/인라인 코드는 강제 없음
- **수정** (globals.css v0.7.114 패치 뒤 약 39줄 추가):
  - `[data-color-mode="light"] .wmde-markdown :not(pre) > code` — 연회색(`#f1f5f9`) bg + slate-200 border + 잉크 color
  - `[data-color-mode="light"] .wmde-markdown table` — `var(--color-surface)` 흰 배경 + `var(--color-hairline)` 회색선 + 잉크 텍스트
  - 헤더 행은 `var(--color-surface-soft)` 1톤 강조
  - 줄무늬(`tr:nth-child(even)`) 제거 — 깔끔하게
  - 표 안 링크는 primary 파란색 유지 (가독성)
  - 다크 모드는 L2488~2492 그대로 보존

## 왜 그렇게 했는가 (§5 4 신호)

- **인수인계 필요성**: 다음 세션/사용자가 "왜 표는 흰색인데 코드는 파란색이야?" 라고 묻지 않게 — 라이트/다크 톤이 모두 디자인 토큰 기반
- **scope/provenance 추적**: v0.7.56에서 pre/code 강제 override는 있었지만 표는 누락 — 이번에 라이트 한정으로 추가

## 검증

- `npx tsc -b` exit 0
- `npx vite build` exit 0 (background session)
- Safari 대시보드에서 `/page/<vault>/<slug>` 페이지 라이트 모드 + 표 + `inline code` 영역 직접 확인

## v0.7.115-hotfix (사용자 피드백 직후)

### 무엇을 했는가

- **문제**: v0.7.115 첫 패치 적용 후에도 표 셀 일부가 검은 배경으로 표시되고 텍스트가 묻힘
- **근본 원인**:
  1. `--color-surface` 토큰이 `:root`에 **미정의**였음 → 표 셀 `background: var(--color-surface)`가 빈 값 fallback → 셀 투명 → 뒤에 있는 wmde-markdown 스타일 또는 캔버스가 비쳐 보임
  2. v0.7.56+ 글로벌 pre 강제(`#1e293b` slate-800)가 **셀 안 pre에도** 적용 → "셀 안에 검은 박스 + 어두운 텍스트" 회귀
- **수정**:
  - `:root`에 `--color-surface: #ffffff` alias 추가 (canvas와 동일, 표/패널 공통 표면)
  - `[data-color-mode="light"] .wmde-markdown table pre/code` override 추가 — slate-100(`#f1f5f9`) bg + slate-200 border + ink fg
  - 표 안 `pre code`는 transparent로 (셀 위에 자연스럽게)

### 검증

- tsc -b exit 0
- vite build exit 0

## 다음에 무엇이 가능한가

- [ ] wmde-markdown의 다른 GitHub 잔재 (kbd, sub/sup, mark 등) 동일 패턴으로 라이트/다크 톤 정합성 점검
- [ ] 다크 모드 표 톤 (현재 미지정 — wmde 기본 + 어두움) — 같은 패턴으로 토큰화 검토
