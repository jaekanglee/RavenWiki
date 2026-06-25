---
title: Raven System Operations — build / lint / migrate 운영
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, operations, build, lint, migrate, raven]
audience: system
confidence: high
---

# Raven System Operations — build / lint / migrate

> **raven 시스템 자체의 운영 매뉴얼.** lint/build 코드 + 사람 운영자 모두 참조.
> agent 행동 지침은 `_meta/agent/*` 참조 (혼용 ❌).

---

## 1. 빌드 파이프라인

```
[markdown files]            ← SoT (git)
       ↓
[raven build]               ← wiki.db 재생성
       ↓
[SQLite wiki.db]            ← Query Index (gitignore)
       ↓
[raven lint run]            ← 12개 규칙 자동 검증
       ↓
[_meta/log.md]               ← build/lint 결과 자동 append
```

### 1.1 build (wiki.db 재생성)

```bash
raven build
# 또는 scripts/build_db.py 직접 호출
```

- 모든 `.md` 파일을 재파싱해서 `wiki.db` 재생성
- FTS5 전문검색 인덱스 + backlinks view 포함
- **atomic 보장**: temp DB 생성 → `os.replace`로 swap (P1 패치 예정)
- 실패 시 기존 `wiki.db` 보존 (atomic 보장 후)

### 1.2 lint (12개 규칙)

| # | 규칙 | severity | 의미 |
|---|---|---|---|
| 1 | frontmatter 필수 | 🔴 | R1 — 모든 페이지 frontmatter 5필드 |
| 2 | slug 형식 | 🔴 | R2 — `~` `/` `..` 금지 |
| 3 | type 8개 taxonomy | 🟡 | R3 — SCHEMA 명시 8개만 |
| 4 | tag core 분류 | 🟡 | R4 — core/custom 분리 |
| 5 | contradictions | 🟡 | frontmatter.contradictions 미존재 경고 |
| 6-12 | ... | ... | (`raven lint run` 출력 참조) |

---

## 2. vault 디렉토리 구조 (시스템 측)

```
<vault>/
├── .vault.json              # vault 메타 (name, mode, owner)
├── _meta/
│   ├── log.md               # 작업 이력 (자동 append, system+agent 공용)
│   ├── collections.yaml     # 분류 정의 (system 전용)
│   ├── system/              # ⭐ 시스템 자체 지침 (사람+코드)
│   │   ├── SCHEMA.md        # vault 구조, SoT, frontmatter 규약
│   │   ├── RULES.md         # 편집 5규칙
│   │   └── OPERATIONS.md    # 이 문서
│   └── agent/               # ⭐ 에이전트 행동 지침 (LLM only)
│       ├── README.md        # 진입점
│       ├── TOOLS.md         # 인터페이스 + scope
│       ├── WORKFLOW.md      # 트리거 / Phase 게이트
│       └── SAFETY.md        # 절대 금지
├── content/                 # ⭐ 사용자 컨텐츠
│   ├── _system/             # raven 시스템 reference (10페이지)
│   ├── <team>/              # 프로젝트별 (harumoa/homeauto/...)
│   └── journal/             # 일지
├── _archive/                # retired 페이지
└── wiki.db                  # SQLite Query Index (gitignore)
```

### 2.1 `system/` vs `agent/` 분리 — 불변 원칙

- **system/** = 시스템 자체 (lint/build 코드 + 사람 운영자)
  - 변경 = 사용자 컨펌 필수
  - lint가 자동 참조
- **agent/** = LLM 에이전트 행동 지침
  - 변경 = 사용자 컨펌 필수 (별도)
  - 에이전트가 read (자동 로드 옵션)

**혼용 ❌**: 한 파일에 "시스템 동작" + "에이전트 행동" 섹션 혼재 금지.

→ 분리 결정 문서: `content/journal/2026-06-25-raven-guidelines-split-decision.md`

---

## 3. CLI 명령어 (9개)

| 명령 | 용도 |
|---|---|
| `raven vault list/create/clone` | vault 관리 |
| `raven page new/get/ls/update/delete` | 페이지 CRUD |
| `raven build` | wiki.db 재빌드 |
| `raven lint run` | 12개 lint 검증 |
| `raven log list/add` | 작업 이력 |

→ 4 인터페이스 (CLI / HTTP / Python / GUI) 모두 동일한 9개 명령어 대응.

---

## 4. 운영 시나리오

### 4.1 신규 vault 생성

```bash
raven vault create myvault /path/to/myvault --bootstrap
# → 빈 디렉토리 + _meta/{system,agent}/ 템플릿 + SCHEMA/RULES 자동 배치
```

### 4.2 일일 운영 (cron 후보)

```bash
# 1. lint 먼저 (실패 시 build 안 함)
raven lint run

# 2. wiki.db 재빌드
raven build

# 3. git commit (vault + log.md)
cd ~/vaults/<name>
git add -A && git commit -m "vault: daily sync"
```

### 4.3 백업 / 복구

```bash
# 백업 — git 추적이 1차 SoT
git push origin master

# 2차 — wiki.db 별도 백업 (scripts/backup_db.py)
python3 scripts/backup_db.py --vault <name> --out /backup/

# 복구 — wiki.db 손상 시
rm wiki.db && raven build    # markdown에서 재생성
```

---

## 5. 코드 측 모듈 (raven/)

| 모듈 | 책임 |
|---|---|
| `core/db.py` | wiki.db 빌드 + 스키마 |
| `core/vault.py` | vault lifecycle (create/load/clone) |
| `core/frontmatter.py` | parse/render/merge (단일 소스) |
| `core/slug.py` | slug validate (`_safe_path()` 핵심) |
| `core/lint.py` | 12개 lint 규칙 |
| `core/log.py` | log.md 자동 append |
| `core/archive.py` | _archive/ 관리 |
| `core/registry.py` | multi-vault registry |
| `cli/__main__.py` | 9 commands (typer) |
| `api/server.py` | FastAPI HTTP (:8765) |
| `agents/agent.py` | scope 기반 Agent |
| `curator/` | stateless curation (v0.8+) |

→ 모듈 경계: 위 표 그대로 — 책임 침범 시 lint/audit에서 발견됨.

---

## 6. 절대 안 되는 운영 (시스템 측)

| ❌ 안됨 | 이유 |
|---|---|
| `wiki.db` 수동 SQL 수정 | build로 재생성 |
| `_meta/log.md` 수동 편집 | 자동 append 깨짐 |
| vault 외부 read/write 시도 | SoT = vault 내부 |
| `_meta/system/*` 자동 변경 | 사용자 컨펌 필수 |
| 같은 vault를 여러 OS path에서 동시 접근 | SQLite lock 충돌 |

---

## 관련

- `_meta/system/SCHEMA.md` — frontmatter 규약
- `_meta/system/RULES.md` — 편집 5규칙
- `_meta/collections.yaml` — 분류 정의
- `_meta/log.md` — 작업 이력
