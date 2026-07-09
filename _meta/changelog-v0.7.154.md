---
title: Changelog v0.7.154
created: 2026-07-09
updated: 2026-07-09
type: rule
tags: database, schema, backend, test
---

# v0.7.154 — Phase 1: Semantic Relation Infrastructure (Vocabulary & DB Schema)

## BLUF
`docs/superpowers/plans/semantic-relation-inference-plan.md`의 Phase 1 계획에 따라, 5대 핵심 의미 관계(`uses`, `depends_on`, `implements`, `implemented_by`, `related`)를 정의하는 Vocabulary 인프라를 구축하고, SQLite `wiki.db`에 `relations` 테이블을 신설하여 Frontmatter에서 관계성 데이터를 추출 및 인덱싱하도록 파이프라인을 확장했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| 5대 핵심 관계 Vocabulary 정의 파일 생성 | `_meta/vocabularies/{uses, depends_on, implements, implemented_by, related}.yaml` | 에이전트와 시스템이 인식할 수 있는 강타입 의미론적 관계 사전 구축 |
| SQLite Schema에 `relations` 테이블 및 인덱스 추가 | `db.py`, `build_db.py` | 1급 데이터인 `relations` 및 다차원 신뢰도, 근거(evidence)를 영구 저장할 스키마 확보 |
| fallback 인덱서 갱신 | `db.py` | fallback 빌드 시에도 frontmatter `relations` 데이터를 추출하여 테이블에 적재 |
| canonical 인덱서 갱신 | `build_db.py` | `build_db.py` 실행 시 frontmatter의 `relations` 파싱, target_slug normalize 및 SQLite 저장 지원 |
| relations 인덱싱 및 정규화 유닛 테스트 추가 | `tests/test_db_build_relations.py` | 신규 기능이 오동작하거나 회귀(Regression)하지 않도록 자동 검증 코드 배치 |
| Wiki 스키마 규약 문서 업데이트 | `_meta/SCHEMA.md`, `templates/agent/SCHEMA.md` | frontmatter `relations` 필드의 공식 템플릿 규약 명문화 |

## 왜 했는가 (4 저장 신호)

- **재사용 가능성**: 향후 RAG 및 Graph Analytics(PageRank 등) 엔진이 `relations` 테이블의 강타입 관계를 활용하여 지식 그래프 추론 및 시각화를 수행할 수 있도록 공통 데이터 인터페이스 확보.
- **인수인계**: `_meta/vocabularies`로 Vocabulary 정의를 분리하여, 후속 에이전트와 큐레이터가 이 사전을 읽고 관계를 자율 학습할 수 있도록 함.
- **scope/provenance 추적 필요성**: 관계 맺음의 신뢰성을 보장하기 위해 `relations` 스키마에 다차원 confidence와 verified_by, evidence(근거), reason(이유)을 1급 컬럼으로 명시.

## 검증

- **테스트 코드 검증**: `make test-one F=tests/test_db_build_relations.py` 실행 → 1 passed (0.52s) ✅
- **회귀 테스트 검증**: `make test` 실행 → 737 passed (35.53s) ✅
- **정적 타입 및 빌드 검증**: `raven build` 및 `python scripts/build_db.py` 정상 구동 확인.

## 연관

- [[semantic-relation-inference-plan]] — Semantic Relation Inference Engine Plan (v3)
- [[SCHEMA]] — Wiki Schema (v0.7.x)
