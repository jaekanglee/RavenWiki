# raven v0.7.38 — 볼트 삭제 API 디렉토리 유실 예외 처리 및 JSON 파싱 에러 수정

> **핵심**: 대시보드에서 볼트 삭제 시, 디스크 상에 해당 볼트 디렉토리가 존재하지 않는 경우 `Vault.load`가 `FileNotFoundError`를 던져 500 에러(Unexpected token 'I', "Internal S"...)가 나던 문제를 해결했습니다. 이제 디스크에 디렉토리가 없더라도 레지스트리에서 정상적으로 제거(Unregister)될 수 있도록 예외 처리를 보완했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.37

---

## 1. 배경

* **상황**: 대시보드의 볼트 관리 화면에서 볼트를 삭제하려 할 때, `⚠ Unexpected token 'I', "Internal S"... is not valid JSON` 에러가 발생함.
* **원인**: 백엔드의 `DELETE /api/vaults/{name}` 엔드포인트가 내부적으로 `Vault.load(meta)`를 호출할 때, 디스크 상에 해당 볼트 디렉토리가 존재하지 않으면 `FileNotFoundError`가 던져지고, FastAPI가 이를 캐치하지 못해 `500 Internal Server Error` (plain text)를 반환했습니다. 이로 인해 프론트엔드가 이를 JSON으로 파싱하려다가 에러가 났습니다.
* **해결 방안**: 삭제 요청 시 디스크 경로 존재 여부를 먼저 확인하고, 존재하지 않는다면 디스크 삭제 시도 없이 레지스트리 등록 해제(unregister) 절차만 정상 수행 후 성공(`{"ok": true}`) 처리하도록 보완했습니다.

---

## 2. 변경 사항

### 2-1. 백엔드 볼트 삭제 API 수정 (`raven/api/server.py`)

* **경로 존재 여부 선 검증**: `_vault_or_404` 대신 `registry().get(name)`를 먼저 사용해 메타데이터를 가져온 후, `meta.path.exists()`를 검사합니다.
* **디렉토리 유실 시 조기 처리**: 디렉토리가 유실된 상태라면, `Vault.load`를 호출하지 않고 `registry().remove(name)`를 호출해 레지스트리에서만 해제하고 성공 응답을 반환합니다.

### 2-2. 백엔드 API 테스트 케이스 추가 (`tests/test_api.py`)

* **`test_api_delete_vault` 구현**:
  * 존재하지 않는 볼트 삭제 시도 (404 반환 검증).
  * 디렉토리가 디스크에서 유실된 경우에도 `DELETE` 요청 시 성공 및 레지스트리 해제 검증.
  * 콘텐트가 남아있는 볼트를 `force=True` 옵션 없이 삭제하려 할 때 삭제 실패 및 요약 정보 반환 검증.
  * `force=True`를 전달했을 때 디스크 및 레지스트리에서 삭제 성공 검증.

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `pytest tests/` 전체 | **490 passed, 1 skipped** | 신규 작성한 `test_api_delete_vault`를 포함해 모든 테스트 통과 |
| `git status` 변경 목록 일치 | **Success** | `raven/api/server.py`, `tests/test_api.py`, `_meta/changelog-v0.7.38.md` 변경 |

---

## 4. 다음 단계

* 추가적인 볼트 상태 관련 API 예외 처리 강화.
