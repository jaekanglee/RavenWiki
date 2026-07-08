---
title: Changelog v0.7.129
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.129 — GraphCanvas initialization runtime crash fix

## BLUF
React Flow가 완전히 초기화되기 전에 `flowToScreenPosition`이 호출되어 `TypeError`로 그래프 탭이 크래시(공백 화면)되는 문제를 방어했다.

## 무엇을 했는가

| 파일 | 변경 | 효과 |
|---|---|---|
| `dashboard/src/components/GraphCanvas.tsx` | `safeFlowToScreenPosition` 추가 | `flowToScreenPosition` 호출 시 발생하는 예외(try-catch) 차단 |
| `dashboard/src/components/GraphCanvas.tsx` | `vaultScreenFromCentroids` 등의 좌표 매핑 수정 | 초기화 완료 전 safe wrapper 적용 및 fallback 리턴 처리 |
| `tests/test_tier_boundary.py` | whitelist에 `CURATION.md` 추가 | v0.7.128 추가분에 대한 boundary test 정합성 확보 |
| `tests/test_mcp_check_freshness.py` | `exist_ok=True` 옵션 추가 | 테스트 중복 실행 시 `FileExistsError` 방지 |
| `raven/core/log.py` | lock 블록 종료 후 `rotate` 실행하도록 변경 | log append 도중 자동 rotate 시의 lock 데드락 수정 |
| `tests/test_lint_log_size.py` | 테스트 실행 중 `_LOG_ROTATE_THRESHOLD` mock 처리 | append 시 자동 rotate가 도는 부작용을 막아 임계값 lint 검출 정상 테스트 |

## 왜 했는가
- **실패 방지**: dense graph 또는 대형 all-vault 모드 진입 시, 첫 렌더링에 react flow initialization 완료 전 좌표 계산 실행으로 인한 런타임 크래시 차단.
- **재사용 가능성**: 향후 Graph 캔버스 좌표 변환 작업의 안정성 확보.
- **테스트 안정성**: 백엔드 테스트 스위트의 deadlock 및 flaky 원인(중복 디렉토리 생성 등)을 차단하여 CI/CD 회귀 방어력을 복구함.

## 검증
- `cd dashboard && npm run build` ✅
- `cd dashboard && npx vitest run tests/GraphCanvas tests/GraphPage` → **29 passed** ✅
- `make test` (pytest tests/ -q) → **730 passed** ✅
