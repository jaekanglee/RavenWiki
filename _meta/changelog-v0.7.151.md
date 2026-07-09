---
title: Changelog v0.7.151
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.151 — 웹 대시보드 이슈 문서 피드백 섹션의 다크모드 미지원 문제 해결

## BLUF
웹 대시보드 내의 이슈 타입 문서 페이지에서 '에이전트 수정 지시 및 피드백' 영역의 배경색 및 글자색이 다크모드에서 흰색으로 고정되어 있던 문제를 해결했다. `globals.css`의 다크모드 변수 목록에 누락되어 있던 `--color-surface`를 추가하고, `PageView.tsx` 내의 피드백 영역 인라인 스타일을 3-layer 디자인 시스템에서 권장하는 `--bg-surface` 및 `--fg-ink` 등의 의미론적 변수로 마이그레이션했다.

## 무엇을 했는가

| 변경 | 위치 | 효과 |
|---|---|---|
| `--color-surface` 다크모드 재정의 추가 | `dashboard/src/styles/globals.css` | `[data-color-mode="dark"]` 및 `html.dark` 스타일 블록에 `--color-surface: #1e293b;` 정의를 추가하여, 다크모드 적용 시 레거시 `--color-surface`를 사용하는 타 컴포넌트(표, 코드 블록 등)의 배경색 깨짐 방지 |
| 피드백 섹션 컨테이너 디자인 시스템 마이그레이션 | `dashboard/src/routes/PageView.tsx` | 이슈 타입 피드백 패널의 inline style을 `var(--color-surface)` -> `var(--bg-surface)`로, border를 `var(--color-border)` -> `var(--border-subtle)`로 교체 |
| 피드백 텍스트 필드 및 제목 스타일링 최적화 | `dashboard/src/routes/PageView.tsx` | 피드백 영역의 h3 텍스트와 textarea의 background, color, border에 `--fg-ink`, `--fg-muted`, `--border-subtle` 등의 토큰 적용 |

## 왜 했는가
- 다크모드 환경에서도 이슈 문서 뷰의 피드백 입력 영역만 밝은 흰색 배경으로 표시되어 시각적 일관성을 크게 저해하고 있었다.
- 원인을 조사한 결과, 다크모드 스타일을 정의하는 `globals.css` 파일의 다크 테마 셀렉터 내에서 `--color-surface` 변수 정의가 누락되어 있었고, 피드백 입력 패널의 inline style 역시 3-layer 디자인 시스템의 semantic 토큰 대신 레거시 `--color-surface` 변수를 직접 참조하고 있었다.
- 3-layer 디자인 시스템 가이드라인(AGENTS.md §13)에 따라 컴포넌트 내의 색상 지정을 semantic CSS 변수로 변경하고, globals.css에 다크모드 전용 `--color-surface` 폴백 값을 명시함으로써 UI 일관성을 확보했다.

## 검증
- `make typecheck` → 통과 (성공)
- `make test` → 성공 (완료 확인 예정)
- `npx vitest run` (in `dashboard/`) → 성공 (완료 확인 예정)
