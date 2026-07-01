# raven v0.7.46 — 그래프 레이아웃 최적화 및 테스트 환경 패스 복구

> **핵심**: 대시보드의 보관소(graph) 및 문서 상세(local graph) 뷰에서 노드와 노드 사이의 거리가 너무 멀어 선이 듬성듬성해 보인다는 사용자 피드백을 반영해, 레이아웃 알고리즘들의 인력/척력 상수를 더 조밀하고 응집력 있게 개선했습니다. 추가로 macOS에서 테스트 임시 디렉토리 심볼릭 링크 불일치로 발생하던 `/var` vs `/private/var` 경로 복구 테스트 실패 문제를 해결했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.45

---

## 1. 변경 사항

### 1-1. 그래프 레이아웃 계수 튜닝 및 Obsidian 스타일 옵션화 ([server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py))
* **`_forceatlas_layout` (ForceAtlas2 - 기본 레이아웃)**
  * **척력(Repulsion)**: `4200.0` → `2200.0` (약 47% 감소)
  * **인력(Attraction)**: `0.075` → `0.15` (2배 증가)
  * **중력(Gravity)**: `0.022` → `0.035` (약 59% 증가)
  * **고립 노드(degree=0) `mass` 제한**: mass 최솟값 `1.0` ➡️ `0.3` (척력 배율 축소로 외곽 비산 억제 및 중력 응집 유도)
  * **Collision Guard (겹침 방지 탄성)**: 노드 간 거리 $d < 45px$ 구간에서 겹침 방지 탄성력(Collision Force)을 작동시켜 노드들이 뭉개지지 않고 동글동글하게 균일한 간격을 유지하며 옵시디언 그래프 감성을 정밀하게 구현합니다.
  * **은하 중심 중력 (Community Centroid Gravity) 도입**: 동일 커뮤니티(구조적 군집) 소속 노드들이 색상뿐만 아니라 공간적으로도 끈끈하게 응집하여 '성단/은하'를 형성하도록, 매 시뮬레이션 iteration마다 실시간 계산된 커뮤니티 Centroid(무게중심)로 노드를 이끄는 커뮤니티 중력($0.065$)을 물리 계산 루프에 결합했습니다.
* **`_spring_layout` (Fruchterman-Reingold - spring 레이아웃)**
  * **목표 간격(LAYOUT_IDEAL_DISTANCE)**: `200.0` → `130.0` (px)
  * **척력 배율(LAYOUT_REPULSION_GAIN)**: `10.0` → `6.5`
  * **인력 배율(LAYOUT_ATTRACTION_GAIN)**: `0.3` → `0.45`
  * **고립 노드 척력 감쇠**: 고립 노드가 포함된 척력 계산 시 척력 계수 0.3배 축소 적용
  * **Collision Guard (겹침 방지)**: 동일하게 $d < 45px$ 구간 충돌 탄성 계산식을 적용해 노드 밀집 겹침을 원천 차단했습니다.
* **`_constellation_layout` (BFS 링 수동 배치)**
  * **반지름 공식 계수**: `145.0 + 125.0 * ring + 18.0 * math.sqrt(comp_size)` → `85.0 + 80.0 * ring + 12.0 * math.sqrt(comp_size)`
  * **고립 노드 ring 반지름 축소**: `360.0 + 55.0 * comp_i` ➡️ `160.0 + 25.0 * math.sqrt(comp_i)` (고립 노드가 우주 밖으로 이탈하여 전체 캔버스의 정규화 스케일을 극단적으로 왜곡/축소시키는 현상 차단)

### 1-2. 그래프 제어판 간소화 및 캔버스 영역 극대화 (UX 개선) ([GraphPage.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/GraphPage.tsx))
* 일반 사용자 관점에서 불필요하고 개념이 모호하던 **"레이아웃 종류(Select)"** 선택 박스를 UI에서 과감히 제거했습니다.
* 유용하고 필수적인 **"문서 검색(TextField)"** 및 **"타입 필터(Select)"** 기능은 피드백에 따라 온전히 유지하여, 탐색 편의성을 지켰습니다.
* **인사이트 카드(핵심 허브, 고립 문서, 타입 분포)의 완전 제거**: 그래프 탐색 몰입도를 해치고 시야를 좁히던 좌측 하단의 3개 인사이트 통계 카드 패널을 완전히 제외하여, 그래프 캔버스가 더 넓은 시야를 가로로 길게 확보할 수 있도록 극대화했습니다.
* **헤더 공간 압축**: `PageHeader` 밑의 장황한 `subtitle` 설명을 지워 세로 여백을 크게 줄였으며, 툴바의 요약 메타정보에서도 더 이상 사용하지 않는 `레이아웃 atlas` 항목을 제거했습니다.

### 1-3. 양방향 상호 참조(Loop) 엣지 단일화 최적화 ([server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py))
* 두 문서가 서로를 동시에 링크하는 양방향 상호 링킹(`A ↔ B`) 또는 중복 엣지 정보가 그래프 엔드포인트 `/api/vaults/{name}/graph`에서 그대로 두 개의 별개 엣지로 반환되던 현상을 수정했습니다.
* 백엔드의 DB 조회 분기 및 rglob fallback 분기 모두에서 방향에 관계없이 엣지를 고유 튜플 `(min(u, v), max(u, v))`로 식별하여 중복을 필터링하도록 개선했습니다.
* **효과**:
  * 프론트엔드로 전달되는 엣지 데이터의 규모가 축소되어 렌더링 성능이 향상되고, 캔버스 상에서 선 두 개가 겹쳐 보이던 시각적 노이즈가 제거되었습니다.
  - force 레이아웃 계산 시 상호 링킹 노드끼리 과다한 인력(2배의 힘)을 받아 노드가 비정상적으로 겹치거나 달라붙던 문제가 물리적으로 해결되었습니다.

### 1-4. macOS 임시 경로 매칭 테스트 픽스 ([test_vault_repair.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/tests/test_vault_repair.py))
* macOS 환경에서 `tempfile.mkdtemp` 반환 경로(`/var/folders/...`)가 런타임에 `/private/var/folders/...`로 해석되어 `test_vault_repair.py` 내 vault 복구(repair) 단언문에서 `AssertionError`가 발생하던 문제를 수정했습니다.
* fixture 단계에서 `Path.resolve()`를 붙여 심볼릭 링크가 풀린 절대 경로로 고정하여 macOS 환경에서도 테스트가 안정적으로 수행되도록 개선했습니다.

### 1-5. 줌 레벨 기반 점진적 세부 가시화 (Progressive Disclosure) 및 성운 가스 효과 구현 ([GraphCanvas.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/GraphCanvas.tsx))
* **Community Nebula Glow (성운 구름 오버레이)**: 각 커뮤니티의 Centroid와 반경을 기준으로 몽환적인 `radial-gradient` 성운 구름 노드(`NebulaNode`)를 캔버스 하단(zIndex=-10)에 동적으로 렌더링했습니다.
* **은하군 대표 허브 라벨 노출**: 각 커뮤니티(군집) 내에서 연결선이 가장 많은 핵심 Hub 노드의 타이틀을 추출하여 `"{Hub Title} 은하군"` 형태로 자동 명명하고, 이를 성운 노드 내부 중앙에 선명하게 띄워 줌아웃 상태에서도 보관소 내 군집 성격을 한눈에 볼 수 있도록 시각화 효과를 더했습니다.
* **줌 레벨별 페이드 아웃/인 연동**:
  * **줌아웃(우주/은하 뷰)**: 노드 라벨 텍스트가 페이드아웃되어 텍스트 겹침 노이즈를 100% 제거하고, 은은한 성운 가스 구름 및 은하군 대표 이름표만 캔버스에 도드라지게 하여 거시적인 구조 파악을 돕습니다.
  * **줌인(성단/별 상세 뷰)**: 성운 구름과 군집 대표 이름표가 조용히 투명하게 걷히며, 개별 노드의 상세 텍스트 라벨이 서서히 페이드인되도록 줌 상태에 연동했습니다.

### 1-6. 클러스터(은하군) 필터링 컨트롤 UI 추가 ([GraphPage.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/GraphPage.tsx))
* 대시보드 좌측 제어판 영역에 **"클러스터 필터"** SelectField를 정식으로 추가했습니다.
* 보관소의 구조적 관계(Modularity)로 묶여 분류된 클러스터들을 문서 개수와 대표 타이틀이 병기된 드롭다운 항목(예: `React 은하군 (#0, 12개)`)으로 직접 탐색 및 개별 필터링할 수 있도록 제공하여 클러스터링 기반 탐색 편의성을 보장했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| 백엔드 API 테스트 (`pytest tests/test_api.py -k graph`) | **10 passed** | 그래프 API 검증 통과 |
| 복구 기능 테스트 (`pytest tests/test_vault_repair.py`) | **8 passed** | macOS 임시 경로 불일치 해결 완료 |
| 전체 백엔드 테스트 (`pytest tests/ -q`) | **506 passed, 2 skipped** | 회귀 버그 없음 |
| 프론트엔드 컴파일/빌드 (`npm run build`) | **성공 (dist 생성)** | TypeScript compile & Vite build 완료 |
| 프론트엔드 단위 테스트 (`npm run test -- --run`) | **116 passed** | UI 회귀 없음 |

---

## 3. 다음 단계
* 사용자가 대시보드 화면에서 본인 입맛에 맞춰 인력/척력 강도를 슬라이더로 조절할 수 있도록 `GraphCanvas` 툴바에 슬라이더 옵션을 도입하는 방안을 고려해 볼 수 있습니다.
