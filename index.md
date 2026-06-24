# Wiki Index

> 콘텐츠 카탈로그. 각 페이지는 한 줄 요약과 함께 타입별로 정렬.
> 마지막 업데이트: 2026-06-24 | 전체 페이지: 3 (content/) + 7 (_meta/)

## Concepts (content/)
- [[content/beyond-karpathy-llm-wiki]] — LLM Wiki 패턴의 한계 + Cognitive Governance 필요성
- [[content/llm-wiki]] — Karpathy의 LLM Wiki 원본 패턴 정리 (3-layer, ingest/query/lint)

## Comparisons (content/)
- [[content/rag-vs-llm-wiki]] — RAG와 LLM Wiki의 7가지 차원 비교

## Meta (vault 운영 문서)
- [[SCHEMA]] — vault 규약 v2.4 (frontmatter, type, tag core+custom, governance, MCP 권한, slug rename)
- [[RULES]] — cross-cutting 운영 정책 (commit/ingest/lint/금지/프로젝트/백업/slug rename)
- [[_meta/mvp-prd]] — 자체구축 위키 시스템 MVP PRD
- [[_meta/system-design]] — 5-Layer 통합 아키텍처 + 요구사항 분석
- [[_meta/wiki-persona]] — 사용자 페르소나 (Primary: Jake, Secondary: Riya)
- [[_meta/wiki-scenario]] — MVP 5개 시나리오
- [architecture.html](_meta/architecture.html) — 통합 아키텍처 다이어그램 (브라우저로 열기)

## Raw Sources (불변)
- [raw/articles/karpathy-llm-wiki-2026.md](raw/articles/karpathy-llm-wiki-2026.md) — Karpathy "LLM Wiki" gist (2026-04-04, 80 lines, sha256: 916af9d6...)

## 마이그레이션 메모

v1 → v2.4 변경:
- `concepts/`, `entities/`, `comparisons/` → **`content/` 단일** + `type:` frontmatter
- 빈 디렉토리는 `.gitkeep`으로 유지 (예: `concepts/`, `projects/`)
