# raven v0.7.47 — 대시보드 헤더 보관소 드롭다운 전환 및 지침 당겨오기 지원

> **핵심**: 대시보드 헤더의 고정 링크였던 active vault chip을 드롭다운(`VaultPicker`) 형태로 교체하여 클릭 시 다른 보관소로 바로 전환하고 인덱스(첫 페이지)로 부드럽게 SPA 라우팅되도록 개선했습니다. 또한, 보관소 관리 페이지에서 지침 파일 정합성을 검증(Verify)하고 최신 원본 지침을 원클릭으로 덮어써서 갱신(Bootstrap/당겨오기)할 수 있는 UI 액션을 추가했습니다. 추가로, 지침 당겨오기 시 기존 파일이 존재하면 덮어쓰지 않고 그냥 건너뛰던 오작동 버그를 수정했으며, 그래프 뷰가 옵시디언 고유의 밀도 높은 밤하늘 은하수(Constellation) 미학을 가질 수 있도록 레이아웃 파라미터 및 연결선 스타일을 정밀하게 튜닝하고 줌 연동 노드 뭉침/풀림(클러스터 병합) 기능을 제거했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.46

---

## 1. 변경 사항

### 1-1. VaultPicker SPA 라우팅 연동 ([VaultPicker.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/VaultPicker.tsx))
* `window.location.reload()` 기반의 강제 새로고침 방식을 제거하고 React Router의 `useNavigate`를 통합했습니다.
* 다른 보관소를 선택하면 `/api/vaults/{name}/pages?top_k=1` API를 즉시 조회하여 해당 보관소의 첫 페이지(slug)가 존재하는 경우 그 페이지(`/page/{vault}/{slug}`)로 라우팅하며, 문서가 존재하지 않는 등의 예외 상황에서는 보관소 관리 페이지(`/vault/manage`)로 이동하도록 안전장치(fallback)를 적용했습니다.

### 1-2. 헤더 액티브 보관소 칩을 드롭다운으로 교체 ([Layout.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/Layout.tsx))
* 기존에 `/vault/manage`로 연결되는 단순 읽기 전용 앵커 칩(`active-vault-chip`)을 `VaultPicker` 드롭다운 컴포넌트로 대체했습니다.
* 드롭다운을 통해 헤더에서 직접 다른 보관소로 바로 전환 가능하며, 사이드바 트리를 포함한 전체 UI가 새로고침 없이 유연하게 SPA 방식으로 갱신되도록 연동했습니다.

### 1-3. 보관소 관리 페이지 내 '지침 검증' 및 '당겨오기' 액션 추가 ([VaultManage.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/routes/VaultManage.tsx))
* **지침 검증 (🔍)**: 해당 보관소 내 지침 파일들이 최신 원본 템플릿과 일치하는지 백엔드 API(`/api/vaults/{name}/verify`)를 통해 해시(SHA256) 단위로 체크하여 토스트 메시지로 상태를 제공합니다.
* **지침 당겨오기 (🔄)**: 보관소 지침 파일들(`SCHEMA.md`, `RULES.md`, `README.md` 등)을 Raven 소스코드에 포함된 최신 템플릿 원본으로 덮어쓸 수 있도록 `/api/vaults/{name}/bootstrap` API를 연동했습니다. 덮어쓰기 전 사용자 경고 모달을 띄워 데이터 손실을 사전에 예방합니다.
* 테이블 뷰(Table) 및 모바일/컴팩트 카드 뷰(Card) 모두에 두 액션 아이콘을 배치했습니다.

### 1-4. 지침 당겨오기(Bootstrap) 시 파일 덮어쓰기 미작동 버그 수정 ([server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py), [__main__.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/cli/__main__.py))
* 기존 `_bootstrap_lite` 메서드는 이미 파일이 존재할 시 덮어쓰지 않고 그냥 건너뛰어(continue), '당겨오기 완료' 후에도 정합성 불일치가 해소되지 않는 모순이 있었습니다.
* 이를 해결하기 위해 백엔드 API 및 CLI 부트스트랩 명령어가 `_bootstrap_lite` 대신 파일 덮어쓰기가 보장되는 `v.sync_meta(lite=True, force=True)`를 수행하도록 수정했습니다.

### 1-5. 줌 연동 노드 뭉침(클러스터 병합) 제거 및 옵시디언 식 촘촘한 은하수 그래프 튜닝 ([GraphCanvas.tsx](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/components/GraphCanvas.tsx), [server.py](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/raven/api/server.py), [globals.css](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/dashboard/src/styles/globals.css))
* **동적 클러스터 뭉침(Collapse) 제거**: 줌 레벨에 따라 노드들이 임의의 무게중심으로 뭉치고 풀어져서 시야를 복잡하게 만들던 Cosmic scale 뭉침 연산(Supercluster/Galaxy/Nebula 모드)을 완전히 배제했습니다. 항상 모든 개별 노드가 본연의 좌표(`PLANET` 모드)에 배치됩니다.
* **노드 응집도 및 밀도 극대화**: ForceAtlas2 레이아웃의 척력(`repulsion`)을 `2200.0` ➡️ `1400.0`으로 줄이고, 중력(`gravity`)을 `0.035` ➡️ `0.045`로, 커뮤니티 핵 인력 배율을 `0.065` ➡️ `0.10`으로 강화하여 노드들이 중심부로 촘촘히 달라붙어 덩어리진 성단 형태를 이루게 했습니다.
* **Collision Guard 완화**: 겹침 방지 임계거리(`min_dist`)를 기존 `45.0px` ➡️ `20.0px`로 낮추고 밀어내는 탄성 계수를 강화하여, 큰 허브 노드 주변의 보조 노드들이 넓게 흩어지지 않고 밤하늘 은하수의 조밀한 아라베스크 무늬처럼 엉키도록 유도했습니다.
* **엣지(연결선) 가시성 투명화**: 수많은 연결선이 화면을 둔탁하게 덮지 않고 안개처럼 얇고 은은하게 녹아들도록, 라이트 모드(`rgba(100, 116, 139, 0.28)`)와 다크 모드(`rgba(148, 163, 184, 0.22)`)의 `--graph-edge` 투명도를 대폭 조율했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| 전체 백엔드 테스트 (`pytest tests/ -q`) | **506 passed, 2 skipped** | 회귀 버그 없음 |
| 프론트엔드 컴파일/빌드 (`npm run build`) | **성공 (dist 생성)** | TypeScript compile & Vite build 완료 |
