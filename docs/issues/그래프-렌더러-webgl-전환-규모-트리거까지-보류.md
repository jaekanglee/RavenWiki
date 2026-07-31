---
title: 그래프 렌더러 WebGL 전환 — 규모 트리거까지 보류
type: issue
status: open
created: 2026-07-31
tags: [performance, dashboard, graph]
source: 2026-07-31 그래프 조사 (옵션 A 성능·B 품질 구현, C 렌더러 교체 보류)
aliases: [graph-webgl-renderer-migration]
---

# 그래프 렌더러 WebGL 전환 — 규모 트리거까지 보류

대시보드 그래프를 WebGL 렌더러로 갈아타는 작업은 **지금 하지 않는다** — 현재 vault 규모(13~144 페이지)에서 병목은 캔버스 페인트가 아니라 서버 ForceAtlas2와 프론트 effect 재실행이었고, 그 둘은 2026-07-31 옵션 A에서 해결했다.

## 요약

2026-07-31 조사에서 "그래프가 2D이고 느리고 저퀄"이라는 보고를 세 갈래로 분해했다.
느림의 실제 원인은 서버 레이아웃 재계산과 프론트의 거대 effect 재실행이었고(옵션 A),
시각 품질은 라벨 충돌·색 토큰화·뷰포트 컬링 문제였다(옵션 B). 두 옵션은 렌더러를
그대로 두고 해결됐다. 남은 것이 이 문서가 다루는 렌더러 자체의 교체다.

## 현재 상태

- 렌더러: `force-graph` 1.51.4 — 2D HTML5 canvas 전용 (`dashboard/package.json`).
- force-graph 내부 특성: d3 시뮬레이션 tick이 메인스레드 `tickFrame`에서 돈다
  (`dist/force-graph.mjs:527-546`), 포인터 피킹용 shadowCanvas 때문에 노드와 링크를
  **프레임당 2회** 페인트한다 (`dist/force-graph.mjs:1085`).
- 우리 쪽 시각 코드: `dashboard/src/components/GraphCanvas.tsx`의
  `nodeCanvasObject` + `onRenderFramePre`에 약 480줄의 캔버스 2D 드로잉이 있다 —
  노드 본체, 이중 포커스 링, broken dependency halo, 라벨 LOD, 커뮤니티 구획,
  타임라인 그리드. 렌더러를 바꾸면 이 전부가 재작성 대상이며, 3D에서는
  `nodeThreeObject` + 스프라이트 라벨로 옮겨야 한다. **교체 비용의 대부분이 여기다.**

## 후보 비교 (2026-07 조사 기준)

| 라이브러리 | 버전 | 라이선스 | 백엔드 | 실용 상한 | 레이아웃 | 비고 |
|---|---|---|---|---|---|---|
| @cosmograph/cosmos | 3.4.0 | MIT | WebGL | 20k+ | **GPU** | 서버 레이아웃을 아예 없앨 수 있는 유일 후보. 커스텀 노드 드로잉 불가(셰이더 기반) |
| sigma | 3.0.3 | MIT | WebGL 2D | ~10k | CPU/worker | 라벨 렌더링이 가장 성숙. React 통합에 손이 감 |
| reagraph | 4.27.0 | Apache-2.0 | three.js | ~5k~10k | CPU/worker | React-first, 2D+3D 동시 지원 |
| 3d-force-graph / react-force-graph-3d | 1.80.0 / 1.29.1 | MIT | three.js | ~3k~5k | CPU/worker | 현재 코드와 API 이질감 최소 |

## 보류 근거

- 실측 규모: harumoa 137 노드 / 469 엣지, babymoa 13 / 39. 이 규모에서 캔버스
  페인트는 프레임 예산을 넘기지 않는다.
- 실제 병목은 (a) 서버 ForceAtlas2 O(n²) — n=600에서 7.5초, (b) 노드 클릭마다
  `graphData()` 재설정으로 d3가 재가열되던 프론트 effect였다. 둘 다 옵션 A에서 처리.
- 렌더러 교체는 480줄 시각 코드 재작성 + 라벨 가독성 회귀 위험을 동반한다.
  지금 얻을 이득이 없다.

## 재개 트리거

다음 중 하나가 성립하면 이 문서를 다시 연다.

1. 단일 vault가 1,000 페이지를 넘어 서버 좌표 캐시로도 첫 렌더가 버벅인다.
2. 여러 vault 통합 그래프(v0.7.144에서 제거된 all-scope)를 되살려 노드 수가 합산된다.
3. GPU 레이아웃으로 서버 ForceAtlas2를 아예 걷어내기로 결정한다.

## 3D에 대한 판단

3D는 렌더러 교체와 별개 결정이다. 137노드 PKM에서 3D는 오클루전과 방향감각 상실로
탐색성이 오히려 떨어진다. 도입한다면 기본 뷰가 아니라 **전체보기 모달 전용 옵션**으로
한정한다.

## 예상 공수

렌더러 교체 3~5일 (라이브러리 배선 0.5일 + 시각 코드 재작성 2~3일 + 라벨/인터랙션
회귀 잡기 1일). 3D 옵션은 그 위에 1~2일.

## 미검증

"Obsidian 그래프 뷰가 WebGL을 쓴다"는 통설은 이번 조사에서 신뢰할 출처를 찾지 못했다.
렌더러를 고를 때 이 통설을 근거로 쓰지 말 것.
