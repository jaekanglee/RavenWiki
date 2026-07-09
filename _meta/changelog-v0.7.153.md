---
title: Changelog v0.7.153
created: 2026-07-09
updated: 2026-07-09
type: rule
tags: dashboard, graph, bugfix
---

# v0.7.153 — 미니맵 패널 위치 우측 하단 복원 및 드래그/툴바 UX 전면 개선

## BLUF
v0.7.152에서 도입한 미니맵 호버 툴바가 3가지 연쇄 버그를 만들었다: (1) localStorage에 저장된 구형 `left/top` 좌표로 인해 패널이 우측 **상단**에 붙어 복원되고, (2) `flex-direction: column` 방향과 `left/top` inline 스타일이 충돌해 카드가 잘렸으며, (3) opacity 0.15 + pointer-events none 조합으로 툴바 버튼이 사실상 투명/클릭 불가 상태였다. 좌표계를 `right/bottom` 기준으로 전면 교체하고 툴바 시인성을 복원했다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 포지션 좌표계 `left/top` → `right/bottom` 전면 교체 | `FloatingGraphPanel.tsx` | CSS 기본 앵커(`right:24px, bottom:24px`)와 일치 — 드래그 미사용 시 항상 우측 하단 |
| 구형 `left/top` localStorage 항목 자동 파기 | `FloatingGraphPanel.tsx` | 이전 세션에서 저장된 잘못된 좌표가 로드되지 않음 |
| 드래그 좌표 계산 `offsetFromRight/Bottom` 재작성 | `FloatingGraphPanel.tsx` | 패널 우측·하단 엣지 기준으로 정확한 드래그 이동 |
| 모바일 `e.preventDefault()` 추가 | `FloatingGraphPanel.tsx` | 터치 드래그 중 브라우저 스크롤이 간섭하지 않음 |
| 툴바 opacity `0.15 → 0.7`, pointer-events `none → auto` | `globals.css` | 버튼 항상 가시적·클릭 가능 |
| 버튼 크기: 28px 원형 → 22px pill 형태 | `globals.css` | 한글 텍스트('전체', '맞춤') 수용 |
| 기호(`⤢ ⌖`) → 한글 라벨 복원 | `GraphCanvas.tsx` | '전체', '맞춤' 텍스트로 직관적 UX |
| 줌 컨트롤 순서 재정렬: `+ → 배율% → −` | `GraphCanvas.tsx` | 세로 툴바에서 위에서 아래로 자연스러운 흐름 |
| 줌 +/- 버튼 미니맵에서도 항상 표시 | `GraphCanvas.tsx` | 미니맵에서도 줌 인/아웃 가능 (배율% 레이블도 표시) |
| 헤더 두께 슬림화: `padding 10px 12px → 5px 8px` | `globals.css` | 배경색 제거, font-size 11px로 경량화 |

## 왜 했는가 (4 저장 신호)

- **실패/리스크 기록**: v0.7.152 호버 툴바 개편이 좌표계 불일치·opacity 충돌이라는 silent failure를 만들었고, 핫픽스 정책(AGENTS.md §9)에 따라 즉시 수정.
- **인수인계**: 좌표계 교체 이유(`right/bottom` 기준이 CSS flex 방향과 일치)를 명시해 향후 재발 방지.

## 근본 원인 분석

```
FloatingGraphPanel CSS: position: fixed; right: 24px; bottom: 24px;  ← 우측 하단 앵커
FloatingGraphPanel state: { left: number; top: number }              ← 반대 방향 좌표계
→ inline left/top이 CSS right/bottom을 override
→ 저장된 left값이 작으면 패널이 우측 상단에 붙음
→ flex-column에서 카드가 top 방향으로 잘림
```

## 검증

- `cd dashboard && npx vitest run` → **28 Test Files, 143 passed | 1 skipped** ✅
- commit: `cd2efca` — `fix(dashboard): 미니맵 패널 위치 우측 하단 복원 및 드래그/툴바 UX 전면 개선`
- push: `master → origin/master` ✅

## 연관

- [[Changelog v0.7.152]] — 이번 버그의 원인이 된 미니맵 툴바 개편 커밋
