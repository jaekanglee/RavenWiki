# raven — Multi-Vault Wiki Engine

> **Obsidian-free, agent-aware, multi-vault.** markdown + git + 자체 뷰어 + Python 어댑터.
> vault는 어디든 지정 가능, 사람과 에이전트가 동시에 사용.

---

## 무엇인가

raven는 **LLM Wiki 패턴** (Karpathy 2026)을 자기 호스팅으로 구현한 시스템.

| 계층 | 구현 | 위치 |
|---|---|---|
| **Vault** (데이터) | 마크다운 폴더 (Obsidian식 자유 계층) | `~/vaults/<name>/` |
| **Index** (쿼리) | SQLite (FTS5 + backlinks view) | `<vault>/wiki.db` |
| **Engine** (Python) | raven.core (db/lint/export/link) | `raven/core/` |
| **CLI** (사람) | Typer 9 commands | `raven/cli/` |
| **API** (HTTP) | FastAPI 12 endpoints | `raven/api/` |
| **GUI** (웹) | React 19 + Vite + PWA | `dashboard/` |
| **Adapter** (에이전트) | Python scope-based API | `raven/agents/` |

**SoT = 마크다운**. DB/API/GUI는 **모두 재생성 가능**한 파생 산출물.

---

## 왜 만들었나 (vs Obsidian)

| Obsidian | raven |
|---|---|
| vault = 사용자가 폴더 지정 ✅ | 동일 ✅ |
| GUI만 있음 | **GUI + CLI + Python + HTTP 4개 인터페이스** |
| 사람이 1차 사용자 | **사람 + 에이전트 동시 1차 사용자** |
| 플러그인 = UI 확장 | **에이전트 = vault 1급 시민** (scope/provenance) |
| 단일 앱 | **multi-vault, multi-user 가능** |

사용자 인용 (2026-06-25):
> "옵시디언 안 사고, 모티브만 빌려서 내가 직접 만들 거야"
> "안정적이고, 심플한걸로 기준. 도전적인건 지양"

→ Obsidian의 **사용성 + 안정성**을 닮되, **에이전트 협업**을 1급 시민으로 추가.

---

## 빠른 시작 (이미 셋업된 로컬)

```bash
# 0. 환경
cd ~/Desktop/Dev/Project/Wiki
source scripts/.venv/bin/activate   # venv

# 1. vault 확인
raven where                       # 현재 설정 + vault 목록

# 2. (선택) 새 vault 만들기
raven vault create personal ~/vaults/personal
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

---

## 환경 변수 (선택)

| 변수 | 기본 | 효과 |
|---|---|---|
| `WIKI_VAULTS_DIR` | `~/vaults` | vaults 루트 전체 변경 |
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

## HTTP API (12 endpoints)

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

## Python 어댑터 (에이전트)

```python
from raven.agents import Agent, AgentScope

# 1. scope 정의 (단일 vault, delete 권한 없음)
hermes = Agent.named(
    "hermes-writer",
    scope="agent-output",
    run_id="run-2026-06-25-001",
    intent="사용자 요청 정리",
)

# 2. vault 핸들
av = hermes.vault("agent-output")

# 3. write (자동 frontmatter + provenance)
result = av.write(
    "content/llm-wiki-pattern",
    body,
    title="LLM Wiki 패턴",
    type="concept",
    tags=["agent-output", "llm-wiki"],
)
# → 파일 frontmatter에 자동 삽입:
#   agents:
#     - name: hermes-writer
#       timestamp: 2026-06-25T13:12:35
#       run_id: run-2026-06-25-001
#       intent: 사용자 요청 정리

# 4. read / search / list
av.read("content/llm-wiki-pattern")
av.search("karpathy", top_k=5)
av.list(type="concept")
av.exists("content/foo")

# 5. permission
hermes.vault("default")         # ❌ PermissionError (scope 밖)
```

---

## vault 구조

```
~/vaults/
├── .registry.json              # vault 인덱스 (default + 목록)
└── <vault-name>/
    ├── .vault.json             # per-vault 메타 (name, mode, owner)
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
    "default":      {"path": "/Users/jaekanglee/vaults/default",       "mode": "personal", "owner": "user"},
    "agent-output": {"path": "/Users/jaekanglee/vaults/agent-output",  "mode": "agent",    "owner": "hermes"}
  }
}
```

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
~/Desktop/Dev/Project/Wiki/           ← 이 저장소 (개발 코드)
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
├── mcp/                              ← (legacy) MCP 서버
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

- `~/vaults/default/_meta/raven-guide.md` — vault 사용자 가이드 (사람/에이전트 공통)
- `~/vaults/default/_meta/raven-faq.md` — 자주 묻는 질문
- `_meta/architecture-5layer.md` — 시스템 아키텍처 (4 layer)
- `_meta/SCHEMA.md` — vault frontmatter 스키마
- `_meta/RULES.md` — 운영 규칙
- `_meta/deployment.md` — VPS + Tailscale 배포
- `_meta/dr-runbook.md` — 재해 복구
- `_meta/decisions-d1-d6.md` + 후속 결정 (D7-D9)

---

## 라이선스 / 상태

- v0.2.0 (multi-vault)
- 단일 사용자 가정 (auth 없음, 127.0.0.1 기본 바인딩)
- Not production-ready for multi-tenant (CORS open, no auth)
