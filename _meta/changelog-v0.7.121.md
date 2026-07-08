---
title: Changelog v0.7.121
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.121 — 대시보드 내 물리 파일 경로 및 볼트 경로 하드코딩 표시 버그 수정

## 무엇을 했는가

- 다른 PC에서 볼트를 가져왔을 때, 이전 PC의 하드코딩된 절대 경로가 웹 대시보드의 볼트 목록 및 파일 상세의 '물리 파일 경로'에 계속해서 노출되던 버그를 수정했다.

### Root cause

1. **볼트 목록 (`/api/vaults`)**:
   - `.registry.json`에 원래 저장되어 있던 absolute path(`display_path`)가 로컬 머신에 실제 존재하지 않음에도 불구하고, 대시보드는 이를 그대로 렌더링에 사용했다.
   - 비록 백엔드(`VaultMeta.from_json`)에서 존재하지 않는 경로를 감지하고 `fallback_path`로 복구하여 `v.path`로 제공했지만, 대시보드 API 응답값을 조립할 때 `.registry.json`에 적힌 예전 절대 경로를 우선적으로 썼던 것.
2. **파일 상세 (`/api/vaults/{name}/pages/{slug}`)**:
   - Docker 컨테이너 환경을 위해 `RAVEN_VAULTS_DIR` 환경 변수를 사용해 컨테이너 내부 경로를 호스트의 물리 경로로 변환하는 치환 로직이 동작하고 있었다.
   - 하지만 로컬(호스트) 환경에서 직접 API 서버를 띄울 때도 `.env`에 잘못 기재된 타인의 절대 경로가 `RAVEN_VAULTS_DIR`로 주입되어 오작동했다. 그 결과, 실제 파일 경로 대신 엉뚱한 타인의 홈디렉토리 경로로 강제 치환되어 출력되는 문제가 발생했다.

## 변경

| 파일 | 변경 |
|---|---|
| `raven/api/server.py` | `list_vaults`에서 로컬 실행 시 `.registry.json`에 정의된 `display_path`가 로컬에 존재하지 않고 `v.path`가 존재한다면 `v.path`를 `display_path`로 쓰도록 복구 보완 |
| `raven/api/server.py` | `get_page`에서 `RAVEN_VAULTS_DIR` 치환 시, Docker 환경이거나 또는 로컬 환경이면서 `host_path`가 실제로 로컬에 존재할 때만 치환을 적용하도록 안전망 추가 |
| `tests/test_api.py` | 테스트 상황에서도 호스트 매핑이 올바르게 동작하도록 테스트용 가상 호스트 디렉토리를 실제 `mkdir` 하도록 개선 |

## 왜 그렇게 했는가 (§5 4 신호)

- **실패/리스크 기록**: 다른 PC로 볼트 이사 시 `display_path` 및 `file_path`가 이전 머신의 홈디렉토리명으로 하드코딩되어 고착되는 문제를 해결함.
- **재사용 가능성**: 로컬 실행 vs Docker 컨테이너 실행에 따라 환경 변수 `RAVEN_VAULTS_DIR`을 사용하는 치환 로직의 유효성을 정밀하게 분기(Docker에서는 무조건 치환, 로컬에서는 존재할 때만 치환).

## 검증

- `pytest tests/test_api.py` → 53 passed
- `scripts/.venv/bin/python -m pytest tests/test_api.py` 실행 완료.

## 후속

- `.env.example`에 기재된 `RAVEN_VAULTS_DIR` 예시의 default 처리를 쉘 스크립트 외에 로컬 구동 시에도 지능적으로 교정할 필요가 있는지 검토.
