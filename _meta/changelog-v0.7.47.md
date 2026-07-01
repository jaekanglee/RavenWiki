# raven v0.7.47 — 대시보드 헤더 보관소 드롭다운 전환 및 지침 당겨오기 지원

> **핵심**: 대시보드 헤더의 고정 링크였던 active vault chip을 드롭다운(`VaultPicker`) 형태로 교체하여 클릭 시 다른 보관소로 바로 전환하고 인덱스(첫 페이지)로 부드럽게 SPA 라우팅되도록 개선했습니다. 또한, 보관소 관리 페이지에서 지침 파일 정합성을 검증(Verify)하고 최신 원본 지침을 원클릭으로 덮어써서 갱신(Bootstrap/당겨오기)할 수 있는 UI 액션을 추가했습니다.

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

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| 전체 백엔드 테스트 (`pytest tests/ -q`) | **506 passed, 2 skipped** | 회귀 버그 없음 |
| 프론트엔드 컴파일/빌드 (`npm run build`) | **성공 (dist 생성)** | TypeScript compile & Vite build 완료 |
