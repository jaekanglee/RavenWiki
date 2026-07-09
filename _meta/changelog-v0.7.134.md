---
title: Changelog v0.7.134
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.134 — all-scope 그래프 시각 클렌징: vault 헤더 라벨 + ring 시각화

## BLUF
all-scope 그래프에서 각 군집이 어떤 vault인지 시각적으로 명확히 식별 가능하도록 두 가지를 추가했다: (1) `nodeCanvasObject`의 vault 색 ring을 1.2px → 2.4px로 두껍게 + `rgba(..., 0.55)` alpha 적용해 시야성 확보, (2) `onRenderFramePost` hook으로 각 vault centroid 위에 **vault 이름 헤더** (작은 둥근 사각 박스 + vault 색 dot + 텍스트) 캔버스에 직접 그림. zoom 따라 텍스트 크기가 변하지 않도록 `globalScale`로 픽셀 사이즈 보정.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | (1) `resolveVaultColor` 옆에 `hexToRgba(hex, alpha)` 헬퍼 추가. (2) vault ring stroke를 `1.2/scale` → `2.4/scale`, strokeStyle에 alpha 0.55. (3) `vaultCentroidsRef` 추가 + 매 frame `ref.current = vaultCentroids` 동기화 (effect 재실행 안 함). (4) 별도 `useEffect`에서 `graph.onRenderFramePost(drawVaultHeader)` 등록 — `isDense` 변화에만 hook 갱신. vault label: `vc.x - width/2, vc.y - vc.radius - 여유` 위치에 rounded rect (rgba(15,23,42,0.78) bg + vault 색 1.4/scale 보더) + 좌측 vault 색 dot + 텍스트 | 사용자가 군집 위 헤더로 vault 이름 즉시 식별. ring 두께로 동일 vault 노드들이 시각 묶음으로 보임 |
| `_meta/changelog-v0.7.134.md` | 본 changelog 작성 | |

## 왜 했는가
- **요구 (사용자 2026-07-09, v0.7.133 작업 후속)**: "각 군집이 어떤 군집인지 알수있게 할수있을까" + "시각적으로 좀 클렌징하자 너무 단순하거 투박해. B 도하자."
- **실측 (v0.7.133 커밋 전 화면 캡처)**: vault ring이 scale 보정 1.2px로 화면에서 거의 invisible → 5개 군집 색 식별 불가. vault 이름 라벨 부재 → 사용자가 어떤 vault인지 추측해야 함.

## 동작
- **all-scope 진입 시**: 5개 vault의 centroid 위에 헤더 박스 (옛날 v0.7.132의 📁 halo 박스와 유사하지만 더 컴팩트 + 정통 카드 스타일)
- **zoom in/out**: 헤더 텍스트 크기 그대로 유지 (`fontSize = 13/scale` 패턴)
- **vault color dot**: 헤더 박스 좌측에 4.5px dot — 색으로 한 번 더 식별
- **current scope**: `vaultCentroids`가 빈 배열이라 자연스럽게 skip (all 모드에서만 활성)
- **hover/click** 영향 없음: ref 기반이라 interaction과 분리

## contract 노트
- `onRenderFramePost` 콜백은 force-graph가 매 frame paint 후 호출. centroids 길이만큼 vault 라벨 그림 — N vault × 1 콜백/frame.
- rounding rect 코드는 기존 `v0.7.139+`에 삭제됐던 `rounded-rect` 헬퍼가 다시 필요해져 inline 작성. 별도 헬퍼 추출 ❌ (1 vault header × ~ 25줄 inline).
- 기존 `vaultCentroids?:` prop 정의 + 주석만 있던 상태 활용 — **prop은 이미 GraphPage에서 `deriveVaultCentroids(filteredGraph)`로 채워 전달 중**, Canvas가 이제 실제로 사용.

## 검증
- `cd dashboard && ./node_modules/.bin/tsc -b` exit 0
- `cd dashboard && ./node_modules/.bin/vitest run` 148 passed + 1 skipped (회귀 0)
- `pytest tests/test_api.py -k "graph"` 11/11 통과
- 실 브라우저에서 `http://localhost:5173/graph` → 전체 vault → 헤더 박스 5개 표시, ring 두께 2x 시각화 확인 필요 (사용자 확인)
