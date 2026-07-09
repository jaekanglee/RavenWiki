---
title: Changelog v0.7.135
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.135 — vault 라벨 단순화: 박스 X, 텍스트만

## BLUF
all-scope 그래프에서 각 vault 이름을 식별 가능하도록 라벨 추가. 처음엔 옵시디안 모방해서 rounded rect 박스 + 색 dot + 보더 + 본문으로 가공했지만 사용자 2026-07-09 보고: "꼭 옵시디안 스타일 고딥 할 필욘 업ㄱ어. 그냥 시인성 즇으면 돼." — 박스 없이 텍스트만, outline + vault 색으로 가볍게.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | `onRenderFramePost`로 vault 라벨 그리기. drawVaultLabel 콜백: centroid 좌표 (`vc.x`, `vc.y - 50 * scale`)에 텍스트. fontSize `14 * scale`, vault 색 fill + dark outline (3 * scale, rgba(15,23,42,0.85))로 가독성 | vault 이름이 centroid 위쪽에 단순 텍스트로 표시. 박스/dot/border 없음 |

## 왜 했는가
- **사용자 2026-07-09**: "지금 그럼 군집 들 가운데에 라벨 못 해? 어떤 군집인지" + "꼭 옵시디안 스타일 고딥 할 필욘 업ㄱ어. 그냥 시인성 즇으면 돼."

## 동작
- vault label = `{vault}` 텍스트만, vault 색 + dark outline
- 위치 = centroid (50px 위, zoom 따라)
- scale < 0.3에서 skip (잡음 컷)
- 텍스트가 노드들과 시각적으로 어울리도록 outline로 분리

## 검증
- vitest 통과 (회귀 0)
- tsc exit 0
- 실 브라우저에서 라벨 가독성 확인 (사용자)