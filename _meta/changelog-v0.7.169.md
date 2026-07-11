---
title: Changelog v0.7.169
created: 2026-07-10
updated: 2026-07-10
type: rule
tags: [dashboard, cleanup, api, test]
---

# v0.7.169 — Dashboard Digest 제거

## BLUF
중복 요약과 근거 없는 자동 관계 생성을 유발하던 Daily Digest를 제거하고, Dashboard는 탐색·편집·검증·이력의 핵심 표면에 집중합니다.

## 변경

- Dashboard `/digest` 라우트와 홈 Quick Action을 제거했습니다.
- Digest UI와 전용 API(`GET /api/vaults/{name}/digest`), 집계 코어를 제거했습니다.
- 기존 Digest 테스트를 제거하고, 해당 UI·API·코어가 재도입되지 않는 회귀 가드를 추가했습니다.

## 검증

- `scripts/.venv/bin/python -m pytest tests/test_digest_removal.py tests/test_api.py -q`
- `cd dashboard && npx tsc -b --noEmit`
- FastAPI route 목록에서 Digest API 부재 확인

## 이유

- **재사용성/운영 밀도**: 활동·린트·최근 문서 요약은 기존 홈·로그·린트·가든 표면과 중복됐습니다.
- **리스크 감소**: 고립 문서 신호만으로 추천 문서와 의미 관계를 자동 추가하는 흐름을 제거했습니다.
