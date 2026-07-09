---
title: Changelog v0.7.152
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.152 — 웹 대시보드 문서 뷰 내 미니맵 그래프 줌 컨트롤 및 레이아웃 개선

## BLUF
문서 페이지 우하단에 제공되는 관련 그래프 미니맵(`FloatingGraphPanel`) 내에서 가로로 너무 많은 면적을 차지하던 줌 컨트롤 버튼들을 소형 세로형 호버 툴바(variant="minimap")로 개편하여 그래프 영역의 공간 효율성과 심미성을 확보했다.

## 무엇을 했는가

| 변경 | 위치 | 효과 |
|---|---|---|
| 미니맵 전용 variant 속성 추가 | `dashboard/src/components/GraphCanvas.tsx` | `variant` prop(기본값 `"default"`)을 추가하여 `"minimap"`으로 렌더링될 때 툴바의 레이아웃과 표시되는 콘텐츠가 미니멀하게 오버라이드되도록 처리 |
| 컴팩트 호버 툴바 적용 및 아이콘화 | `dashboard/src/components/GraphCanvas.tsx` | 미니맵 모드일 때 줌 배율(%) 텍스트 렌더링을 생략하고, '전체보기' 및 '맞춤' 텍스트를 세련된 유니코드 기호 (`⛶`, `⌖`)로 치환하여 원형 버튼화 |
| 툴바 스타일 및 호버 트랜지션 추가 | `dashboard/src/styles/globals.css` | 툴바를 절대 좌표 기준 세로 블록으로 정렬하고, 평소에는 불투명도 `0.15`와 클릭 차단 상태를 유지하다가 사용자가 미니맵 영역에 마우스를 호버하면 서서히 `opacity: 1`로 나타나는 부드러운 효과 적용 |
| 미니맵에 고밀도(dense) 레이아웃 적용 | `dashboard/src/components/FloatingGraphPanel.tsx` | 미니맵 내에 `GraphCanvas`를 렌더링할 때 `variant="minimap"`과 `density="dense"`를 기본 전달하여 노드들과 라벨 폰트 크기가 좁은 화면에서도 서로 뭉치지 않게 조절 |
| 이전 커밋(49533a7) 깨진 테스트 복구 | `tests/test_v0_7_4_tailscale_host.py`<br>`tests/test_v0_7_12_docker.py`<br>`tests/test_v0_7_14_vault_persistence.py` | 기존 단일 `.env.example`을 참조하던 3개 백엔드 테스트 파일을 신규 분리된 `.env.example.house` / `.env.example.company` 파일들을 검증하도록 수정하여 빌드 복구 |

## 왜 했는가
- 기존 줌 컨트롤 툴바(`전체보기`, `맞춤`, `-`, `100%`, `+`)는 240px 너비의 좁은 미니맵 그래프 패널에서 영역의 절반 이상을 가려 그래프 조작 및 시각적 감상을 방해했다.
- 이 문제를 해결하기 위해 사용자의 피드백을 수렴하여, 평소에는 미니맵을 가리지 않도록 툴바의 영역 차지를 최소화하고 마우스를 올렸을 때만 반응성 있게 조절 버튼이 드러나는 컴팩트 툴바를 설계했다.
- 스타일 토큰화 및 컴포넌트화 가이드라인(AGENTS.md §13)에 의거하여, `GraphCanvas.tsx` 내부의 인라인 스타일을 CSS 클래스로 마이그레이션하고 테마 변수를 활용해 다크/라이트모드 대응과 유리 효과(Glassmorphism) 트랜지션을 globals.css에서 안전하게 정의했다.
- 추가로, 이전 `49533a7` 커밋에서 범용 환경변수 파일 `.env.example`을 프로필 템플릿(`.env.example.house`, `.env.example.company`)으로 분리하면서 기존 백엔드 회귀 가드 테스트들이 `FileNotFoundError`로 깨져있던 것을 빌드 검증 루프 도중 감지하여, 핫픽스 정책(AGENTS.md §9)에 따라 즉시 정합성을 확보했다.

## 검증
- `make typecheck` → 성공 (`npx tsc -b --noEmit`)
- `cd dashboard && npx vitest run` → 성공 (143개 테스트 전체 통과)
- `make test` → 성공 (736개 테스트 전체 통과 확인)
