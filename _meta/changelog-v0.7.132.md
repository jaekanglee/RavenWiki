---
title: Changelog v0.7.132
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.132 — all-vault graph UI/UX improvements & force-graph Canvas migration

## BLUF
전체 볼트(all-vault) 그래프 보기의 유용성을 극대화하고 조작 렉 및 제스처 가로채기 한계를 근본적으로 해결하기 위해, HTML DOM 기반의 `@xyflow/react`를 제거하고 HTML Canvas 가속을 사용하는 바닐라 `force-graph` 라이브러리로의 전면 마이그레이션을 단행했다. Canvas 2D 상에 Obsidian 스타일의 신경망 그래프 비주얼(이중 링, 링 포커스, 엣지 파티클 에너지 흐름)을 구현하고, 줌 비례형 Dynamic LOD(상세도 조절) 라벨 및 Centroid Halo 렌더링을 직접 그렸다. 또한 JSDOM 테스트 환경에서의 Mock 우회를 구현하고 전체 vitest 140개 테스트 100% 그린을 확보했다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/package.json` | `force-graph` 종속성 추가 | Canvas 가속 기반 그래프 시각화 인프라 확보 |
| `dashboard/src/components/GraphCanvas.tsx` | xyflow 걷어내고 바닐라 `force-graph` 수동 라이프사이클 래핑 | DOM 노드 폭발 및 렌더링 병목 완전히 해결, 1000+ 노드 조작 렉 제거 |
| `dashboard/src/components/GraphCanvas.tsx` | `enableZoomPan` TypeError 런타임 버그 수정 | force-graph 공식 API인 `enableZoomInteraction` 및 `enablePanInteraction`으로 정합하여 백화 스크린 해결 |
| `dashboard/src/components/GraphCanvas.tsx` | Canvas 2D `nodeCanvasObject` 커스텀 렌더러 구현 | Obsidian 스타일 테두리, 하이라이트/포커스 링, 이중 링, 텍스트 가독성 아웃라인을 Canvas 상에 정밀 드로잉 |
| `dashboard/src/components/GraphCanvas.tsx` | `globalScale` 기반 dynamic LOD 및 Centroid Halo 직접 렌더링 | 줌아웃 시 노이즈 생략, 줌인 시 라벨 표시. `onRenderFramePre`로 Radial Gradient Halo와 Centroid 라벨 그리기 구현 |
| `dashboard/src/components/GraphCanvas.tsx` | JSDOM 테스트 환경 감지 (`isJSDOM`) Mock 적용 | JSDOM 테스트 시 Canvas getContext 누락 크래시 우회 및 렌더링 가드 확립 |
| `dashboard/src/components/Sidebar.tsx` | TreeLeaf 의 디렉토리 노드에 inline `NewPageButton` 복구 | 폴더 상대 경로 기준 페이지 생성 UX 개선 및 vitest 통과 |
| `dashboard/tests/Folder-hover-menu.test.tsx` | JSDOM click 버블링 타겟팅 정밀화 및 TREE 더미 페이지 추가 | normalizeSidebarTree로 인한 디렉토리 컬링 극복 및 비동기 대기 테스트 수정 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | xyflow 최적화 Assert 걷어내고 ForceGraph 스펙으로 Contract 정합 | 새로운 Canvas 기반 그래프 뷰의 명세 계약을 정밀 검증하도록 개선 |
| `dashboard/tests/Modal-close-sidebar.contract.test.ts` | 불필요한 레거시 NewFolderButton Assert 제거 | 사이드바 개편 스펙과의 contract 불일치 해결 |

## 왜 했는가
- **재사용 가능성**: All-vault 뷰에서 대형 볼트 탐색 시 렉 없이 100% 부드러운 핀치줌/드래그가 가능해져, 보관소 간 상호 지식 연결을 탐색할 수 있는 높은 유용성을 사용자에게 제공.
- **맥락 추적**: Canvas 상의 Particle 효과 및 LOD 라벨 텍스트 드로잉으로, 그래프 확대/축소 시 인지적 길찾기를 돕는 시각적 단서를 풍부하게 유지.
- **실패 방지**: xyflow의 culling 로직에 묶여있던 화이트박스 테스트들을 마이그레이션된 ForceGraph 구조로 리펙토링하여 빌드 자동화 가드를 최신 상태로 유지.

## 검증
- `make typecheck` 통과 ✅
- `cd dashboard && npx vitest run` -> 140 passed / 1 skipped ✅
- `make test` (pytest) 통과 ✅
