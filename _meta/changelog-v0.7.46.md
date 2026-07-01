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

### 1-5. 줌 레벨 연동 4단계 다단계 우주 줌 스케일링 (Multiscale Aggregation) ([GraphCanvas.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/GraphCanvas.tsx))
* 별자리형(atlas) 레이아웃 모드에서 단순 단일 축소를 넘어, 줌 레벨(`zoom`)에 연계하여 노드와 엣지를 4단계의 우주적 은유(Cosmic Metaphor) 스케일로 동적 클러스터 병합(Collapse/Expand)처리하는 다차원 가시화 아키텍처를 구현했습니다:
  1. **Level 4: SUPERCLUSTER (초은하단 뷰 - `zoom < 0.20`)**:
     * 보관소의 최상위 대분류 폴더(1뎁스 경로)를 기준으로 노드를 뭉쳐 단 3~5개의 큼직한 메인 노드(`CONCEPT 초은하단`, `LOG 초은하단` 등)와 초은하단 간의 거대한 골격 연결선(Super Edge)들만 노출합니다.
  2. **Level 3: GALAXY (은하 뷰 - `0.20 <= zoom < 0.42`)**:
     * Louvain 커뮤니티 단위로 병합된 10~15개의 은하 노드들을 렌더링하며, 라벨은 군집 내 대표 문서명으로 표기합니다.
  3. **Level 4: NEBULA / STAR SYSTEM (성운/항성계 뷰 - `0.42 <= zoom < 0.72`)**:
     * 2뎁스 하위 폴더(예: `concept/react`) 단위로 좀 더 조밀하게 뭉친 서브클러스터 노드들로 가독성을 스케일링합니다.
  4. **Level 1: PLANET / MOON (개별 행성 및 위성 뷰 - `zoom >= 0.72`)**:
     * 개별 문서들이 Planet(일반 행성)으로 모두 해체되어 펼쳐집니다.
     * 이때, 유입 링크가 1개 이하인 고립/보조 노드는 **Moon (위성)**으로 판정해 노드 크기를 매우 작게(4px) 축소하고 투명도를 주어(`opacity: 0.55`), 큼직하게 빛나는 행성 노드들 곁에 매달려 공전하는 듯한 시각적 위계를 극대화했습니다.
  * **좌표 보간형 수렴/발산 애니메이션 탑재**: 노드의 개수를 매번 재생성하여 필터링하는 방식 대신, 원래 노드들의 갯수와 고유 ID를 온전히 보존한 채 줌 레벨에 따라 자식 노드들의 목표 좌표를 대표 노드의 Centroid 좌표로 수렴(Collapse)시키거나 원래 좌표로 펼쳐지도록 발산(Expand) 연산하는 보간형 애니메이션 기법을 채택했습니다. CSS transition(`.react-flow__node`)과 연계되어 노드와 엣지들이 우주 성운의 소용돌이처럼 한곳으로 빨려 들어가거나 사방으로 수려하게 뻗어 나가는 650ms 트랜지션 인터랙션을 완성했습니다.

### 1-6. 클러스터 필터링 컨트롤 UI 추가 및 라벨 정돈 ([GraphPage.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/GraphPage.tsx))
* 대시보드 좌측 제어판 영역에 **"클러스터 필터"** SelectField를 추가했습니다.
* 드롭다운 옵션에서도 불필요한 "은하군" 꼬리표를 떼어내고, 군집 대표 문서의 순수 명칭과 군집 ID, 문서 개수만 정갈하게 표기하도록 개선했습니다 (예: `React (#0, 12개)`).

### 1-7. YAML Frontmatter 'importance' 연계 하이브리드 노드 가중치 수식 탑재 ([server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py))
* 에이전트나 사람이 문서를 구조화할 때 수동/의미론적으로 중요도를 부여할 수 있도록, 각 마크다운 파일의 YAML frontmatter 내 `importance` 속성을 파싱하는 기능을 추가했습니다.
* **하이브리드 가중치 공식 적용**:
  * `weight = int(in_degree + (importance - 1) * 3.5)`
  * 링크 유입 수(In-Degree)에 기반한 기존의 자동 크기 조절 구조와 상호 호환성을 유지하면서, 중요하게 지정된 핵심 문서가 시각적으로 거대하고 밝게 반짝이도록 크기 가중치 보정을 결합했습니다.
  * 백엔드 레이아웃 연산 단계에서도 이 가중치가 질량(`mass`) 및 관성으로 결합하여 중요한 문서가 은하의 중심부에 묵직하게 앵커링되도록 제어했습니다.

### 1-8. 폴더 기반 계층형 트리 레이아웃 (Hierarchical Layout) 및 선택 UI 추가 ([server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py), [GraphPage.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/GraphPage.tsx))
* 별자리형(Force-directed)의 자유도 높은 포진 방식과 더불어, 지식 보관소의 폴더 깊이와 계층 구조를 직관적으로 파악할 수 있는 **"계층형 트리 레이아웃(Hierarchical Layout)"** 알고리즘을 백엔드에 신규 구현했습니다.
  - **Y 좌표**: 파일 디렉토리 경로의 깊이(depth)에 비례하여 위에서 아래로 정돈 배치합니다.
  - **X 좌표**: 동일 깊이 레이어 내의 노드 개수에 맞게 가로 폭을 균등 할당하여 사전식(Alphabetical) 결정론적 배치를 수행합니다.
  - **좌표 정규화**: 계산된 좌표를 `_normalize_layout`에 전달해 `[-500, 500]` 스케일로 맞춤으로써 React Flow의 화면 밖으로 노드가 이탈하지 않고 화면 중앙(fitView)에 최적의 줌으로 앵커링되도록 정밀 조율했습니다.
* **레이아웃 모드 선택 UI 추가**:
  * 제어판 영역에 **"레이아웃 모드"** SelectField를 복구하여 사용자가 언제든지 실시간으로 `별자리형 (네트워크)`과 `트리형 (계층 구조)` 뷰를 실시간 선택 및 교환하며 탐색할 수 있도록 편의를 제공했습니다.

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
