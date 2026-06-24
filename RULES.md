---
title: Cross-cutting Rules
created: 2026-06-24
updated: 2026-06-24
type: rule
tags: [system, rule, meta]
sources: []
---

# RULES.md — Cross-cutting Rules

> SCHEMA는 데이터 형식, RULES는 운영 정책.

## 1. Commit 규약

```
<type>(<scope>): <subject>

<body>
```

### Type

- `feat`: 새 페이지/기능
- `update`: 기존 페이지 갱신
- `fix`: 오타/링크 수정
- `chore`: 메타/문서
- `ingest`: 새 raw 소스
- `lint`: lint pass

### 예시

- `feat(content): add mcp-server.md`
- `update(architect): strengthen governance rules`
- `ingest(raw): karpathy LLM Wiki gist`

## 2. Ingest 절차 (wiki-writer)

1. raw에 저장 (sha256 frontmatter)
2. discussion with user (핵심 3가지)
3. 페이지 결정 (2+ 출처 or 중심 = 생성)
4. outbound `[[wikilinks]]` ≥ 2 (concept/person/tool 한정)
5. wikilink intent: `[[link]]` 자동, `[[link]]!` 명시 broken, `[[link]]?` 명시 placeholder
6. frontmatter 검증
7. `python3 scripts/build_db.py` 실행
8. `log.md` append
9. `git add` + commit
10. (선택) `git push`

## 3. Lint (wiki-curator, 주 1회)

```bash
cd ~/wiki/scripts && python3 lint.py
```

결과 처리:

- 🔴 critical → 즉시 fix
- 🟡 warning → backlog
- 🔵 info → 기록만

## 4. 금지 사항 (Hard Rules)

- ❌ raw 파일 수정 (불변)
- ❌ vault 외부에서 vault 수정
- ❌ `[[wikilinks]]` 없는 concept/person/tool 페이지
- ❌ `confidence: high` 단일 출처 페이지
- ❌ 200줄 초과 push (분리 필요)
- ❌ wiki.db git commit (gitignore)

## 5. 다중 프로젝트

- 새 프로젝트 시작: `content/<name>-overview.md` (type: project)
- vault-wide 규약 상속
- project-specific rule은 본문 안 section으로 (별도 RULES ❌)
- v2.2: `content/<name>/<page>.md` 구조 가능 (slug = `<name>/<page>`)

## 6. 백업 (M5 자동화, M1 수동)

- **git push = 진짜 백업** (markdown이 SoT)
- `wiki.db.backup` = `backup_db.py` 일 1회 (DB만 복구 가능)
- **v2.4**: `git push` 실패 감지 (RULES 우선순위)
  - webhook 실패 시 Telegram 알림
  - push 실패 → wiki.db.backup 즉시 확인 + 수동 push
- 로컬 Time Machine = OS 의존

## 7. Slug Rename (v2.3)

```bash
# 1. 파일 이동
git mv content/docker-deploy.md content/deployment/docker.md

# 2. frontmatter 갱신
# ---
# slug: deployment/docker
# aliases: [docker-deploy]
# ---

# 3. 자동 리라이트 (M2 구현 예정)
python3 scripts/rename_slug.py --from docker-deploy --to deployment/docker
```

## 관련

- [[SCHEMA]] — 데이터 형식
- [[content/llm-wiki]]
- [[content/beyond-karpathy-llm-wiki]]
- [[_meta/system-design]]
