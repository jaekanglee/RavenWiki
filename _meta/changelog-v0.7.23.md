# raven v0.7.23 — 시스템 아키텍처 문서화 및 API vaults: [] 컨테이너 경로 버그 해결

> **핵심**: Raven의 4-Layer 시스템 아키텍처 공식 가이드를 구축하고, Docker 컨테이너 구동 시 호스트와 컨테이너 간의 vault 절대 경로 격리로 인해 API 응답이 `vaults: []`로 반환되던 해묵은 마운트 경로 버그를 완벽히 해결했습니다.

릴리스 일자: 2026-06-30
이전: v0.7.22

---

## 한 줄 요약

Raven의 4-Layer 계층 관계와 데이터 흐름을 Mermaid 다이어그램으로 시각화하여 `docs/` 및 `_meta/`에 공식 문서화하고, Docker 환경에서 호스트 절대 경로 매핑 불일치로 발생하던 API `vaults: []` 응답 버그를 레지스트리 경로 폴백(fallback) 및 Compose 환경변수 수정을 통해 완벽히 해결했습니다.

---

## 1. 변경 사항

### 1-1. 아키텍처 공식 문서 추가
* **`docs/architecture.md`**: Raven의 4개 계층(Data, Engine, Interface, Client/UX), 계층별 파일 및 데이터베이스 스키마, CRUD 데이터 흐름(Sequence Diagram), 주요 아키텍처 결정(D7-D9) 및 격리 정책(Lite Bootstrap, Tier Boundary)을 상세하게 기술한 공식 문서를 생성하였습니다.
* **`_meta/raven-architecture.md`**: 기존 `_meta/index.md`에서 깨진 링크로 남아있던 `[[raven-architecture]]` 대상을 생성하고, `docs/architecture.md`로 이어지도록 연동하여 위키 무결성을 복구했습니다.

### 1-2. API vaults: [] 응답 버그 수정 (Docker 환경 경로 격리 문제)
* **원인**: `docker-compose.yml`에서 컨테이너 내부 `WIKI_VAULTS_DIR` 값을 호스트 절대 경로인 `${RAVEN_VAULTS_DIR}`(예: `/Users/jaekanglee/Raven`)로 그대로 넘겨주었으나, 실제 볼트 디렉토리는 컨테이너 내부 `/vaults`에 마운트되어 있었습니다. 이로 인해 컨테이너 내 파이썬 프로세스가 레지스트리 파일 및 볼트 경로를 찾지 못해 빈 목록(`vaults: []`)을 반환했습니다.
* **해결**:
  1. `docker-compose.yml` 내 `api` 및 `mcp-http` 서비스의 `WIKI_VAULTS_DIR` 환경변수를 `/vaults`로 정정하여 컨테이너 내부 마운트 경로와 일치시켰습니다.
  2. `raven/core/registry.py` 내 `VaultMeta.from_json`에서 레지스트리에 저장된 호스트 절대 경로(예: `/Users/jaekanglee/Raven/default`)가 컨테이너에서 조회되지 않을 경우, 현재 환경변수(`WIKI_VAULTS_DIR` = `/vaults`) 하위의 동일한 이름의 폴더로 동적 fallback 처리(경로 재해석)하도록 구현했습니다. 이로써 호스트-컨테이너 간의 absolute path 불일치 문제가 완벽히 해결되었습니다.
* **회귀 가드**:
  1. `tests/test_raven_root.py`에 `test_registry_path_fallback_for_docker` 테스트를 신규 추가하여, 레지스트리에 존재하지 않는 경로가 설정되어 있어도 `WIKI_VAULTS_DIR` 하위의 폴더를 통해 올바르게 경로가 재해석되는지 검증하도록 했습니다.
  2. `tests/test_v0_7_12_docker.py`에 `test_compose_uses_vaults_as_wiki_vaults_dir` 테스트를 신규 추가하여, docker-compose 내 환경변수 `WIKI_VAULTS_DIR`가 `/vaults`로 잘 선언되어 있는지 정적으로 검증하도록 했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| pytest | **473 passed, 1 skipped** | 전체 테스트 성공 (신규 테스트 2개 포함) ✅ |

---

## 3. 다음 단계
* **v0.7.24 (후보)**: Dashboard 첫 실행 wizard (vault create 자동 안내)
