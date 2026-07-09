---
title: Changelog v0.7.150
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.150 — 그래프 캔버스 쏠림 및 잘림 현상 수정 (ResizeObserver 도입)

## BLUF
그래프 캔버스 진입 시 레이아웃 크기가 확보되기 전에 줌핏(`zoomToFit`)이 수행되어 노드들이 캔버스 구석으로 쏠리거나 잘리는 현상을 수정했다. 캔버스 컨테이너 크기 변화를 추적하는 `ResizeObserver`를 도입하고 크기가 정상 확보된 시점에 `zoomToFit`을 수행하도록 개선했다.

## 무엇을 했는가

| 변경 | 위치 | 효과 |
|---|---|---|
| `ResizeObserver` 도입 | `dashboard/src/components/GraphCanvas.tsx` | 컨테이너의 실제 픽셀 크기를 감지하여 `force-graph` 크기(width, height)를 실시간 갱신 |
| `zoomToFit` 레이아웃 가드 | `dashboard/src/components/GraphCanvas.tsx` | `width > 0 && height > 0`일 때까지 100ms 대기 후 최대 10회 재시도(tryFit) 하도록 개선 |

## 왜 했는가
- 사용자가 웹 대시보드의 그래프(캔버스) 탭 진입 시, 캔버스 레이아웃의 최초 렌더링 시점에 컨테이너 크기가 0(또는 임시 값)으로 판정된다.
- 이 상태에서 `zoomToFit`이 즉시 실행되어 잘못된 배율 및 카메라 좌표가 설정됨함으로써 노드들이 우하단으로 쏠리거나 잘려서 출력되었다.
- 캔버스의 동적 크기 변화를 브라우저 레이아웃에 맞춰 지속 업데이트해 주어야 `zoomToFit`이 올바른 중앙 정렬을 계산할 수 있다.

## 검증
- `npm run build` (in `dashboard/`) → 성공 (Vite build 완료)
- `npm run test` (in `dashboard/`) → 성공 (28개 테스트 파일, 143개 테스트 통과)
