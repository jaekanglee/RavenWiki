# Raven — local-first Zettelkasten-inspired markdown PKM

> **markdown SoT + 사람 1차 + 제텔카스텐식 연결 지식 + 에이전트 옵션 + multi-vault.** Obsidian 모티브 + 자유 구조 + 자체 Dashboard. LLM Wiki 패턴은 vault 안에서 +α로 선택적 도입.
>
> 옵시디언의 모티브를 빌려왔지만, **에이전트 옵션 + 프로그래머블 진입점 + LLM Wiki +α**가 차별점. Obsidian clone이 아님.

## North Star (v0.6.37 재정렬)

> **"Raven은 사람을 1차 사용자로 하는 local-first Zettelkasten-inspired markdown PKM이며, 원하는 vault 영역에만 LLM Wiki 패턴을 +α로 켜 AI 에이전트가 이해하고 재사용하기 좋은 compounding knowledge를 누적한다."**
>
> — **Zettelkasten 원칙 (작은 생각 단위 + 링크 + 누적) + Obsidian 모티브 (자유 vault) + Karpathy LLM Wiki (2026) 영감 + 자체 구현체.** 분업: 사람은 source curate + 방향 결정, **원하면** vault의 특정 영역에서 LLM Wiki 패턴(raw/, log.md, _meta/agents/)을 켜서 에이전트가 compile / cross-reference / lint / consistency를 도울 수 있음. **컴파일 후 reuse, 매번 재구성 ❌.**

---

## 무엇인가

raven는 **사람 1차 Zettelkasten-inspired 마크다운 PKM 도구**. Obsidian-style 자유 vault와 자체 Dashboard를 제공하고, Karpathy LLM Wiki (2026) 패턴을 영감으로 받아 vault 안에서 선택적 +α로 도입 가능하다. **local-first 마크다운 지식 vault**.

| 계층 | 구현 | 위치 |
|---|---|---|
| **Vault** (데이터) | 마크다운 폴더 (Obsidian식 자유 계층) | `~/Raven/<name>/` (v0.6.3+) |
| **Index** (쿼리) | SQLite (FTS5 + backlinks view) | `<vault>/wiki.db` |
| **Engine** (Python) | raven.core (db/lint/export/link) | `raven/core/` |
| **CLI** (사람/자동화) | Typer 9 commands | `raven/cli/` |
| **API** (HTTP) | FastAPI 26 endpoints | `raven/api/` |
| **GUI** (웹) | React 19 + Vite + PWA | `dashboard/` |
| **MCP** (LLM 표준) | FastMCP 9 tools + 5 resources | `raven/mcp/` |

**SoT = 마크다운**. DB/API/GUI/MCP는 **모두 재생성 가능**한 파생 산출물.

---

## 누가 쓰는가 (사용자 3종 — 정직한 표현)

| 사용자 | 상태 | 진입점 |
|---|---|---|
| **사람 (개발자 1인)** | ✅ 안정 — CLI/Dashboard/API | 직접 |
| **단일 에이전트** | ⚠️ MCP가 표준 (Python adapter는 사람/스크립트 보조) | MCP :8766 |
| **멀티 에이전트 (MCP 다중)** | ⚠️ **experimental** — 동시 쓰기 충돌 보호 없음 (locks/queue/review 미구현) | MCP |

> 멀티 에이전트 write는 **scope 명시 + 동시성은 사용자 책임**. "안정 지원"이라고 표현하지 않음.

---

## 왜 만들었나 (vs Obsidian)

| Obsidian | raven |
|---|---|
| vault = 사용자가 폴더 지정 ✅ | 동일 ✅ |
| GUI만 있음 | **CLI + HTTP API + Dashboard + MCP 4개 진입점** |
| 사람이 1차 사용자 | **사람 1차, 에이전트 옵션** (LLM Wiki +α로 켤 수 있음) |
| 플러그인 = UI 확장 | **에이전트 = vault 옵션 시민** (scope/provenance 강제는 opt-in) |
| 단일 앱 | **multi-vault, multi-user 가능 (단, ACL은 non-goal)** |

**대체하지 않는 범위** (정직):
- Obsidian의 모바일 UX, sync 서비스, 플러그인 생태계 → 비목표
- 단일 사용자 가정 (auth 없음, 127.0.0.1 기본 바인딩) → 명시
- 대규모 팀 (Notion/Confluence 영역) → Anti-persona

사용자 인용 (2026-06-25):
> "옵시디언 안 사고, 모티브만 빌려서 내가 직접 만들 거야"
> "안정적이고, 심플한걸로 기준. 도전적인건 지양"

→ Obsidian의 **사용성 + 안정성**을 닮되, **에이전트 협업 + 프로그래머블 진입점**을 1급 시민으로 추가.

---

## 빠른 시작 (이미 셋업된 로컬)

```bash
# 0. 환경
cd ~/Desktop/Dev/Project/Raven
source scripts/.venv/bin/activate   # venv

# 1. vault 확인
raven where                       # 현재 설정 + vault 목록

# 2. (선택) 새 vault 만들기
raven vault create personal ~/Raven/personal
raven vault use personal

# 3. 빌드 (DB + lint)
raven build

# 4. GUI 띄우기 (다른 터미널)
python -m raven.api               # → http://127.0.0.1:8765
cd dashboard && npm run dev         # → http://localhost:5173

# 5. CLI로 페이지 작업
raven page new content/hello --title "Hello" --type concept --tags "demo"
raven page ls
raven page get content/hello
raven link check
raven export                      # GUI 정적 JSON 재생성
```

### Lite bootstrap (v0.5.5+) — `raven vault create` 시 자동 복사

새 vault를 `--profile llm-wiki`로 만들면 다음 **5종**이 vault 폴더에 자동 복사됩니다:

| 파일 | 용도 |
|---|---|
| `_meta/system/SCHEMA.md` | frontmatter / type / tag / wikilink 규약 |
| `_meta/system/RULES.md` | 편집 5규칙 |
| `_meta/system/README.md` | vault 운영자 가이드 ("Vault User Guide", v0.7.35+ 리네임) |
| `_meta/agents/PROJECT-WORKFLOW.md` | 프로젝트 작업 에이전트 공통 워크플로우 |
| `log.md` | 작업 이력 (append-only) |

**Tier 1 문서** (`OPERATIONS.md` / `agent/*` / `raven-policy.md`)는 raven 패키지 내부에 있으며 vault에 **복사되지 않습니다**. 접근은 `raven docs show <topic>`. `vault clone` 기본 = content only (Tier 1 leak 방지).

---

## Docker 운영 (v0.7.36+: 이미지 SHA 핀)

Raven은 4 진입점(CLI/API/MCP/Dashboard) 모두 Docker로 띄울 수 있습니다. **코드 변경 후 반드시 이미지 재빌드 + 컨테이너 재기동** — stale 이미지 캐시가 옛 `_bootstrap_lite`(예: `_meta/system/AGENTS.md` 참조)를 들고 있으면 새로 만든 vault가 즉시 깨질 수 있습니다 (silent failure 사고 사례: v0.7.35 리네임 후 stale 이미지로 `Lite bootstrap failed` 발생).

```bash
# 0. 환경 (.env에 RAVEN_VAULTS_DIR, PORT_*, HOST 등 정의)
cd ~/Desktop/Dev/Project/Raven

# 1. 코드 변경 후 → 반드시 SHA 이미지로 재빌드
# ⚠️ IMPORTANT: 3개 서비스가 같은 image: raven:${GIT_SHA} 태그를 공유하므로
#    반드시 **서비스를 explicit 나열**해 sequential build 해야 합니다.
#    `docker compose build`(서비스 인자 없음) 는 병렬 빌드 → 3개 레이어가
#    같은 태그를 동시에 export 시도 → "image already exists" 충돌.
GIT_SHA=$(git rev-parse --short HEAD)
docker compose build --build-arg "GIT_SHA=$GIT_SHA" api mcp-http dashboard

# 2. 이전 컨테이너/이미지 정리 후 재기동
docker compose down
docker compose up -d

# 3. 어떤 SHA가 박힌 이미지인지 즉시 확인
docker exec raven-api cat /app/.git_sha
# → fa65226 같은 7자 SHA가 보이면 OK. 보이지 않으면 stale.
```

**이미지 핀 정책 (왜 필요한가)**: docker-compose는 `image: raven:latest` 만 쓰면 캐시된 이전 레이어를 재사용합니다. 한 번 rename/리팩토 후에도 컨테이너는 옛 코드/템플릿을 들고 있어 vault 생성이 깨지는 일이 발생합니다. **이미지 태그를 GIT SHA로 핀** (`image: raven:${GIT_SHA:-latest}`)하면, 코드 변경 → 다른 태그 → 이전 이미지로 자동 다운그레이드되는 사고가 차단됩니다.

**병렬 빌드 충돌 회피**: yaml anchor `&raven_image` 가 `build` + `image:` 를 묶어 3개 서비스가 동일 정의(`<<: *raven_image`)를 공유합니다. 같은 `image:` 태그로 parallel export 하면 Docker가 `image "raven:<sha>": already exists` 에러로 한두 서비스 빌드가 죽습니다. 위 명령처럼 **서비스 이름을 explicit 나열**해 sequential build 하면 회피됩니다. 대안으로 `make docker-build-{api,mcp-http,dashboard}` (Makefile에 이미 존재) 도 동일한 sequential 동작입니다.

**Makefile 단축 명령** (changelog-v0.7.17의 `docker-build-{api,mcp-http,dashboard}` 패턴 활용):
```bash
GIT_SHA=$(git rev-parse --short HEAD) make docker-build
# 또는 한 줄씩:
GIT_SHA=$(git rev-parse --short HEAD) make docker-build-api
GIT_SHA=$(git rev-parse --short HEAD) make docker-build-mcp-http
GIT_SHA=$(git rev-parse --short HEAD) make docker-build-dashboard
```

---

## 환경 변수 (선택)

| 변수 | 기본 | 효과 |
|---|---|---|
| `WIKI_VAULTS_DIR` | `~/Raven` | vaults 루트 전체 변경 |
| `WIKI_VAULT` | (registry default) | active vault 일시 변경 |

```bash
# 예: 다른 위치 vault 사용
WIKI_VAULTS_DIR=~/Documents/vaults raven vault list
WIKI_VAULT=agent-output raven page ls
```

---

## 핵심 명령 (CLI 9)

```bash
raven where                                 # 환경 표시
raven vault list                            # 등록된 vault 목록
raven vault use <name>                      # 기본 vault 전환
raven vault info [name]                     # 메타 + 통계
raven vault create <name> <path>            # 새 vault 생성 + 등록
raven vault register <name> <path>          # 기존 폴더를 vault로 등록
raven vault remove <name> --force           # 등록 해제 (파일은 유지)

raven page ls [--type T] [--tag T] [--vault N] [--json]
raven page get <slug> [--vault N]
raven page new <slug> --title T --type T --tags "a,b" [--vault N]
raven page delete <slug> [--vault N] [--force]

raven link check [--vault N] [--json]       # broken/missing wikilink
raven build [--vault N] [--db PATH] [--lint]   # wiki.db 빌드
raven export [--vault N] [--out DIR]          # GUI 정적 JSON
```

---

## HTTP API (26 endpoints)

```bash
# vault 관리
GET    /api/vaults
GET    /api/vaults/{name}
POST   /api/vaults/{name}/select

# 페이지 CRUD
GET    /api/vaults/{name}/pages[?type=T&tag=T]
GET    /api/vaults/{name}/pages/{slug}
POST   /api/vaults/{name}/pages                  # body: {slug, title, content, type, tags}
PUT    /api/vaults/{name}/pages/{slug}           # body: {content, title?, type?, tags?}
DELETE /api/vaults/{name}/pages/{slug}           # → _archive/

# 쿼리
GET    /api/vaults/{name}/search?q=X&top_k=N
GET    /api/vaults/{name}/link-check[?slug=X]

# 엔진
POST   /api/vaults/{name}/build                  # wiki.db 재빌드 + lint
POST   /api/vaults/{name}/export                 # GUI 정적 JSON
```

전부 `{ok: true, ...}` 또는 `{ok: false, error: "..."}` 형식.

---

## 에이전트 인터페이스 (MCP, v0.7.8+)

> **에이전트(LLM client) ↔ Raven = MCP 단일 표준**.
> Python adapter(`raven.agents`)는 v0.7.9+ 제거됨.

MCP client (어떤 LLM 기반 agent든 표준 protocol 사용)는:
- `tools/list` — 자동 도구 발견
- `tools/call` — 도구 호출 (`wiki_update`, `wiki_get_page`, `wiki_search`, `wiki_lint` 등)
- 표준 protocol (stdio 또는 HTTP)

```json
// MCP client 설정 (예: Claude Desktop)
// ~/.config/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "raven": {
      "url": "http://127.0.0.1:8766/mcp"
    }
  }
}
```

```bash
# Raven MCP server 띄우기
make rebuild          # Docker image rebuild + restart
# 또는 이미 빌드된 상태면
make docker-up

# stdio client용 MCP는 컨테이너에서 실행
docker compose exec api docker-entrypoint.sh mcp-stdio
```

> **자세한 도식**: `_meta/diagrams/three-flows.png`
> **정책**: AGENTS.md §5.5 "MCP = 에이전트 표준 프로토콜"

---

## vault 구조

```
~/Raven/
├── .registry.json              # vault 인덱스 (default + 목록)
└── <vault-name>/
    ├── .vault.json             # per-vault 메타 (name, path)
    ├── content/                # 사용자 마크다운 (Obsidian식 자유)
    │   ├── _template.md
    │   ├── llm-wiki.md
    │   └── projects/harumoa/_overview.md
    ├── _meta/                  # 시스템 문서 (SCHEMA, RULES, ...)
    ├── _archive/               # 삭제된 페이지 백업
    ├── wiki.db                 # SQLite (gitignore)
    └── wiki.db.backup          # 자동 백업
```

`.registry.json` 예시:
```json
{
  "version": 1,
  "default": "default",
  "vaults": {
    "default":      {"path": "/Users/jaekanglee/Raven/default",       "mode": "personal", "owner": "user"},
    "agent-output": {"path": "/Users/jaekanglee/Raven/agent-output",  "mode": "agent",    "owner": "hermes"}
  }
}
```

### Tier 1 ↔ Tier 2 경계

Raven은 vault 데이터에 들어가는 문서를 두 계층으로 나눕니다:

| Tier | 위치 | 접근 | 용도 |
|---|---|---|---|
| **Tier 1** (raven 패키지 내부) | `raven/agent/`, `raven-policy.md`, `OPERATIONS.md` | `raven docs show <topic>` | raven CLI/API 운영 매뉴얼 |
| **Tier 2** (사용자 vault) | `<vault>/_meta/system/` | vault 직접 read | vault 데이터 운영 규칙 |

- `vault clone` 기본 = **content only** (Tier 1 leak 방지)
- Tier 2 Lite = **5종 고정** (`SCHEMA.md` / `RULES.md` / `AGENTS.md` / `PROJECT-WORKFLOW.md` / `log.md`)
- Tier 1 ↔ Tier 2 혼동 시 `raven vault verify <name>`로 진단

---

## vault frontmatter 스키마

```yaml
---
title: 페이지 제목
type: concept | person | comparison | project | tool | rule | query | journal
tags: [core-tag, custom-tag]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [content/source-page]              # 인용한 페이지 (선택)
confidence: high | medium | low              # 신뢰도 (선택)
agents:                                      # 에이전트가 쓴 경우 (자동)
  - name: hermes-writer
    timestamp: 2026-06-25T13:12:35
    run_id: run-2026-06-25-001
    intent: 사용자 요청 정리
---
```

wikilink: `[[content/llm-wiki]]` (auto), `[[link]]!` (broken), `[[link]]?` (placeholder).

---

## GUI 사용

```
http://localhost:5173                     # vite dev server

좌측 헤더:
  📁 <vault>       ← vault picker (클릭 → 다른 vault 전환)
  🔍 검색          ← vault별 실시간 BM25
  🕸 Graph         ← vault 링크 그래프
  🔍 Search        ← 전체 검색

좌측 사이드바:
  📚 Wiki          ← 홈
  ➕ 새 페이지     ← 새 페이지 생성 (현재 vault에)
  트리             ← vault 페이지 계층

페이지 헤더:
  ✏️ 편집          ← textarea 편집 → raven API PUT
  🗑 삭제          ← slug 재입력 확인 → _archive로 백업
```

vault 전환 시 페이지 자동 새로고침. localStorage `raven:active_vault`에 저장.

---

## 빌드 / 검증

```bash
# Python 타입/린트
python -m py_compile raven/**/*.py
scripts/.venv/bin/python -c "from raven.cli import app; print('OK')"

# TypeScript
cd dashboard && npx tsc -b --noEmit
cd dashboard && npm run build     # PWA 자동 생성 (dist/sw.js)

# E2E
raven build && raven link check
```

---

## 파일 트리 (코드베이스)

```
~/Desktop/Dev/Project/Raven/         ← 이 저장소 (개발 코드)
├── raven/                          ← 핵심 패키지
│   ├── core/
│   │   ├── registry.py              ← vault 발견 (.registry.json + env)
│   │   ├── vault.py                 ← vault 핸들 (load/create/resolve_active)
│   │   ├── db.py                    ← wiki.db 빌드 wrapper
│   │   ├── lint.py                  ← lint runner
│   │   ├── export.py                ← GUI 정적 JSON
│   │   └── link.py                  ← wikilink 파싱/감사
│   ├── cli/
│   │   └── __main__.py              ← Typer 9 commands
│   ├── api/
│   │   ├── server.py                ← FastAPI app
│   │   ├── main.py                  ← uvicorn entry
│   │   └── __main__.py
│   └── agents/
│       └── agent.py                 ← Agent + AgentVault
├── dashboard/                        ← React 19 SPA
│   ├── src/
│   │   ├── components/              ← Sidebar, VaultPicker, EditButton, ...
│   │   ├── routes/                  ← PageView, SearchPage, GraphPage
│   │   └── lib/api.ts               ← fetch 헬퍼
│   └── public/api/                  ← (legacy) 정적 JSON
├── scripts/                          ← legacy 빌드/lint 스크립트 (subprocess로 호출됨)
│   ├── build_db.py
│   ├── lint.py
│   ├── export_static.py
│   └── backup_db.py
├── _meta/                            ← 시스템 문서 (이 프로젝트 자기 자신에 대한 wiki)
├── raven/mcp/                      ← MCP 서버 (v0.6.0+ namespace)
├── mcp/                              ← (deprecated, v0.6.0에서 raven/mcp/로 이동)
└── log.md                            ← 작업 로그
```

---

## 의존성

```
# Python (scripts/.venv)
typer              # CLI
fastapi            # API
uvicorn[standard]  # ASGI server
pydantic           # 데이터 모델
python-frontmatter # .md 파싱
sqlite3 (stdlib)

# Node (dashboard/)
react@^19
react-router-dom@^7
@xyflow/react      # 그래프
minisearch         # (legacy) 클라이언트 BM25
zustand            # 상태관리
react-markdown + remark-gfm + remark-math + rehype-katex + rehype-highlight
mermaid            # 다이어그램
vite-plugin-pwa    # PWA
```

설치:
```bash
uv pip install --python scripts/.venv/bin/python typer fastapi 'uvicorn[standard]' pydantic python-frontmatter
cd dashboard && npm install
```

---

## 결정 사항 (요약)

자세한 결정 내역은 `_meta/decisions-d1-d6.md` + 후속 결정(D7-D9 multi-vault).

| # | 결정 | 이유 |
|---|---|---|
| D1 | Obsidian-free, 자체 빌드 | 사용자 인용: "옵시디언 안 사고" |
| D2 | SQLite (단일 DB) | 단순, 충분, git 추적 불필요 |
| D3 | React SPA (정적 빌드) | PWA, 오프라인 |
| D4 | Tailscale 원격 | VPS 비용 절감 |
| D5 | wikilink 표준 `[[...]]` | Obsidian 호환 |
| D6 | SCHEMA v2.4 | type taxonomy + intent suffix |
| **D7** | **vault 분리 (코드 ≠ 데이터)** | **사용자 제약 A: "런타임 데이터를 개발 폴더에 두지 않음"** |
| **D8** | **multi-vault + 중앙 레지스트리** | **사용자 비전: 여러 vault 동시 운영** |
| **D9** | **에이전트 1급 시민 + scope** | **사용자 제약 B: "에이전트가 vault에 쓰고 관리"** |

---

## 관련 문서

- `AGENTS.md` — AI 에이전트 운영 규칙 (이 Raven 코드베이스를 다룰 때)
- `~/Raven/<vault>/_meta/system/README.md` — vault 운영자 가이드 (Lite bootstrap 자동 복사, +α opt-in)
- `~/Raven/<vault>/_meta/agents/PROJECT-WORKFLOW.md` — 프로젝트 에이전트 공통 작업 지시 템플릿
- `docs/vault-patterns.md` — **Karpathy LLM Wiki +α 가이드** (v0.7.0+) — raw/ log.md _meta/agents/ opt-in 패턴, 사용자 자유
- `_meta/decisions/adr-2026-06-30-llm-wiki-plus-alpha.md` — **+α 결정 ADR** (v0.7.0+)
- `_meta/changelog-v0.5*.md` — 변경 이력
- `_meta/decisions-d1-d6.md` + `decisions-d7-d9-multivault.md` — 결정 내역
- `_meta/SCHEMA-v0.2-multivault.md` — vault frontmatter 스키마
- `_meta/architecture-5layer.md` — 시스템 아키텍처
- `_meta/deployment.md` — VPS + Tailscale 배포
- `_meta/dr-runbook.md` — 재해 복구

---

## 진입점 추가 / 변경 의사결정

진입점 구조 변경은 **큰 결정**. 다음 절차 따르세요:

1. **ADR 작성**: `_meta/decisions/adr-YYYY-MM-DD-<topic>.md`
2. **write contract 단일화 검증**: 모든 write가 `raven.core`의 같은 create/update/delete/log/rebuild contract를 타는지 확인
3. **테스트 추가**: 새 진입점의 회귀 가드
4. **README + AGENTS.md 동기화**
5. **사용자 승인** → 머지

→ 5번째 진입점 (Telegram, Slack 등) 추가 ❌ — 외부 오케스트레이터의 영역.

---

## 라이선스 / 상태

- v0.5.5 (Lite bootstrap with AGENTS.md, templates → _deprecated)
- 단일 사용자 가정 (auth 없음, 127.0.0.1 기본 바인딩)
- 멀티 에이전트 write는 **experimental** (scope 명시 + 동시성 사용자 책임)
- Not production-ready for multi-tenant (CORS open, no auth)
