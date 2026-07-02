# raven v0.7.49 — 그래프 atlas layout 성운 군집화 강화

> **핵심**: 다크 모드 시인성 개선(v0.7.48)에 이어, 그래프 atlas layout의 force 파라미터를 조정해 **"성운처럼 군집이 뚜렷한"** 미학을 강화했습니다. 같은 community에 속한 노드들을 centroid로 빨아들이는 **은하 핵 인력(community_hub)**을 0.10 → 0.25로 2.5배 강화하고, 노드 간 척력(repulsion)을 1400 → 1100으로 약화시켜 **클러스터 내부 응집도(intra-cluster spread)를 약 11% 감소**시켰습니다. iterations 320 → 400은 repulsion 약화로 인한 수렴 시간 보강입니다. 결정론(deterministic) / `normalize_layout` contract(중심=0, scale=±500)는 그대로 유지되며 frontend는 무변경입니다.

릴리스 일자: 2026-07-02
이전: v0.7.48

---

## 1. 변경 사항

### 1-1. 은하 핵 인력 2.5배 강화 ([server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py), `_forceatlas_layout` L1017)
* 같은 community에 속한 노드들을 centroid로 끌어당기는 가중치를 `0.10` → `0.25`로 올렸습니다.
* `_forceatlas_layout`는 이미 `communities`를 매 iteration마다 centroid로 묶어 가속화하기 때문에 (`_louvain_communities` 결과를 layout 전에 미리 계산), 이 가중치 변경만으로 동일 입력에서도 **성운 효과가 뚜렷**해집니다.
* frontend에서 `커뮤니티별 색상`을 켜지 않아도 backend layout은 항상 community-aware이므로, 사용자가 색 토글을 안 한 상태에서도 이 효과는 보입니다.

### 1-2. 척력 약화 & 수렴 안정 ([server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py), L941, L865)
| 파라미터 | v0.7.48 | v0.7.49 | 의도 |
|---|---|---|---|
| `repulsion` (노드 간 척력) | 1400.0 | **1100.0** | 척력 약화 → 노드들이 더 가까이 머물 수 있음 |
| `attraction` (edge 인력) | 0.15 | 0.15 | 변경 없음 — edge로 연결되지 않은 노드 간 분리는 유지 |
| `gravity` (중심 인력) | 0.045 | 0.045 | 변경 없음 |
| `iterations` (수렴 반복) | 320 | **400** | repulsion 약화로 평형점에 도달하는 데 더 많은 iteration 필요 |
| community_hub (은하 핵 인력) | 0.10 | **0.25** | 핵심 변경 — 2.5배 강화 |

`steps = max(40, min(iterations, 500))` 가드(상한 500)는 유지되어 무한 수렴/성능 저하를 방지합니다.

### 1-3. 결정론 & contract 보존
* `_forceatlas_layout`는 `random`을 사용하지 않고 seed는 `_constellation_layout`의 결정론적 결과에 의존하므로 **입력이 같으면 출력 좌표도 결정론적**입니다.
* `_normalize_layout`은 출력을 center=0, scale=±500로 정규화하므로 frontend의 `minZoom 0.005` / `maxZoom 2` / `fitView` 동작이 그대로 유효합니다.
* `vault_graph` 엔드포인트의 response schema(`nodes[i].x, .y, .community`)는 변경 없음.

---

## 2. 검증 결과

### 2-1. 정량 검증 (합성 3-cluster × 12-nodes)

동일 입력에 대해 v0.7.48(v0.7.47과 동일) / v0.7.49 파라미터로 각각 layout을 계산하고, 클러스터별 통계 비교:

| 지표 | v0.7.48 (before) | v0.7.49 (after) | 변화 |
|---|---|---|---|
| C0 intra-cluster spread (작을수록 뭉침) | 96.8 | 86.3 | **−10.8%** |
| C1 intra-cluster spread | 96.2 | 85.3 | **−11.3%** |
| C2 intra-cluster spread | 96.4 | 85.9 | **−10.9%** |
| C0↔C1 centroid 거리 | 437.1 | 417.6 | −4.5% |
| C0↔C2 centroid 거리 | 433.9 | 418.4 | −3.6% |
| C1↔C2 centroid 거리 | 810.7 | 790.7 | −2.5% |

**읽는 법**: intra-cluster spread가 약 11% 감소(같은 community 안 노드들이 centroid에 더 가까이 뭉침)하여 "성운 응집도"가 뚜렷해졌습니다. centroid 간 거리 -3% 정도는 repulsion 약화의 의도된 trade-off입니다 — 가깝게 뭉친 군집이 살짝 더 모이는 효과이며, normalize_layout의 scale=±500 안에서 화면 배치는 여전히 명확합니다.

### 2-2. 회귀 가드

| 항목 | 결과 | 비고 |
|---|---|---|
| `pytest tests/test_api.py tests/test_contracts.py` | **64/64 passed** | API + contract 회귀 없음 |
| `git diff --stat` | 1 file, +10/-3 | surgical 패치 |
| 결정론 | ✅ | `random` 미사용, seed = `_constellation_layout` 결정론 |
| Contract | ✅ | `nodes[i].x/y/community` schema 무변경, normalize_layout output 동일 |

### 2-3. 사용자 시각 검증 (권장)
1. `make dev`로 Dashboard 띄우기 (port 5173 + 8765)
2. `Cmd+Shift+R`로 강력 새로고침 (PWA 캐시 무효화)
3. `/graph` 페이지 진입
4. **확인 포인트**:
   - 같은 색(또는 같은 community)의 노드들이 **이전보다 더 밀집된 덩어리**로 보임
   - 노드 간 거리는 좁아져도 collision guard(20px) 때문에 겹치진 않음
   - 군집과 군집 사이에는 여전히 분리가 보임 (normalize_layout 보존)
5. 너무 뭉치거나 / 너무 분리되면 B안(attraction↑, collision↓)으로 한 단계 더 다룰 수 있음

---

## 3. 다음에 가능한 것 (선택)

* **B안 (응집 강화, +)**: `attraction` 0.15 → 0.35, collision 20px → 14px — edge 응집과 군집 내 밀도 모두 강화. 큰 hub가 화면 작아 보일 수 있어 normalize_layout 영향 검증 필요.
* **사용자 가중치**: frontmatter의 `importance` 필드를 community centroid 가중치에 더해, "중요한 hub가 속한 community가 더 크게/조밀하게 보이게" 하는 가중치 옵션.
* **zoom-out decay**: 노드 수가 500+ 일 때 zoom-out 시 자동으로 intra-cluster edge bundling을 적용 — 별도 패치.
* **커뮤니티 가스 헤일로 (C안)**: NebulaNode 컴포넌트(v0.6.15+ 도입)를 weight≥3 hub 주변에 자동 배치해 진짜 성운 같은 무광 가스 layer 추가. 큰 패치(30-50줄 + ADR).

---

## 4. 비고

* v0.7.47(은하수 미학)과 v0.7.48(dark mode 시인성)에 이은 **v0.7.49(성운 군집화) 시리즈**의 세 번째 패치입니다. 사용자 north star("옵시디언 식 미학 + 자유 vault") 범주 안에서 그래프 가독성을 점진 강화하는 흐름입니다.
* 의미 있는 데이터(200+ 노드)에서는 11% 응집도 향상이 시각적으로 더 도드라집니다 — 소규모 vault(10-20 노드)에서는 변화가 미세할 수 있습니다.
