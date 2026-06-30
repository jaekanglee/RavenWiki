# raven v0.7.27 — 대시보드 완성도 제고 및 백링크·활성 락 연동 UI 개편

> **핵심**: Zettelkasten PKM과 에이전트 협업의 핵심 가치를 대시보드에 밀접하게 녹여냈습니다. 개별 문서의 연결을 명시하는 **실시간 백링크(Backlinks) 연동**, 다중 에이전트 환경에서 유용한 **보관소 활성 락(Active Locks) 모니터링 섹션**을 구현하였으며, 모든 주요 페이지에 **일관된 Vault 컨텍스트 헤더(`in <vault>`)** 및 **Button 공통 컴포넌트 마이그레이션**을 적용하여 UI/UX와 기능 완성도를 극대화했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.26

---

## 1. 변경 사항

### 1-1. 백링크(Backlinks) 쿼리 API 구현 및 PageView 연동
* **`raven/api/server.py`**:
  * `GET /api/vaults/{name}/pages/{slug}` API에서 wiki.db를 통해 이 문서를 가리키는 `source_slug`와 `source_title`을 역방향 조인 쿼리하여 응답에 포함시켰습니다.
  * DB가 없는 경우를 위해 본문 `[[slug]]` 정규식 기반의 rglob fallback 수집 구조도 완비했습니다.
* **`dashboard/src/routes/PageView.tsx`**:
  * 기존에 빈 배열로 고정되어 백링크를 표시하지 못하던 `BacklinksPanel`에 API가 반환하는 실시간 백링크 데이터를 바인딩하여 렌더링되게 개선했습니다.

### 1-2. 일관된 Vault 컨텍스트 헤더 (`in <vault>`) 표시
* **`dashboard/src/routes/GraphPage.tsx`**, **`dashboard/src/routes/SearchPage.tsx`**, **`dashboard/src/routes/LintPage.tsx`**, **`dashboard/src/routes/LogPage.tsx`**:
  * 사용자가 다중 보관소 환경에서 현재 어떤 vault의 콘텍스트 안에 머무르고 있는지 직관적으로 식별할 수 있도록 제목 영역 우측에 `in <vault>` 메타 텍스트를 일관성 있게 추가했습니다.

### 1-3. LogPage Raw Mode 연동
* **`raven/api/server.py`**:
  * `GET /api/vaults/{name}/log` 엔드포인트에 `raw` 쿼리 파라미터를 추가하여, `raw=true` 요청 시 `log.md` 파일 전체의 날것의 텍스트를 반환하는 스펙을 더했습니다.
* **`dashboard/src/lib/api.ts`**:
  * API 헬퍼 함수 `fetchLog`가 `raw` 플래그를 처리해 raw text를 받아올 수 있도록 타입을 확장했습니다.
* **`dashboard/src/routes/LogPage.tsx`**:
  * raw mode 버튼 활성화 시 단순히 하드코딩된 도움말만 표시하던 방식에서 벗어나, 백엔드로부터 실제 `log.md` 텍스트를 fetch하여 pre 태그 내에 그대로 렌더링하도록 완성도를 높였습니다.

### 1-4. 공통 Button 컴포넌트 마이그레이션
* **`dashboard/src/components/NewPageInline.tsx`**:
  * 스타일 토큰화 및 재사용 컴포넌트화 원칙(§13)에 따라, 날것의 `<button className="...">` 태그들을 UI 공통 컴포넌트인 `<Button>`으로 마이그레이션하여 테마 일관성과 코드 가독성을 제고했습니다.

### 1-5. Active Locks (활성 락) 모니터링 섹션 구현
* **`dashboard/src/routes/VaultManage.tsx`**:
  * 각 보관소별 stats와 함께 locks 현황 API를 병렬 호출하여 활성 락 개수 및 락 상세를 state로 관리하게 수정했습니다.
  * 요약 테이블에 `락` 개수 컬럼을 추가해 현황을 한눈에 식별할 수 있게 했습니다.
  * 테이블 하단에 락이 1개라도 존재하는 경우 `🔒 활성 락 현황` 상세 테이블을 보여주어, 어느 vault의 어떤 문서가 어떤 에이전트(`holder`)에 의해 락 상태에 걸려 있는지 획득/만료 시간과 함께 투명하게 표시했습니다.

### 1-6. NewVaultWizard 텍스트 정합성 동기화
* **`dashboard/src/components/NewVaultWizard.tsx`**:
  * v0.7.3+ 릴리스에 따라 실제 5종으로 확장된 Lite bootstrap 파일 목록에 대응하여, Step 2 확인 창의 설명 텍스트를 `4종`에서 `5종`(`_meta/agents/PROJECT-WORKFLOW.md` 포함)으로 동기화했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **Success** | `npx tsc -b --noEmit` 타입 검증 완료 |
| backend pytest | **487 passed, 1 skipped** | 백링크 API 검증 테스트 추가 및 전체 테스트 회귀 없음 ✅ |

---

## 3. 다음 단계
* **v0.7.28**: 다중 에이전트 쓰기 충돌을 웹 대시보드 상에서 수동으로 강제 Claim / Release 할 수 있는 Lock Management 인터렉션 툴 추가.
