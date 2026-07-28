---
created: 2026-06-24
sources: []
tags:
- system
- rule
- meta
title: Cross-cutting Rules
type: rule
updated: '2026-06-25'
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
- ❌ 개인 경로(기기 사용자명 포함), 고정 IP, API 키 등 환경 의존적/개인 데이터 하드코딩 금지

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

## 8. 파일명, 타이틀 및 본문 가독성 규칙 (v2.5)

- **1:1 대응 원칙**: 마크다운 파일명(Slug)과 Frontmatter의 `title`은 반드시 1:1 대응되어야 합니다.
  - 물리 파일명(확장자 제외)은 문서 타이틀을 그대로 슬러그화(Slugify)한 형태여야 합니다: 공백 및 특수문자는 하이픈(`-`)으로 치환하고, 영문은 소문자화합니다.
  - **언어 보존 (필수)**: `title`의 언어를 파일명에서 임의로 번역하거나 로마자로 음차하지 않습니다. 한글 `title` → 한글 파일명, 영문 `title` → 영문 파일명.
    - 예: `title: Vault Git Sync Setup` $\rightarrow$ 파일명: `vault-git-sync-setup.md`
    - 예: `title: 볼트 깃 동기화 설정` $\rightarrow$ 파일명: `볼트-깃-동기화-설정.md` (❌ `vault-git-sync-setup.md`로 번역 금지)
  - 타이틀의 의미와 무관하게 지어진 임의의 파일명이나 기계적인 이름(예: `note-1234.md` 등) 지정을 금지합니다.
- **직관적인 요약형 타이틀**: 에이전트가 문서를 자동 생성/요약할 때는 본문의 내용을 대표하여 사람이 한눈에 무슨 역할을 하는 파일인지 직관적으로 이해할 수 있는 명료한 요약형 타이틀을 부여해야 합니다.
- **본문 내용의 인간 중심 서술 및 요약 강제**:
  - 본문 서술 시 기계적인 태스크 번호(`P0-3`, `minor-2` 등)나 단순 빌드 코드에 의존하지 않고, 변경 사유와 구체적인 기능 중심으로 명확한 비즈니스/기술 용어를 사용해야 합니다.
  - 저널(`journal`)이나 일지 형식의 문서는 반드시 최상단에 `# 요약` 섹션을 명시하고 3줄 이내의 명확한 사람 대상 요약문을 작성해야 합니다.

## 9. 개발 및 환경 지침 (v2.6)

- **크로스 플랫폼 및 원격 환경 지향**: Raven은 기본적으로 macOS 및 Linux 환경에서 널리 설치 및 활용되며, Tailscale VPN 망을 통해 다중 호스트 간의 원격 연동이 이루어지는 것을 기본 시나리오로 가정합니다.
- **하드코딩 금지**: 소스코드, 빌드 스크립트, 설정 파일 등에 특정 기기의 개인 경로(예: `/Users/jaekanglee/...`와 같은 특정 사용자명이 들어간 절대 경로), 고정 IP, 개인 인증 키/API 토큰 등을 절대 하드코딩해서는 안 됩니다.
- **동적 파싱 및 환경 변수 우선**: 사용자마다 환경이 다를 수 있으므로 상대 경로 및 환경 변수(`WIKI_VAULTS_DIR`, `WIKI_VAULT` 등)를 적극 도입하고, 동적 정보 조회를 통해 런타임에 분기하도록 설계해야 합니다.

## 관련

- [[SCHEMA]] — 데이터 형식
- [[content/llm-wiki]]
- [[content/beyond-karpathy-llm-wiki]]
- [[_meta/system-design]]
