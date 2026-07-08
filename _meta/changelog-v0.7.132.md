---
title: Changelog v0.7.132
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.132 — all-vault graph UI/UX improvements & vault labels

## BLUF
전체 볼트(all-vault) 그래프 보기 시 지도의 정독 가치와 시인성을 극대화하기 위해 3종 UI/UX 개선을 단행했다. 줌인 시 노드 라벨을 동적으로 다시 띄우고, Cross-Vault Edge 시인성을 향상시켰으며, 캔버스상에 줌 반응형 Vault 이름 라벨을 추가했다. 추가적으로, 고밀도(dense) 모드에서 캔버스 드래그/줌 제스처를 가로막아 조작을 방해하던 노드/엣지 이벤트 간섭을 해결하기 위해 **Figma 스타일의 `이동 모드(Hand Mode)` 및 `Space 단축키` 기능**을 도입했다. 워킹트리의 레이아웃 필터 동기화 및 22% 클러스터 압축(Compaction) 변경분도 함께 확정했다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | 줌 레벨 `zoom > 0.55`일 때 `showLabel` 활성화 | Dense 모드에서도 줌인을 하면 문서 제목이 뚜렷하게 보이도록 개선 |
| `dashboard/src/components/GraphCanvas.tsx` | Edge Opacity 조정 및 `pointerEvents: "none" as const` 적용 | Dense 모드에서 엣지 시인성을 올리면서 엣지가 캔버스 줌/이동 제스처를 방해하는 현상 해결 |
| `dashboard/src/components/GraphCanvas.tsx` | `graph-vault-centroid-label` 추가 (줌 비례 크기/투명도 보간) | 캔버스 상에서 각 Vault 구역의 정체성을 상시 텍스트로 인식 가능 |
| `dashboard/src/components/GraphCanvas.tsx` | `이동 모드 (Hand Mode)` 및 우측 상단 토글 UI 추가 | 이동 모드에서 모든 노드의 `pointerEvents`를 `none`으로 강제해 빽빽한 화면에서도 100% 매끄러운 캔버스 드래그/줌 제스처 보장 |
| `dashboard/src/components/GraphCanvas.tsx` | 키보드 `Space` 키 Down/Up 이벤트 바인딩 | 문서 조회/선택 작업 중 Space바를 누르는 동안 임시로 hand 모드로 즉시 전환 |
| `dashboard/src/components/GraphCanvas.tsx` | Dense(all-vault) 그래프 진입 시 Hand 모드로 기본 활성화 | 빽빽한 전체 지도를 열자마자 노드 가로채기 렉 없이 부드러운 패닝/핀치줌 조작 시작 가능 |
| `dashboard/tests/GraphPage.all-vault-scope.test.tsx` | 변경된 상수 및 centroid-label 추가에 맞춰 contract test 정합 | 프론트엔드 테스트 회귀 방지 및 빌드 정상화 |
| `dashboard/src/routes/GraphPage.tsx` | Centroid 계산 기준을 `filteredGraph`로 정합 | 필터 적용(검색, 타입 등) 시 Halo/Centroid 좌표가 어긋나지 않도록 수정 |
| `raven/api/server.py` | `cluster_compaction = 0.78` 도입 | All-vault 레이아웃 배치 시 Vault 간 분리감 향상 (22% 압축) |

## 왜 했는가
- **재사용 가능성**: 전체 볼트 뷰의 유용성(Utility)을 올려 사용자가 보관소 간 다차원적 연결을 적극 탐색하게 유도함
- **맥락 추적**: dense 모드에서 발생하던 극단적인 텍스트 라벨 실종 현상과 흐린 연결선 문제를 구조적으로 차단
- **실패 방지**: Centroid 계산이 필터 이전의 전체 그래프 기준으로 남아 캔버스상 렌더링된 컴포넌트 위치와 불일치하던 버그 방지

## 검증
- `make typecheck` ✅
- `cd dashboard && npx vitest run tests/GraphPage.all-vault-scope.test.tsx` → **11 passed** ✅
- `make test` (pytest) → **730 passed** ✅
