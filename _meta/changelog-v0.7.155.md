---
title: Changelog v0.7.155
created: 2026-07-09
updated: 2026-07-09
type: rule
tags: [database, schema, backend, test, migration, lint]
---

# v0.7.155 — Phase 2: Semantic Relation Migration Script & Semantic Lint Rule

## BLUF
Phase 1에서 정의된 Vocabulary 및 DB relations 스키마 인프라를 바탕으로, 기존 300여 개 문서의 단순 `[[wikilink]]`들을 문맥(context)에 맞춰 5대 핵심 의미 관계(`uses`, `depends_on`, `implements`, `implemented_by`, `related`)로 일괄 전환하는 마이그레이션 스크립트를 구축하고, relations frontmatter의 문법, 타입, 대상 존재 여부, 그리고 evidence/reason 필수 여부를 실시간 검사하는 Semantic Lint 룰 `#23`을 추가했습니다.

## 무엇을 했는가

| 변경 | 파일 | 효과 |
|---|---|---|
| Semantic Relation Lint 룰 (#23) 구현 | `raven/core/lint.py` | frontmatter의 `relations` 문법 및 타입 정합성, 대상 문서 존재 여부, evidence/reason 필수 기재를 자동 검사하는 규칙 추가 |
| wikilink 일괄 마이그레이션 스크립트 작성 | `scripts/migrate_relations.py` | active vault 내 모든 문서를 스캔하여 wikilink 주변 문맥에 맞는 의미 관계 추론 및 다차원 신뢰도, evidence/reason 기입 후 frontmatter 적재 기능 제공 (--apply/--dry-run 지원) |
| Semantic Lint 유닛 테스트 추가 | `tests/test_semantic_relations_lint.py` | `#23` 룰에 의해 허용되지 않는 관계 타입, 존재하지 않는 타겟, 누락된 evidence/reason 등이 정확하게 warning/critical로 적발되는지 자동 검증 |
| 마이그레이션 스크립트 유닛 테스트 추가 | `tests/test_migrate_relations.py` | wikilink 문맥으로부터 관계 타입을 추론하고, 기존 relations에 중복 없이 병합(merge)하는 로직을 자동 검증 |
| 전체 300여 개 문서에 대한 실제 마이그레이션 완료 | `hermes-infra` vault | 마이그레이션 스크립트를 사용하여 47개 파일에서 총 341개의 신규 semantic relation 관계 적재 완료 |

## 왜 했는가 (4 저장 신호)

- **재사용 가능성**: 단순 표현 계층의 `[[wikilink]]`를 semantic graph를 위한 1급 관계 정보로 자가 추출 및 변환하여, 향후 지식 탐색 및 시각화에 일관된 data model을 보장함.
- **인수인계**: 후속 에이전트나 사용자가 frontmatter의 `relations`를 바탕으로 문서의 영향도 및 도메인 상호 관계를 한 눈에 파악할 수 있도록 뼈대 구축.
- **scope/provenance 추적 필요성**: 스키마 원칙에 따라 모든 relation에 `evidence`와 `reason`을 포함시켜, 지식 추출의 유래와 맥락을 영구 추적 가능하게 함.

## 검증

- **테스트 코드 검증**: `make test-one F=tests/test_semantic_relations_lint.py` (Passed) ✅, `make test-one F=tests/test_migrate_relations.py` (Passed) ✅
- **회귀 테스트 검증**: `make test` 실행 → 741 passed (36.06s) ✅
- **정적 타입 및 빌드 검증**: `raven build` 및 `wiki.db` 재생성 후 relations indexing 성공 완료.

## 연관

- [[semantic-relation-inference-plan]] — Semantic Relation Inference Engine Plan (v3)
- [[SCHEMA]] — Wiki Schema (v0.7.x)
