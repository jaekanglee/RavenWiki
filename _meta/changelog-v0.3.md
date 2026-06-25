---
title: changelog-v0.3 (progressive delivery)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, changelog, raven, v0.3]
sources: [_meta/plan-v0.3-crud.md, _meta/decisions-d7-d9-multivault.md]
confidence: high
---

# changelog-v0.3 (progressive delivery)

> 2026-06-25. v0.3.0 = CLI 강화. v0.3.1 = API, v0.3.2 = Agent (progressive).

## v0.3.0 (이번 릴리스)

### 추가
- `raven.core.slug` — slug 검증 (`..`, `~`, 절대경로, NUL, `:` 거부) + vault root 내 확인
- `raven.core.frontmatter` — FM parse/render/merge 단일화 (`created` 보존, `updated` 강제 today)
- `raven.core.templates.{SCHEMA,RULES}.md` — 신규 vault 부트스트랩용 슬림 템플릿
- `Vault.create(..., bootstrap=True)` — 신규 vault에 content/ + _meta/{SCHEMA,RULES} 자동 복사
- `Vault.sync_meta()` — _meta/SCHEMA.md, RULES.md 재동기화 (덮어쓰기)
- CLI sub-app `raven meta sync` — vault 메타 문서 갱신
- 4 신규 테스트 파일 (66 케이스 pass)

### 변경
- `raven page new <slug>` — slug에 `/` 없으면 자동 `content/` prefix (R3)
- `raven page new` — frontmatter 생성이 `frontmatter.render()` 단일화 사용 (R2)
- `raven page delete` — archive 경로 mirror (nested 구조 보존, S1 흡수)
- `raven page new/delete` — slug 검증 (B4 MED 가드)
- `raven vault create` — `--no-bootstrap` 옵션 추가 (기본은 on)

### 호환성
- 기존 vault (`~/vaults/{default,second-vault}`) — 영향 없음 (부트스트랩은 신규만)
- 기존 `raven page new content/foo` — 동작 그대로
- 기존 `raven vault list/use/info/register/remove` — 변경 없음
- API 12 endpoints, Agent 어댑터 — **이번 릴리스 범위 외** (v0.3.1/3.2)

## v0.3.1 (이번 릴리스)

### 변경
- API 12 endpoints 중 write 5개에 R1 (slug 검증) + R2 (FM 단일화) 적용:
  - `POST /api/vaults/create` — `bootstrap` 옵션 추가 (기본 true)
  - `POST /api/vaults/{name}/pages` — slug validate + auto-prefix + fm 단일화
  - `PUT /api/vaults/{name}/pages/{slug}` — slug validate + **`created` 보존** (이제 Agent/CLI와 동일 정책)
  - `DELETE /api/vaults/{name}/pages/{slug}` — slug validate + archive mirror (nested 구조 보존)
- `_safe_slug_or_400()` helper 추가 — invalid slug → HTTP 400 (이전엔 500 가능했음)

### 호환성
- 기존 API 클라이언트 (dashboard) — 시그니처 무변경, payload 그대로 호환
- read endpoints (`GET /vaults`, `/pages`, `/search`, `/link-check`, `/build`, `/export`) — 무변경

### 테스트
- `tests/test_api.py`: 15 신규 케이스 (vault 3 + page CRUD 10 + read 회귀 2)
- 합계 **81 passed** (slug 20 + frontmatter 22 + vault_create 8 + cli 16 + api 15)

## v0.3.2 (이번 릴리스)

### 변경
- `raven.agents.AgentVault.write` — 자체 `_render`/`_split_frontmatter` 제거 → `frontmatter_module` 사용
  - `created` 보존 (이제 CLI/API와 동일 정책)
  - `tags` 강제 list (tuple 입력도 정확히 변환)
  - agents provenance는 render 단계에서 항상 append
- `write`/`delete`에 `slug_module.validate()` 적용 (CLI/API와 동일 가드)
- `_safe_path()` helper 추가 — invalid slug → `Result(ok=False, error="invalid slug: ...")`
- `delete` archive 경로 mirror (CLI/API와 동일 — nested 구조 보존)

### 호환성
- `AgentScope` 시그니처 무변경
- `Result` shape 무변경 (`ok/slug/path/bytes_written/message/error`)
- 기존 `_render`/`_split_frontmatter` 메서드는 thin wrapper로 유지 (back-compat)

### 버그 수정
- `frontmatter._coerce_tags`: tuple 입력 시 str로 변환되던 결함 → list로 정확히 변환
- `Agent.write`의 `if "/" not in slug` 검사 → slug safety로 대체 (잘못된 slug 메시지 명확화)

### 테스트
- `tests/test_agent.py`: 11 신규 케이스 (write 6 + delete 3 + list/search 2)
- `tests/test_frontmatter.py` +2 (tuple/list 케이스)
- 합계 **94 passed** (slug 20 + frontmatter 24 + vault_create 8 + cli 16 + api 15 + agent 11)

## v0.4 (예정)

- B8 (vault clone/import), B9 (archive cleanup), B10 (stale 가드)
- `.vault.json` path 환경변수 rename (B6)
- cross-vault wikilink (`[[vault:slug]]`)
- 백업 cron
