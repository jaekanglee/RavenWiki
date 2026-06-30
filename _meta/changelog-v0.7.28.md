# raven v0.7.28 — 보관소 활성 락(Active Locks) 강제 해제 기능 구현

> **핵심**: 보관소 관리 페이지의 락 모니터링 섹션에 인터랙티브한 제어권을 부여했습니다. 백엔드에 **락 강제 해제(Release Lock) API**를 설계하고, 대시보드 UI에 **락 강제 해제(Unlock) 액션 버튼**을 추가하여 사람이 에이전트의 충돌/교착 상태 락을 직접 모니터링하고 해제할 수 있도록 지원을 강화했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.27

---

## 1. 변경 사항

### 1-1. 락 강제 해제 DELETE API 엔드포인트 설계
* **`raven/api/server.py`**:
  * `DELETE /api/vaults/{name}/locks` API를 추가했습니다.
  * 쿼리 매개변수로 특정 `slug`를 전달받아, 해당 보관소의 `.mcp/locks.json` 저장소에서 락 엔트리를 강제로 삭제하고 원자적으로 저장해주는 락 해제 로직을 구현했습니다.

### 1-2. 대시보드 락 강제 해제(🔓 해제) 인터렉션 구현
* **`dashboard/src/routes/VaultManage.tsx`**:
  * 활성 락 상세 테이블의 각 행 마지막 열에 `🔓 해제` 액션 버튼을 신설했습니다.
  * 해당 버튼 클릭 시 사용자 확인 창(`window.confirm`)을 거친 후, 백엔드 DELETE 락 API를 호출하여 즉시 락을 해제하고 보관소 통계를 새로고침하는 `handleUnlock` 함수를 연동했습니다.
  * 이전 v0.7.27 구현 중 락 상세 필드 스키마가 실제 백엔드의 `actor`, `since` 규격과 달라 렌더링되지 않거나 잘못 파싱되던 에러(KeyError, Date parsing 오류)를 백엔드 락 스토어 규격에 부합하도록 교정하였습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **Success** | `npx tsc -b --noEmit` 타입 검증 통과 |
| backend pytest | **488 passed, 1 skipped** | 락 해제 API 테스트(`test_locks_api_list_and_delete`) 추가 및 통과 완료 ✅ |

---

## 3. 다음 단계
* **v0.7.29**: 지식 정원 가꾸기(`GardenPage.tsx`)에서 잡초(Stale)로 식별된 문서들을 일괄 체크박스 선택하여 한 번에 삭제/아카이빙 처리할 수 있는 Batch Action UI 구현.
