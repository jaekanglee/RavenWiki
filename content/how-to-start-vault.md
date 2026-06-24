---
title: 새 vault 시작하는 법 (사용자 가이드)
created: 2026-06-25
updated: 2026-06-25
type: journal
tags: [journal, wiki, onboarding]
sources: [SCHEMA.md, RULES.md, content/_template.md]
confidence: high
---

# 새 vault 시작하는 법 (사용자 가이드)

> 처음 우리 시스템 vault를 시작할 때 따라하는 단계별 가이드.
> [[content/_template]] (프로젝트 시작)와는 다름 — vault **전체** 시작.

## 왜 이 페이지가 필요한가

[[content/llm-wiki]] 패턴을 직접实践하고 싶지만 시작점이 막막한 사용자/미래의 나를 위해.

**대상**:
- 본 vault를 처음 보는 사람
- 다른 vault에서 마이그레이션하는 사람
- 새 환경(macOS/Linux)에서 다시 시작하는 사람

## 0단계: 사전 준비

```bash
# Python 3.11+
python3 --version

# git
git --version

# uv (Python 패키지 매니저)
uv --version
```

없으면:
- macOS: `brew install python git uv`
- Ubuntu: `sudo apt install python3 git; curl -LsSf https://astral.sh/uv/install.sh | sh`

## 1단계: vault 디렉토리 생성 + git

```bash
mkdir ~/wiki && cd ~/wiki
git init
```

**`.gitignore`**:
```
wiki.db
wiki.db.backup
.venv/
__pycache__/
*.pyc
```

## 2단계: 운영 문서 작성

### `SCHEMA.md` (vault 규약)
- [[SCHEMA]] 본문 복사 → frontmatter/title 조정
- type: rule, tags: [schema, system]

### `RULES.md` (운영 정책)
- 우리 [[RULES]] 본문 참고
- type: rule, tags: [rule, system]

### `log.md` (append-only 액션 로그)
```markdown
# Wiki Log

## 2026-06-25

- 04:00 — vault init
- 04:10 — SCHEMA/RULES 작성
```

### `index.md` (콘텐츠 카탈로그)
```markdown
# Wiki Index

(자동 갱신됨 — wiki-curator가 빌드 시 갱신)
```

## 3단계: scripts/ 디렉토리 (빌드 + lint)

**`scripts/build_db.py`**:
- 우리 [[scripts/build_db]] 본문 복사
- (sqlite3 + python-frontmatter 필요)

**`scripts/lint.py`**:
- 우리 [[scripts/lint]] 본문 복사

**Python 의존성**:
```bash
cd ~/wiki/scripts
uv venv .venv
source .venv/bin/activate
uv pip install python-frontmatter pytest
```

## 4단계: raw/ 디렉토리 (불변 1차 자료)

```bash
mkdir raw/articles
```

→ ingest할 article을 `raw/articles/`에 저장:
- frontmatter에 `source_url`, `ingested`, `sha256`
- 본문은 원본 그대로 (검증 가능성)

## 5단계: content/ 디렉토리 (콘텐츠)

```bash
mkdir content
```

→ [[content/llm-wiki]] + [[content/_template]] 본문 참고.

**첫 페이지 5개 정도**:
- `content/concept/your-domain.md` — type: concept
- `content/tool/your-tools.md` — type: tool
- `content/comparison/x-vs-y.md` — type: comparison
- `content/projects/<name>/_overview.md` — type: project
- `content/queries/<first-question>.md` — type: query

## 6단계: 빌드 + lint 검증

```bash
cd ~/wiki
python3 scripts/build_db.py
# ✅ wiki.db (X KB): 5 pages, N links, M tags

python3 scripts/lint.py
# 📊 0 critical, 0 warning, 0 info, 0 total (모두 통과 시)
```

## 7단계: 첫 commit

```bash
cd ~/wiki
git add SCHEMA.md RULES.md log.md index.md .gitignore scripts/ raw/ content/
git commit -m "feat: vault init with schema + first 5 pages"
```

## 8단계: 4 wiki 프로필 설정 (선택)

Hermes Agent 사용 시:

```bash
mkdir -p ~/.hermes/profiles/{wiki-architect,wiki-curator,wiki-writer,wiki-dashboard}
```

각 프로필에:
- `config.yaml` (model + tools)
- `skills/` (절차 메모리)
- `memories/` (프로젝트 컨텍스트)

→ 위임 시 `wiki-writer` 프로필로 콘텐츠 작업 분리.

## 9단계: VPS + Tailscale (M4, 선택)

[[_meta/system-design]] §2.4 따라:
- Hetzner CAX11 (~$5/월) Ubuntu 24.04
- Tailscale 설치 + MagicDNS
- systemd service (wiki-mcp, wiki-dashboard)
- git webhook → git pull → systemctl restart

## 흔한 실수

### ❌ Obsidian 의존
- "Karpathy 패턴 = Obsidian"이 아님 ([[content/llm-wiki]])
- 우리는 자체 dashboard ([[content/react-spa-architecture]])

### ❌ wiki.db를 git에 커밋
- 빌드 산출물 ([[SCHEMA]] §빌드 원칙)
- `.gitignore`에 반드시 추가

### ❌ frontmatter 생략
- 모든 content/ 페이지 필수
- lint가 critical로 표시

### ❌ [[wikilink]] 잘못된 형태
- `[[link]]!` (broken) — 절대 ❌
- `[[link]]?` (placeholder) — 의도적만
- `[[link]]` (auto) — 대부분

### ❌ 200줄+ 단일 페이지
- 분리 대상 ([[SCHEMA]] §분리/아카이브)
- lint warning → 분리 권장

### ❌ Cognitive Governance 무시
- "정확하지만 죽은 페이지" ([[content/beyond-karpathy-llm-wiki]])
- 모든 페이지 "왜 중요한가" 섹션 + 한계

## 성공 지표

| 지표 | 목표 |
|---|---|
| 페이지 수 | ≥ 100 (90일) |
| 평균 outbound wikilinks | ≥ 2.0 |
| lint critical | 0 |
| dashboard 사용 | 1일 1회+ |
| DR 훈련 | 분기 1회 통과 |
| 비용 | ≤ $10/월 |

→ [[_meta/system-design]] §7.

## 다음 단계

| 단계 | 시점 | 문서 |
|---|---|---|
| M1 Data Layer | W1-W2 | (이미 작성된 [[SCHEMA]]) |
| M2 MCP | W3-W6 | [[content/mcp-server]] |
| M3 Dashboard | W7-W12 | [[content/react-spa-architecture]] |
| M4 Hosting | W13-W16 | [[content/tailscale-mesh]] |
| M5 Backup/DR | W17-W20 | (W5에서 `_meta/dr-runbook` 예정) |

## 일기 (메타)

- 작성일: 2026-06-25 (M1 W4 작업 중)
- 동기: 위키 시스템 onboarding을 한 곳에 정리
- 다음 갱신: M3 dashboard 완성 후 스크린샷 추가

## 관련

- [[content/llm-wiki]] — 우리 패턴
- [[content/_template]] — 새 프로젝트 시작
- [[content/harumoa-overview]] — 첫 샘플 프로젝트
- [[SCHEMA]] — vault 규약
- [[RULES]] — 운영 정책
- [[_meta/system-design]] — 시스템 전체 설계
- [[scripts/build_db]] — 빌드 도구
- [[scripts/lint]] — lint 도구
