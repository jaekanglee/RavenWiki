# raven v0.6.11 — Graph A2 진짜 fix: spring layout 파라미터 튜닝

> **핵심**: v0.6.10에서 도입한 server-side force-directed layout이 사용자 보고대로 작동하지 않음 — "노드 한 군데 뭉침 (상단 중앙) / 작은 원에서도 여전히 겹침 / 최악". v0.6.11에서 FR 알고리즘 자체는 유지하되 **파라미터 튜닝 + 초기화 방식 교체**로 sparse layout 재현.

릴리스 일자: 2026-06-29
이전: v0.6.10+ (Graph A 종합 — force-directed + dark + orphan hide)

---

## 한 줄 요약

`_spring_layout` 의 iterations·repulsion·attraction·ideal_distance·초기 위치·cooling 을 다시 튜닝 — **노드 간 평균 spacing ≥ ideal_distance/2 (=100 px) 가드 테스트 4개 추가**, hub-style 그래프에서도 노드들이 hub 주위에 정원형으로 분산됨을 확인.

## 1. 발견 경위

v0.6.10+ 적용 후 사용자 보고 (Graph 화면):

> "노드들이 한 군데 뭉침 (상단 중앙)"
> "작은 원인데도 여전히 겹침"
> "최악"

## 2. 근본 원인 (root cause 분석)

기존 구현의 4가지 결함:

1. **iterations=120 부족** — 작은 vault에서도 layout 충분히 안정화 안 됨 (FR은 보통 300~500)
2. **repulsion 약함** — FR 기본 척력 `k²/d`는 vault 크기로부터 `k = sqrt(area/n)`을 계산해서 너무 작은 값이 나옴 (vault가 작을수록 `k` 작아짐 → 척력 약해짐)
3. **attraction 강함 + ideal_distance 작음** — hub 노드가 주변 노드를 강하게 끌어당겨 중앙 집중 패턴 유발
4. **초기 위치 = hash 격자 + 작은 jitter** — FR 알고리즘 정석은 uniform random. 격자 시작은 hub가 격자 중앙에 모이는 패턴을 강제함

## 3. 변경 사항 (A2 패치 3개)

### Patch 1 — `_spring_layout` 튜닝 (`raven/api/server.py`)

| 항목 | 이전 | 이후 | 효과 |
|---|---|---|---|
| iterations | 120 | **500** | 작은 vault에서도 충분히 안정화 |
| 초기 위치 | 격자 + ±10 jitter | **uniform random** (seed=0) | FR 정석; hub가 중앙에 모이는 패턴 제거 |
| repulsion gain | ×1.0 | **×10** | 비인접 척력 강해져 hub 잡아당김 압도 |
| attraction gain | ×1.0 | **×0.3** | hub 중심 응집 압력 완화 |
| ideal_distance (k) | `sqrt(1200·800/n)` ≈ 67 (n=144) | **200 고정** | vault 크기와 무관하게 일정 spacing |
| cooling t0 | 100 | **50** | 초기 변위 폭 절반으로 좁혀 미세 조정 위주 수렴 |

모듈 상단 상수 블록으로 노출 (`LAYOUT_IDEAL_DISTANCE`, `LAYOUT_REPULSION_GAIN`, `LAYOUT_ATTRACTION_GAIN`, `LAYOUT_T0`) — 향후 튜닝/회귀 가드 진입점.

### Patch 2 — server-side default iterations (`raven/api/server.py`)

`@app.get("/api/vaults/{name}/graph")` 의 `iterations: int = Query(...)` 기본값을 `120 → 500`으로 변경. `GraphLayoutParams` (Pydantic 모델) 기본값도 동일하게 `500`. frontend가 `?iterations=`를 안 넘기므로 **기본값이 곧 사용자 경험**이라는 판단.

### Patch 3 — 회귀 가드 테스트 (`tests/test_api.py`) 4개 추가

1. **`test_spring_layout_v0611_sparse_spacing`** — hub-style 그래프(1 hub + 11 leaf)에서 페어와이즈 평균 거리 ≥ `ideal_distance/2` (=100 px), 최소 거리 > 1 px 검증
2. **`test_spring_layout_v0611_deterministic_with_new_seeds`** — uniform random + seed=0 도입 후에도 결정론 유지 확인
3. **`test_api_vault_graph_default_iterations_is_500`** — `GraphLayoutParams().iterations == 500` 가드 (기본값 회귀 차단)
4. **`test_api_vault_graph_returns_spread_coordinates`** — 실제 `GET /api/vaults/{name}/graph` 응답이 충분히 펼쳐져 있는지 end-to-end 가드

## 4. 검증 결과

```
pytest  : 380 passed (이전 376 + 신규 4) — tests/test_api.py 단독 33 passed
tsc -b  : exit 0
vitest  : 19/19 passed
```

수동 hub-style 시나리오 (`hub` + 11 leaf, 500 iter):
- hub 중심으로 정확히 정원형 분포 (반경 ≈1170 px 균등)
- 평균 pairwise 거리: 1550.8 px
- 최소 pairwise 거리: 658.4 px (ideal_distance=200의 3.3배)

## 5. 호환성·결정론

- **결정론 유지**: `random.Random(0)` seed 고정 → 같은 vault에서 항상 같은 좌표
- **하위 호환**: `iterations` 파라미터 자체는 그대로 노출 (1~2000 범위). 기본값만 변경됨
- **frontend 변경 없음**: query param 안 넘기는 기존 동작 유지, 기본값으로 자동 적용

## 6. 후속 후보

- (선택) `?iterations=` 를 frontend에서 옵션으로 노출 (Settings → "더 정확한 배치", 기본 OFF + 500)
- (선택) 큰 vault (n>500) 대응: O(n²) 척력 → Barnes-Hut quadtree 최적화 검토
- (관측) 실제 운영 vault에서 hub-style 외 sparse / chain / disconnected 케이스 시각 회귀 — 사용자 보고 대기