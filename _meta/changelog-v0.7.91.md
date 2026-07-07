# Changelog v0.7.91 — MCP `wiki_get_guide` (Lite bootstrap 3종 read-only MCP surface)

> **BLUF**: v0.7.89 REST `/api/vaults/{name}/guide/{kind}` 의 contract를 **MCP 표면에도 동일하게 노출** (`wiki_get_guide`, v0.7.91+). **도구 9개 → 10개** (read 그룹 +1). 화이트리스트 fail-closed 동일 (Tier 1 leak 방지). ADR 동반: `_meta/decisions/adr-2026-07-07-mcp-wiki-get-guide.md`. 회귀 631/631 PASS (v0.7.90 baseline 623 + 8 신규) + Dashboard build clean.

이전 changelog: `_meta/changelog-v0.7.90.md`

---

## §0 — 변경 요약 (4 파일 수정 + 2 신설)

| 파일 | 변경 | LOC |
|---|---|---|
| `raven/mcp/tools/__init__.py` | `LITE_GUIDE_KINDS` + `GuideNotFoundError` + `_resolve_guide_path` + `read_guide` helper | +93 |
| `raven/mcp/tools/read.py` | `wiki_get_guide` 함수 (5 → 6 read 도구) | +24 |
| `raven/mcp/cli.py` | `@mcp.tool(name="wiki_get_guide", ...)` 등록 + 헤더 코멘트 9→10 갱신 | +17 |
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | §1 MCP 도구 표에 1줄 추가 (wiki_get_guide) | +1 |
| `tests/test_v0_7_91_mcp_wiki_get_guide.py` (신설) | 회귀 가드 8 tests (whitelist / 403 / 404 / shape / 등록 확인) | +200 |
| `_meta/decisions/adr-2026-07-07-mcp-wiki-get-guide.md` (신설) | ADR: MCP 표면 승격 결정 (의미 변경) | — |

---

## §1 — 무엇을 만들었나

### 1.1 신규 도구: `wiki_get_guide`

```
wiki_get_guide(vault: str, kind: str) -> dict
```

- `vault`: 등록된 vault 이름 (기존 도구와 동일)
- `kind`: 화이트리스트 3종 중 하나
  - `_meta/agents/SCHEMA.md`
  - `_meta/agents/PROJECT-WORKFLOW.md`
  - `log.md`
- 응답: REST `/api/vaults/{name}/guide/{kind}` 와 **동일 shape**
  ```
  {ok, vault, kind, content, size, modified}
  ```
- 모드: `read` (모든 모드에서 사용 가능, write/admin 권한 불요)
- 화이트 외 kind → `ValueError` (MCP tool error, REST 403과 동치)

### 1.2 MCP 도구 표 (v0.7.91+)

| 모드 | 도구 | ... |
|---|---|---|
| `read` (always) | `wiki_search` / `wiki_get_page` / `wiki_lint` / `wiki_graph` / `wiki_log` / **`wiki_get_guide`** / `wiki_stale_detect` | 7개 |
| `write` (+`--write`) | + `wiki_update` / `wiki_ingest` / `wiki_archive` | 3개 |
| `admin` (+`--admin`) | + `wiki_delete` / `wiki_rename` | 2개 |
| **합계** | | **12개 (read 7 + write 3 + admin 2)** |

(도구 9개 → 10개 → 12개 명세 정정. 기존 코멘트 "Read (always): 6종" 은 stale, v0.7.91 헤더 갱신으로 정합.)

### 1.3 PROJECT-WORKFLOW.md §1 갱신

Lite bootstrap 3종을 MCP로 read하는 정식 표면 신설 — Quick Start Step 1-2 가 MCP 클라이언트에서도 즉시 실행 가능.

## §2 — 왜 MCP 표면이 필요했나

### 2.1 R9 위험 (MCP 표면 없을 때)

AGENTS.md §9: "에이전트는 vault 외부 시스템/폴더를 직접 수정하지 않는다."

Strict 해석: PROJECT-WORKFLOW 본문을 보려면 vault 파일시스템 read가 사실상 유일한 방법. R9 ("외부 시스템") 정의에 걸릴 수 있음. v0.7.65+ Lite bootstrap 정책상 `_meta/agents/` 는 vault 내부지만, 그 contents를 agent가 raw read하는 건 정책의도와 어긋남.

→ **표준 MCP surface = R9 risk 0**.

### 2.2 §0.5 normative "추측 금지" + Quick Start 정합

v0.7.90 PR1에서 "Quick Start Step 1 = Layer 인지, Step 2 = log.md" 신설. **MCP 클라이언트도 같은 Step을 표준 protocol로 수행 가능**해짐. v0.7.91 이전엔 MCP는 `wiki_search` 우회만 가능했음.

### 2.3 v0.7.89 REST contract 그대로 승격

helper (`LITE_GUIDE_KINDS`, `read_guide`) 는 `raven/mcp/tools/__init__.py` 에 정의. **REST와 별도 화이트리스트** (Raven 4개 진입점 정책상 두 layer의 SOT는 각자). drift 위험은 pytest 회귀 가드 (16 tests: 8 REST + 8 MCP) 로 방지.

## §3 — 검증

### 3.1 신규 가이드 MCP 테스트

```
tests/test_v0_7_91_mcp_wiki_get_guide.py:: 8/8 PASS
  ├─ test_resolve_guide_path_accepts_three_kinds       PASS
  ├─ test_resolve_guide_path_accepts_basename_for_log  PASS
  ├─ test_resolve_guide_path_rejects_non_whitelist    PASS  (403 equivalent)
  ├─ test_resolve_guide_path_rejects_path_traversal   PASS  (../)
  ├─ test_read_guide_returns_full_shape               PASS  (REST 1:1)
  ├─ test_read_guide_log_md                           PASS
  ├─ test_read_guide_404_when_file_missing            PASS
  └─ test_wiki_get_guide_registered_in_cli            PASS
```

### 3.2 회귀

```
$ pytest tests/ -q --ignore=tests/curator
631 passed, 1 skipped, 1 warning in 40.43s
```

(v0.7.90 baseline 623 + 8 신규 = 631, 0 회귀)

### 3.3 Dashboard build

```
$ cd dashboard && npm run build
✓ built in 1.82s (변경 0 — sanity)
```

## §4 — AGENTS.md / SCHEMA.md 영향

- **AGENTS.md §4 (Lite bootstrap 정책)**: 변경 없음. 3종 그대로.
- **AGENTS.md §5.5 (MCP 표준화)**: 정합 강화. "에이전트 ↔ Raven = MCP 1개" 원칙 + Lite bootstrap 3종 read 모두 MCP 가능.
- **AGENTS.md §9 (R9)**: README 변경 없음. v0.7.91 의도가 R9 강화.
- **SCHEMA.md**: 변경 없음.

## §5 — 후속 작업 (deferred)

- **Dashboard drawer에서 MCP `wiki_get_guide` 직접 호출**: 현재 drawer는 REST endpoint 사용. MCP 직접 호출로 전환 시 일관성 ↑ (v0.7.92+ 검토)
- **MCP guide 결과 캐싱**: vault 동기화 시까지 cache (멀티 vault에서 효율성). lite bootstrap sync 정책과 결합 (v0.7.93+ 검토)
- **PR2-B (PROJECT-WORKFLOW.md §1-7 재배치)**: 사용자 1차 제안 후속. §1 normative 의미 변경 가능성 → ADR 동반 (별도 사이클)
