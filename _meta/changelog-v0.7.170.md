---
title: Changelog v0.7.170
created: 2026-07-13
updated: 2026-07-13
type: rule
tags: [dashboard, graph, api, performance, test]
---

# v0.7.170 — 그래프 응답 캐시

## BLUF
변경되지 않은 vault의 그래프 재진입에서 ForceAtlas와 Louvain 레이아웃을 재계산하지 않도록 API 응답 캐시를 추가했습니다.

## 변경

- `GET /api/vaults/{name}/graph` 응답을 vault 경로, iteration, community 옵션, `wiki.db`, Markdown, `.graph_positions.json`의 변경 fingerprint 기준으로 캐시합니다.
- Markdown 직접 수정, DB 갱신, 사용자 노드 위치 변경은 다음 조회에서 자동으로 새 그래프를 계산합니다.
- 프로세스 메모리 캐시는 최대 16개 상태로 제한합니다.
- 동일 입력의 레이아웃 재계산 방지와 Markdown 변경 후 무효화 회귀 테스트를 추가했습니다.

## 검증

- `scripts/.venv/bin/python -m pytest tests/test_api.py -q` → 59 passed
- `scripts/.venv/bin/python -m compileall -q raven/api/server.py`
- `cd dashboard && npx tsc -b --noEmit`
- 로컬 API 실측: `raven-dev` 0.372s → 0.016s, `harumoa` 1.239s → 0.017s (cold → warm)

## 이유

- **재사용성/운영 밀도**: 데이터가 바뀌지 않은 재진입마다 동일한 그래프 레이아웃을 계산할 필요가 없습니다.
- **리스크 감소**: 모든 Markdown과 그래프 입력의 변경을 fingerprint에 포함해 직접 편집 경로도 stale 응답을 반환하지 않습니다.
