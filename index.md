# Wiki Index

> 콘텐츠 카탈로그. 각 페이지는 한 줄 요약과 함께 타입별로 정렬.
> 마지막 업데이트: 2026-06-25 | 전체 페이지: 15 (content/) + 9 (_meta/)

## Concepts (content/)
- [[content/beyond-karpathy-llm-wiki]] — LLM Wiki 패턴의 한계 + Cognitive Governance 필요성
- [[content/llm-wiki]] — Karpathy의 LLM Wiki 원본 패턴 정리 (3-layer, ingest/query/lint)

## Comparisons (content/)
- [[content/rag-vs-llm-wiki]] — RAG와 LLM Wiki의 7가지 차원 비교

## Meta (vault 운영 문서)
- [[SCHEMA]] — vault 규약 v2.4 (frontmatter, type, tag core+custom, governance, MCP 권한, slug rename)
- [[RULES]] — cross-cutting 운영 정책 (commit/ingest/lint/금지/프로젝트/백업/slug rename)
- [[_meta/mvp-prd]] — 자체구축 위키 시스템 MVP PRD
- [[_meta/requirements]] — 사용자 요구사항 (니즈 6 / 제약 5) — system-design 분할
- [[_meta/architecture-5layer]] — 5-Layer 아키텍처 (Data/MCP/Dashboard/Hosting/Backup) — system-design 분할
- [[_meta/decisions-d1-d6]] — 결정사항 D1-D6 + 마일스톤 M0-M6 — system-design 분할
- [[_meta/dr-runbook]] — 재해 복구 Runbook (RPO 1h / RTO 30m, 4 시나리오)
- [[_meta/deployment]] — VPS + Tailscale 배포 절차 (docker-compose + Caddy + webhook)
- [[_meta/ai-roadmap]] — AI 활용 로드맵 (M3 vector search → M6 작성 도우미)
- [[_meta/wiki-persona]] — 사용자 페르소나 (Primary: Jake, Secondary: Riya)
- [[_meta/wiki-scenario]] — MVP 5개 시나리오
- [architecture.html](_meta/architecture.html) — 통합 아키텍처 다이어그램 (브라우저로 열기)

## Raw Sources (불변)
- [raw/articles/karpathy-llm-wiki-2026.md](raw/articles/karpathy-llm-wiki-2026.md) — Karpathy "LLM Wiki" gist (2026-04-04, 80 lines, sha256: 916af9d6...)

## 마이그레이션 메모

v1 → v2.4 변경:
- `concepts/`, `entities/`, `comparisons/` → **`content/` 단일** + `type:` frontmatter
- 빈 디렉토리는 `.gitkeep`으로 유지 (예: `concepts/`, `projects/`)
