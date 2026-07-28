# Raven v0.7.176 — Tailscale/원격 IP CORS 허용 및 원격 연결/삭제 디버깅 개선

**날짜**: 2026-07-28  
**유형**: 버그 수정 및 Remote UI/API 디버깅 보강

---

## 1. 개요 및 배경

테일스케일(Tailscale) 또는 동일 사설망(LAN) 환경에서 다른 PC(`100.x.x.x` 또는 `192.168.x.x`)의 Raven API/Dashboard로 연결을 시도할 때, 백엔드의 CORS origin 제한 정책으로 인해 브라우저 단에서 요청이 차단(`TypeError: Failed to fetch`)되고, UI에서 원인을 알 수 없는 "Load failed" 혹은 연결 실패 상태에 빠지는 현상이 발생했습니다.
또한, 호스트가 오프라인 상태일 때 호스트를 삭제할 방법이 제한적이거나, Vault/API 삭제 실패 시 `[object Object]` 등 모호한 메시지로 표출되던 문제를 전면 개선했습니다.

---

## 2. 주요 변경 사항

### 2.1 백엔드 CORS regex 추가 (`raven/api/server.py`)
- `CORSMiddleware`에 `allow_origin_regex` 매개변수 도입.
- **허용 대역**:
  - 로컬 (`localhost`, `127.0.0.1`)
  - Tailscale 대역 (`100.64.0.0/10` → `100.\d{1,3}.\d{1,3}.\d{1,3}`)
  - 사설망 대역 (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`)
- Tailscale IP(`100.121.237.40` 등)를 이용한 원격 웹 대시보드 API 통신이 기본적으로 CORS 정책에 의해 차단되지 않도록 보장했습니다.

### 2.2 삭제 및 유실 Vault 안전 등록 해제 (`raven/api/server.py`)
- `DELETE /api/vaults/{name}` API 호출 시, Vault 디렉토리가 미존재하거나 디스크 유실/접근 불가 상태(`Vault.load` 실패)인 경우에도 500 에러를 던지지 않고 안전하게 등록 해제(`registry().remove(name)`)가 수행되도록 예외 처리했습니다.

### 2.3 프론트엔드 에러 디버깅 메시지 및 삭제 기능 보강 (`dashboard/src/`)
- **`formatApiError` 헬퍼 도입 (`dashboard/src/lib/api.ts`)**:
  - 네트워크/CORS 에러 (`Failed to fetch`), FastAPI JSON detail 객체(`{ reason, hint, ... }`), HTTP 에러 등을 직관적이고 상세한 한글 디버깅 메시지로 정제.
- **호스트 관리 모달 내 개별 삭제 기능 (`dashboard/src/components/HostPicker.tsx`)**:
  - 오프라인 상태이거나 선택되지 않은 원격 호스트라도 모달 목록에서 삭제(🗑)할 수 있도록 "등록된 원격 호스트 목록" 섹션 및 삭제 버튼 배치.
- **Vault 삭제 에러 상세 표출 (`dashboard/src/routes/VaultManage.tsx`)**:
  - `deleteVault` 수행 시 발생한 오류 원인과 백엔드 힌트를 `formatApiError`로 화면에 명확하게 표출.

---

## 3. 검증

- **TypeScript 타입 체크**: `npx tsc -b` (dashboard) 실행 완료 — 오류 0건 pass.
- **백엔드 라우팅 및 CORS 검증**: CORS regex 패턴 정의 및 `delete_vault` exception handling 안전 조치 적용 완료.
