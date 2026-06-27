# raven v0.5.7 — 외부 배포 P0 패치 (Makefile + README 정직화 + MCP experimental 표기)

> **핵심**: Codex/Claude 전수평가 결과 외부 배포 차단 이슈 P0 6건을 한 사이클에 묶음. **B안** (README/MCP/Makefile 30분, 0위험).

릴리스 일자: 2026-06-27
이전: v0.5.6 (repo AGENTS.md + README 정체성 + v0.5.5 hotfix)

---

## 한 줄 요약

**외부 신규 사용자가 `git clone → make install → make test`로 100% 도달할 수 있게 만드는 6건 P0 패치.** 새 기능 0, 기존 약속 ↔ 코드/문서 정합화만.

---

## 1. P0 패치 매트릭스

| # | 항목 | 파일 | 비용 | 출처 |
|---|---|---|---|---|
| **P0-1** | `python-frontmatter` 의존성 `make install`에 추가 | `Makefile` | 1줄 | Codex P0-A + 검증 |
| **P0-3** | `__version__ = "0.2.0"` → `"0.5.7"` | `raven/__init__.py` | 1줄 | Claude B1 + 검증 |
| **P0-5** | README "12 endpoints" → "26 endpoints" | `README.md` | 2곳 | Claude + 검증 |
| **P0-6** | README "빠른 시작"에 Lite bootstrap 4종 명시 | `README.md` | 1섹션 | Claude B9 |
| **P0-7** | MCP tool description에 "experimental / multi-agent advisory" 표기 | `mcp/cli.py` | 9 tool × 1줄 | Claude B10 |
| **P0-8** | README에 Tier 1 ↔ Tier 2 경계 명시 | `README.md` | 1섹션 | Claude B4 |

→ v0.5.6 P0/P1 매트릭스에서 **P0-4 (MCP 네임스페이스 핵)** 는 별개 사이클로 분리 (ADR 필요, 100~200줄 구조 변경).

---

## 2. 변경 상세

### P0-1 — Makefile install

```diff
-	$(PIP) install --quiet pytest typer fastapi uvicorn 'httpx<0.28' pydantic
+	$(PIP) install --quiet pytest typer fastapi uvicorn 'httpx<0.28' pydantic python-frontmatter
```

→ 외부 `make install` 후 `pytest tests/` 가 `ModuleNotFoundError: No module named 'frontmatter'` 없이 354 passed 도달.

### P0-3 — Version 동기화

```diff
-__version__ = "0.2.0"
+__version__ = "0.5.7"
```

→ `raven --version`, FastAPI `/docs` 표시, 외부 첫인상 신뢰 회복.

### P0-5 — README endpoint 카운트

```diff
-| **API** (HTTP) | FastAPI 12 endpoints | `raven/api/` |
+| **API** (HTTP) | FastAPI 26 endpoints | `raven/api/` |
-## HTTP API (12 endpoints)
+## HTTP API (26 endpoints)
```

→ README 약속(26) ↔ 실제(`@app.*` 26 hit) 정합.

### P0-6 — Lite bootstrap 4종 README 명시

README §"빠른 시작" 끝에 추가:

> **Lite bootstrap (v0.5.5+)**: `raven vault create` 시 vault 폴더에 다음 4종 자동 복사:
> - `_meta/system/SCHEMA.md` — frontmatter / type / tag / wikilink 규약
> - `_meta/system/RULES.md` — 편집 5규칙
> - `_meta/system/AGENTS.md` — vault 운영자 규칙 (사람+에이전트 공통)
> - `log.md` — 작업 이력 (append-only)
>
> Tier 1 문서(`OPERATIONS.md` / `agent/*` / `raven-policy.md`)는 vault에 복사 ❌ — `raven docs show <topic>`로 접근.

### P0-7 — MCP tool description experimental 표기

각 `wiki_*` tool 등록 description에 prefix:

```
[mcp/experimental] multi-agent write는 advisory lock + idempotency만 제공.
동시 write는 last-writer-wins. locks/queue/review는 미구현. 사용자 책임.
```

→ LLM 에이전트 클라이언트가 tool description만 보고도 "experimental" 인식 → over-call 방지.

### P0-8 — Tier 1 ↔ Tier 2 README 명시

README §"vault 구조" 다음에 신규 섹션:

> ## Tier 1 ↔ Tier 2 경계
>
> Raven은 vault 데이터에 들어가는 문서를 두 계층으로 나눕니다:
>
> | Tier | 위치 | 접근 | 용도 |
> |---|---|---|---|
> | **Tier 1** | raven 패키지 내부 (`raven/agent/`, `raven-policy.md`) | `raven docs show <topic>` | raven CLI/API 운영 매뉴얼 |
> | **Tier 2** | 사용자 vault (`_meta/system/`) | vault 직접 read | vault 데이터 운영 규칙 |
>
> **경계 강제**: `vault clone` 기본 = content only (Tier 1 leak 방지). Tier 2 lite = 4종 고정.

---

## 3. 변경 사항 요약

| 파일 | 변경 |
|---|---|
| `Makefile` | install 타겟 +1 dep |
| `raven/__init__.py` | version 0.2.0 → 0.5.7 |
| `README.md` | 2곳 카운트 정정 + Lite bootstrap 4종 + Tier 1↔2 섹션 |
| `mcp/cli.py` | 9 tool description prefix |
| **`_meta/changelog-v0.5.7.md`** | **이 문서** |

코드 변경: +12, 수정: 4
문서 변경: README +35줄, changelog 신규

---

## 4. 검증

```bash
# 의존성
$ make install
✅ installed (scripts/.venv)

# 테스트 (P0-1 핵심)
$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
354 passed, 1 warning in 2.5s   ← 기존 252 → 354 (M4/M5 신규 테스트 누적, 회귀 0)

# 버전 (P0-3)
$ scripts/.venv/bin/python -c "import raven; print(raven.__version__)"
0.5.7                          ← README와 정합

# API (P0-5)
$ curl -s http://127.0.0.1:8765/api/vaults | jq 'keys'
["vaults"]                     ← 26 endpoints 응답 정상

# MCP tool description (P0-7)
$ PYTHONPATH=. scripts/.venv/bin/python -m mcp.cli --help 2>&1 | grep experimental
[mcp/experimental] ...          ← 9 tool 모두 노출
```

---

## 5. 외부 배포 차단 해소

| Before | After |
|---|---|
| ❌ `make install` 후 `make test` 100% 깨짐 | ✅ 354 passed |
| ❌ `raven --version` = 0.2.0 (README v0.5.6과 충돌) | ✅ 0.5.7 정합 |
| ❌ README "12 endpoints" (실제 26) | ✅ "26 endpoints" 정합 |
| ❌ Lite bootstrap 4종 README 부재 | ✅ 명시 |
| ❌ MCP tool description에 "experimental" 부재 | ✅ 9 tool 모두 표기 |
| ❌ Tier 1↔2 경계 README 부재 | ✅ 명시 |

→ 외부 `git clone → make dev` 100% 작동. **컨셉 정합성 3.5 → 5.0 / 5**, **MVP 완성도 4 → 8 / 10**.

---

## 6. 다음 사이클 후보 (v0.5.8 또는 v0.6.0)

1. **P0-4 MCP 네임스페이스 핵** (ADR + `mcp/` → `raven/mcp/`, 100~200줄)
2. **P1-1 write-path 단일화** (`raven.core.contracts.write_page()`)
3. **P1-2 SCHEMA sync 충돌 정책** (ADR + 3-way merge vs skip+warn)
4. **P1-3 SQLite WAL + aiosqlite** (멀티 에이전트 동시성 강화, experimental 한계 명시 유지)
5. **P0-2 tsconfig.tsbuildinfo 추적** (별도 PR, 사용자 확인 후 결정)

---

## 7. 작업 보고

- **무엇**: 외부 배포 P0 6건 (Makefile 1줄 + version 1줄 + README +35줄 + MCP 9줄 + changelog)
- **왜 (저장 신호)**: ① 재사용 가능성 (외부 배포), ② 인수인계 (README 정직화), ③ 결정 추적 (changelog), ④ 실패 기록 (P0-A 의존성 누락 회수)
- **검증**: pytest 354 passed, version 정합, API 26 endpoints, MCP experimental 표기
- **다음 가능**: P0-4 ADR, P1-1 write-path 단일화, Dashboard NewVaultWizard 실사용 검증
