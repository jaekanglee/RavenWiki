# raven v0.7.52 — restart-all.sh macOS Bash 3.2 호환성 및 헬스체크 수정

> **핵심**: macOS 기본 탑재 Bash(v3.2.57)에서 지원하지 않는 `declare -A`(연관 배열) 문법으로 인한 `api: unbound variable` 크래시를 해결하고, FastMCP HTTP SSE 엔드포인트 기동 확인 시 406 상태 코드를 허용하여 `restart-all` 스크립트 실행이 안정적으로 완료되도록 개선했습니다.

릴리스 일자: 2026-07-02
이전: v0.7.51

---

## 1. 변경 사항

### 1-1. 연관 배열 제거 및 Bash 3.2 호환 헬스체크 구현 ([scripts/restart-all.sh](file:///Users/jaekanglee/Desktop/Dev/Project/Raven/scripts/restart-all.sh))
* macOS 기본 셸 `/bin/bash`가 3.2 버전이라 `declare -A` 문법을 해석하지 못하고 스크립트가 비정상 종료되는 현상을 수정했습니다.
* `declare -A SERVICE_URLS` 대신 단일 헬스체크를 수행하는 `check_service` 헬퍼 함수를 정의하고 순차 호출 방식으로 변경하여 macOS 환경과의 완벽한 호환성을 확보했습니다.

### 1-2. FastMCP HTTP 헬스체크 반환 코드 허용 다변화 (200 | 406)
* `GET /mcp` 요청 시 FastMCP/Starlette 서버가 SSE handshake용 헤더 헤더 누락으로 인해 `406 Not Acceptable`을 반환하여 헬스체크가 실패로 분류되는 이슈를 수정했습니다.
* `check_service` 내 매칭 연산자에 정규식(`=~`)을 도입하여 `"200|406"`을 모두 정상 부팅 완료 신호로 인정하게 함으로써 컨테이너가 정상적으로 돌고 있음에도 헬스체크 실패로 오판해 중단되는 문제를 해결했습니다.

---

## 2. 검증 결과

### 2-1. 검증 내역
* `make restart-all` 실행 결과 모든 서비스가 정상 재기동 및 헬스체크를 통과하고, 스크립트가 성공 상태(`exit 0`)로 정상 종료되는 것을 확인했습니다.
  ```
  🩺 헬스체크 (최대 60s)…
     ✅ api        http://localhost:8765/api/vaults → 200
     ✅ mcp        http://localhost:8766/mcp → 406
     ✅ dashboard  http://localhost:5173/ → 200

  ✨ Raven 재시작 완료
  ```
* `make test` 전체 테스트 세트 검증 완료: 542 passed.

---

## 3. 다음에 가능한 것 (후속 작업)
* **포트 동적 바인딩 지원**: `scripts/restart-all.sh`에 하드코딩된 포트 번호(`8765`, `8766`, `5173`)를 `.env` 파일의 `PORT_API`, `PORT_MCP_HTTP`, `PORT_DASHBOARD` 설정값에서 동적으로 파싱해 체크하도록 추가 개선할 수 있습니다.
