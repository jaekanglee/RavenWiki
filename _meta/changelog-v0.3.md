---
title: changelog-v0.3 (progressive delivery)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, changelog, wikisys, v0.3]
sources: [_meta/plan-v0.3-crud.md, _meta/decisions-d7-d9-multivault.md]
confidence: high
---

# changelog-v0.3 (progressive delivery)

> 2026-06-25. v0.3.0 = CLI 강화. v0.3.1 = API, v0.3.2 = Agent (progressive).

## v0.3.0 (이번 릴리스)

### 추가
- `wikisys.core.slug` — slug 검증 (`..`, `~`, 절대경로, NUL, `:` 거부) + vault root 내 확인
- `wikisys.core.frontmatter` — FM parse/render/merge 단일화 (`created` 보존, `updated` 강제 today)
- `wikisys.core.templates.{SCHEMA,RULES}.md` — 신규 vault 부트스트랩용 슬림 템플릿
- `Vault.create(..., bootstrap=True)` — 신규 vault에 content/ + _meta/{SCHEMA,RULES} 자동 복사
- `Vault.sync_meta()` — _meta/SCHEMA.md, RULES.md 재동기화 (덮어쓰기)
- CLI sub-app `wikisys meta sync` — vault 메타 문서 갱신
- 4 신규 테스트 파일 (66 케이스 pass)

### 변경
- `wikisys page new <slug>` — slug에 `/` 없으면 자동 `content/` prefix (R3)
- `wikisys page new` — frontmatter 생성이 `frontmatter.render()` 단일화 사용 (R2)
- `wikisys page delete` — archive 경로 mirror (nested 구조 보존, S1 흡수)
- `wikisys page new/delete` — slug 검증 (B4 MED 가드)
- `wikisys vault create` — `--no-bootstrap` 옵션 추가 (기본은 on)

### 호환성
- 기존 vault (`~/vaults/{default,second-vault}`) — 영향 없음 (부트스트랩은 신규만)
- 기존 `wikisys page new content/foo` — 동작 그대로
- 기존 `wikisys vault list/use/info/register/remove` — 변경 없음
- API 12 endpoints, Agent 어댑터 — **이번 릴리스 범위 외** (v0.3.1/3.2)

## v0.3.1 (예정)

- API 12 endpoints 모두 R1 (slug) + R2 (FM) 흡수
- import 변경 위주, LOC ~150

## v0.3.2 (예정)

- `wikisys.agents.Agent._render` / `_split_frontmatter` 제거 → `frontmatter_module` 사용
- LOC ~50

## v0.4 (예정)

- B8 (vault clone/import), B9 (archive cleanup), B10 (stale 가드)
- `.vault.json` path 환경변수 rename (B6)
- cross-vault wikilink (`[[vault:slug]]`)
- 백업 cron
