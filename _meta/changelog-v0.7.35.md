# raven v0.7.35 — 보관소 에이전트 가이드 명칭 변경 및 마이그레이션 실드 구축

> **핵심**: 사용자가 시스템 폴더(`_meta/system/`)에 진입했을 때 가이드라인을 가장 자연스럽고 명확하게 인지할 수 있도록 기존 `AGENTS.md` 파일의 명칭을 `README.md`로 변경했습니다. 이 리네임 변경 사항을 Raven 코어(templates, bootstrap, verify) 및 테스트 코드 전반에 걸쳐 교체 적용하고, 기존 보관소들의 매끄러운 이관을 위한 자동 마이그레이션 로직을 통합했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.34

---

## 1. 변경 사항

### 1-1. 시스템 폴더 사용자 가이드 명칭 변경 (README.md)
* **`raven/core/templates/system/README.md`**:
  * 템플릿 파일 명칭을 `AGENTS.md`에서 `README.md`로 리네임하고, `SCHEMA.md` 및 `PROJECT-WORKFLOW.md` 내에서 해당 가이드를 가리키던 파일 링크들을 `_meta/system/README.md`로 일제히 수정 및 갱신했습니다.
  * 보관소 생성/싱크 시 활용되는 복사 맵(`vault._bootstrap_lite`, `vault.sync_meta`)을 새 명칭에 맞추어 보완했습니다.

### 1-2. 기존 보관소 자동 마이그레이션 실드(Shield) 탑재
* **`raven/core/vault.py`**:
  * 사용자가 기존에 생성해 사용 중이던 구버전 보관소들의 호환성 유지를 위해, 보관소를 여는(load) 시점에 `_meta/system/AGENTS.md`가 존재하고 `README.md`가 없으면 자동으로 이름을 전환(rename)해 주는 자동 이관 실드 로직을 탑재했습니다.
  * 활성 보관소 리스트인 `raven-dev` 및 `harumoa` 볼트들에 수동 `meta sync --force`를 직접 구동하여 기존 구버전 파일들을 성공적으로 안전 정리하고 `README.md` 체계로 싱크 이관 완료했습니다.

### 1-3. 검증 및 테스트 코드 일괄 갱신
* **`raven/core/verify.py` & `raven/cli/__main__.py`**:
  * 5대 Lite bootstrap 무결성을 자가 테스트하는 verify(Bootstrap Self-Test) 코드 내 경로 단언과 헬프 설명 텍스트를 `README.md`에 맞춰 갱신했습니다.
* **`tests/` 하위 테스트들**:
  * `test_bootstrap_verify.py`, `test_cli.py`, `test_raven_root.py`, `test_tier_boundary.py`, `test_v0_7_1_lite_bootstrap_surface.py`, `test_vault_create.py` 등 verification 및 bootstrap 관련 테스트 내부에서 `AGENTS.md` 존재를 assertion하던 테스트 구문을 전부 `README.md`로 교체 완료했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **Success** | `npx tsc -b --noEmit` 타입 검증 완료 |
| backend pytest | **488 passed, 1 skipped** | 전체 API 및 Core 회귀 테스트 통과 확인 ✅ |
| harumoa/raven-dev sync | **Success** | 로컬 보관소 2종 모두 README.md 마이그레이션 완료 |

---

## 3. 다음 단계
* v0.7.36: 향후 대시보드와 코어 간의 리비전 완성도 유지보수 및 자율 테스트 패키지 유지.
