# raven v0.7.48 — 그래프 dark mode 엣지 시인성 보수

> **핵심**: v0.7.47에서 옵시디언 식 은하수 미학을 위해 그래프 연결선(`--graph-edge`)의 투명도를 라이트 0.28 / 다크 0.22로 떨어뜨렸으나, 다크 모드에서는 slate-400 22%가 배경(#0a0e1a)에 묻혀 path가 사실상 보이지 않는 문제가 있었습니다. 다크 모드의 엣지 opacity를 0.45로 올리고(`globals.css`), `GraphCanvas`의 base/focus 분기에서도 stroke 두께를 `0.65→1.0`, 평상시 opacity를 `0.16→0.6`으로, hover/highlight 비례를 재조정했습니다. 또한 옛 베이스 값(0.65/0.16)을 잠그던 회귀 가드 테스트(`edge style은 조용한 기본 톤`)를 새 베이스(1.0/0.6)와 비례 관계를 검증하는 형태로 갱신했습니다.

릴리스 일자: 2026-07-02
이전: v0.7.47

---

## 1. 변경 사항

### 1-1. 다크 모드 그래프 엣지 시인성 개선 ([globals.css](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/styles/globals.css))
* `--graph-edge` 토큰의 다크 값을 `rgba(148, 163, 184, 0.22)` → `rgba(148, 163, 184, 0.45)`로 약 2배 강화했습니다(body / html.dark 두 곳 모두).
* 라이트 모드 토큰은 v0.7.47의 0.28을 유지해 의도된 은하수 미학(보통 빛의 별자리 무늬)을 보존합니다.
* highlight 토큰(`--graph-edge-highlight`) 및 기타 그래프 토큰은 변경하지 않았습니다 — 기존 노드/라벨 톤과 일관성 유지.

### 1-2. rfEdges의 베이스 stroke 상향 ([GraphCanvas.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/GraphCanvas.tsx))
* 기존 베이스(`strokeWidth: 0.65 / strokeOpacity: 0.16`)은 다크 토큰(0.22)과 곱해져 사실상 3.5% 가시도였습니다.
* 베이스를 `strokeWidth: 1, strokeOpacity: 0.6`으로 바꾸고, 토큰의 opacity와 분리해 두었습니다(토큰은 hover/focus 외 다른 컨텍스트에서의 단일 사용처). 이제 다크 모드 평상시 가시도가 약 17배(0.035 → 0.6) 상승합니다.

### 1-3. focus 분기 비례 조정 ([GraphCanvas.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/GraphCanvas.tsx), L558)
* L558의 focus 분기는 매 렌더 rfEdges를 덮어쓰므로(`, strokeOpacity: opacity`), base만 올려도 dim 상태에서 여전히 옅게 보일 위기가 있었습니다. 베이스에 맞춰 분기를 비례 조정했습니다.

| 상태 | 이전 (v0.7.47) | 이후 (v0.7.48) | 의미 |
|---|---|---|---|
| `!focus.active` (평상시) | opacity 0.16, width 0.65 | opacity 0.6, width 1 | 다크 모드에서 path가 명확히 보임 |
| focus 활성 + highlight | opacity 0.82, width 1.35 | opacity 0.85, width 1.5 | 강조 노드가 한층 또렷 |
| focus 활성 + 비활성 | opacity 0.045, width 0.65 | opacity 0.18, width 1 | 비활성 edge를 진짜로 가리면서도 0에 수렴하지 않음 |

### 1-4. 회귀 가드 테스트 갱신 ([GraphCanvas.mobile-tap-label.test.ts](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/tests/GraphCanvas.mobile-tap-label.test.ts))
* 옛 `"edge style은 조용한 기본 톤 — slate-400 / 0.65px / 0.16"` 케이스는 옛 베이스 값을 그대로 박아 둔 회귀 가드였으나, 이번 패치로 인해 베이스(1.0/0.6)와 어긋나 stale이 됩니다.
* 테스트를 `"edge style은 dark mode 시인성 개선 적용 — slate 토큰 / 1px / 0.6 (v0.7.48+)"`로 교체하고 다음을 검증하도록 바꾸었습니다.

  1. `strokeWidth < 1.5` — v0.6.11 1차의 두꺼운 선(≥ 2px)으로 회귀하지 않음을 보장.
  2. `strokeOpacity >= 0.4` — 다크 모드에서 path가 안 보이던 회귀(0.16 수준)를 방지.
  3. `dimOpacity === 0.6`, `highlightOpacity > baseOpacity`, `highlightWidth > baseWidth` — focus 분기 간 비례가 유지됨을 보장.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `tsc -b` | exit 0 | 타입 에러 없음 |
| `vitest run` (graph 3 files) | 18/18 passed | 새 테스트 명 1건 포함 |
| `git diff --stat` | 3 files, +32/-18 | GraphCanvas 16 / globals.css 4 / 테스트 30 |

---

## 3. 다음에 가능한 것

* 모바일/태블릿에서 zoom-out 시 path가 살짝 도드라지면 — inline MediaQuery로 `strokeOpacity` 보간 필요 (이번 패치는 손대지 않음).
* 사용자/타입 색 강조와 무관하게 path 자체를 살짝 색조 변화(예: 양 끝점이 만나는 노드 색으로 살짝 페이드) — 마지막 보너스.
* `--graph-edge-strong` 별도 토큰 도입: 향후 라이트 모드에서도 시인성 보강이 필요해질 경우(v0.7.47의 의도된 0.28이 오히려 부족하다는 피드백 시).
