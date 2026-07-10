---
title: Changelog v0.7.168
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [graph, dashboard, analytics, docs, test]
---

# v0.7.168 — Phase 17: Semantic Relation Inference Plan 시각화 종결

## BLUF
Dashboard Graph View가 이미 DB에 계산·저장하던 동적 속성 `freshness`와 `layer`를 끝까지 소비하도록 마무리했습니다. 이제 `freshness`는 노드 opacity, `layer`는 별도 `Layered` 레이아웃으로 시각화되며, `docs/superpowers/plans/semantic-relation-inference-plan.md`와 `_meta/index.md`도 완료 상태로 닫혔습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| freshness 시각 매핑 추가 | `dashboard/src/components/GraphCanvas.tsx` | `nodeOpacity()` 헬퍼를 도입해 오래된 문서는 더 반투명하게 렌더. 기존 `importance`(크기), `centrality`(테두리), `community`(색상)와 함께 `freshness`도 실제 UI에 반영 |
| layer 전용 레이아웃 신설 | `dashboard/src/components/GraphCanvas.tsx` | `computeLayeredLayout()` 추가. `layer` 값을 가로축 깊이로 사용하고 동일 layer 노드는 세로로 분산 배치. concentric의 "선택 중심 거리"와 분리된 별도 분석 뷰 |
| 레이아웃 선택 UI 확장 | `dashboard/src/routes/GraphPage.tsx`, `dashboard/src/components/FullscreenGraphModal.tsx` | `GraphLayoutMode` 타입 공유 및 `레이어 깊이 (Layered)` 옵션 추가. 헬퍼 문구도 concentric vs layered 차이를 명시하도록 보완 |
| 회귀 테스트 추가 | `dashboard/tests/GraphCanvas.obsidian-style.test.ts` | `freshness → opacity` 범위와 `layered` 좌표 계산 규칙을 정적 테스트로 검증 |
| SoT 완료 처리 | `docs/superpowers/plans/semantic-relation-inference-plan.md`, `_meta/index.md` | 계획서 frontmatter에 `status: completed` 및 완료 문구 추가. 인덱스의 SoT 안내도 완료 상태로 갱신 |

## 왜 했는가 (4 저장 신호)
- **재사용 가능성**: 그래프 분석으로 계산된 5개 동적 속성이 모두 Dashboard에서 일관되게 소비되어, 이후 다른 뷰나 인사이트 UI도 같은 메타데이터 계약 위에서 확장할 수 있습니다.
- **인수인계**: 계획서와 인덱스를 완료 상태로 닫아 다음 세션이 "무엇이 남았는지"를 다시 추적하지 않도록 했습니다.
- **scope/provenance 추적**: `concentric`와 `layered`의 의미 차이를 UI helper와 changelog에 함께 남겨 해석 혼선을 줄였습니다.

## 검증
- `cd dashboard && npx vitest run tests/GraphCanvas.obsidian-style.test.ts`
- `cd dashboard && npx tsc --noEmit`
- `cd dashboard && npm run build`

## 후속 작업 후보
- `layer` 계산 근거(루트 기준 평균 깊이)를 그래프 상세 패널에도 숫자/배지로 노출
- `freshness` 범례(최근/정체)를 HUD나 도움말에 추가
