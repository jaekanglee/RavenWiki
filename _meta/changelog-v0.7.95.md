# Changelog v0.7.95 — MCP `wiki_get_guide_diff` (Lite bootstrap 3종 diff MCP surface)

> **BLUF**: v0.7.94 REST `/api/vaults/{name}/guide-diff/{kind}` 의 contract를 **MCP 표면에도 동일하게 노출** (`wiki_get_guide_diff`, v0.7.95+). **도구 10개 → 11개** (read 그룹 +1). 화이트리스트 fail-closed 동일. 에이전트가 "내 vault 지침이 왜 mismatch?" 표준 protocol로 진단 가능. **NORTH STAR 가드 보존**: 1.5배 차단 / 권한 / Lite bootstrap 3종 / Tier 1 leak 방지 모두 그대로. 회귀 647/647 PASS (v0.7.94 baseline 639 + 8 신규) + Dashboard build clean.

이전 changelog: `_meta/changelog-v0.7.94.md`

---

## §0 — 변경 요약 (4 파일 수정 + 1 신설)

| 파일 | 변경 | LOC |
|---|---|---|
| `raven/mcp/tools/__init__.py` | `read_guide_diff()` + `_resolve_guide_template()` + `_LITE_GUIDE_DIFF_TEMPLATE` + `_MAX_DIFF_LINES` | +113 |
| `raven/mcp/tools/read.py` | `wiki_get_guide_diff` 함수 (7 read tool) | +19 |
| `raven/mcp/cli.py` | `@mcp.tool(name="wiki_get_guide_diff", ...)` 등록 + 헤더 코멘트 10→11 갱신 | +20 |
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | §1 MCP 도구 표에 1줄 추가 | +1 |
| `tests/test_v0_7_95_mcp_wiki_get_guide_diff.py` (신설) | 회귀 8 tests (whitelist / 403 / 404 / truncation / 등록) | +200 |
| `_meta/changelog-v0.7.95.md` (신설) | 본 changelog | — |

---

## §1 — 무엇을 만들었나

### 1.1 신규 도구: `wiki_get_guide_diff`

```
wiki_get_guide_diff(vault: str, kind: str) -> dict
```

- `vault`: 등록된 vault 이름 (기존 도구와 동일)
- `kind`: 화이트리스트 3종 중 하나 (wiki_get_guide 와 동일)
  - `_meta/agents/SCHEMA.md`
  - `_meta/agents/PROJECT-WORKFLOW.md`
  - `log.md`
- 응답: REST `/api/vaults/{name}/guide-diff/{kind:path}` 와 **동일 shape** (v0.7.94 1:1)
  ```
  {ok, vault, kind, identical, template_path, diff_lines, stats, truncated, truncation_note}
  ```
- 모드: `read` (모든 모드에서 사용 가능)
- 화이트 외 kind → `ValueError` (MCP tool error, REST 403과 동치)
- 200줄 truncation 동일

### 1.2 MCP 도구 표 (v0.7.95+)

| 모드 | 도구 | ... |
|---|---|---|
| `read` (always) | `wiki_search` / `wiki_get_page` / `wiki_lint` / `wiki_graph` / `wiki_log` / `wiki_get_guide` / **`wiki_get_guide_diff`** / `wiki_stale_detect` | 8개 |
| `write` (+`--write`) | + `wiki_update` / `wiki_ingest` / `wiki_archive` | 3개 |
| `admin` (+`--admin`) | + `wiki_delete` / `wiki_rename` | 2개 |
| **합계** | | **13개 (read 8 + write 3 + admin 2)** |

### 1.3 PROJECT-WORKFLOW.md §1 갱신

Lite bootstrap 3종을 MCP로 read하는 정식 표면 + **diff 진단** 도구 신설. 운영자 / 에이전트 둘 다 같은 surface로 "내 vault 지침이 왜 mismatch?" 즉시 확인.

## §2 — 왜 MCP 표면이 필요했나

### 2.1 R9 정합 (에이전트)
v0.7.94 REST drawer에서 운영자가 진단 가능. **에이전트도 같은 진단 가능**해야 R9 ("에이전트는 vault 외부 시스템 ❌") 정합. v0.7.95 이전엔 에이전트가 Lite bootstrap mismatch 진단을 위해 `wiki_get_guide` + `wiki_get_guide` (동일 vault 끼리) 같은 우회 없었음. **diff 자체가 불가는 R9 위반 위험** (raw filesystem read).

### 2.2 §0.5 normative "추측 금지" 정합
v0.7.90 PR1 + v0.7.92 §1-7 재배치: 에이전트가 작업 전 "이 vault의 운영 사실 확인" = `wiki_get_guide`. **"내 vault가 템플릿과 다른가?" = `wiki_get_guide_diff`**. 두 도구가 함께 정합.

### 2.3 v0.7.91 / v0.7.94 REST surface 그대로 승격
helper (`read_guide_diff`, `_resolve_guide_template`) 는 `raven/mcp/tools/__init__.py` 에 정의. **REST와 별도 화이트리스트** (Raven 4개 진입점 정책상 두 layer의 SOT는 각자). drift 위험은 pytest 회귀 가드 (16 tests: 8 REST + 8 MCP) 로 방지.

## §3 — 검증

### 3.1 신규 가이드 diff MCP 테스트

```
tests/test_v0_7_95_mcp_wiki_get_guide_diff.py:: 8/8 PASS
  ├─ test_resolve_guide_template_three_kinds        PASS
  ├─ test_resolve_guide_template_rejects_non_whitelist PASS
  ├─ test_resolve_guide_template_rejects_path_traversal PASS
  ├─ test_read_guide_diff_returns_modified          PASS
  ├─ test_read_guide_diff_log_md                    PASS
  ├─ test_read_guide_diff_404_for_missing_file      PASS
  ├─ test_read_guide_diff_truncates_at_200_lines    PASS
  └─ test_wiki_get_guide_diff_registered_in_cli     PASS
```

### 3.2 회귀

```
$ pytest tests/ -q --ignore=tests/curator
647 passed, 1 skipped, 1 warning in 40.66s
```

(v0.7.94 baseline 639 + 8 신규 = 647, 0 회귀)

### 3.3 Dashboard build

```
$ cd dashboard && npm run build
✓ built in 1.82s (변경 0)
```

## §4 — AGENTS.md / SCHEMA.md 영향

- **AGENTS.md §4 (Lite bootstrap 정책)**: 변경 없음. 3종 그대로. read-only surface + diff 진단 추가.
- **AGENTS.md §5.5 (MCP 표준화)**: 정합 강화. Lite bootstrap 3종 read + diff 모두 MCP 가능.
- **AGENTS.md §9 (R9)**: README 변경 없음. v0.7.95 의도가 R9 강화 (에이전트의 filesystem read 회피).
- **SCHEMA.md**: 변경 없음.

## §5 — 후속 작업 (deferred)

- **MCP `wiki_get_guide_diff` 결과 캐싱** (v0.7.94+ 후속): 진단 비용 절감.
- **MCP dogfooding** — Claude/Cursor/Hermes 등 외부 에이전트가 `wiki_get_guide_diff` 로 자동 진단 워크플로우.
- **"지침 검증" → "지침 진단 + 갱신" 자동화**: 에이전트가 `wiki_stale_detect` + `wiki_get_guide_diff` + `wiki_update` (사람 명시 명령 시) 로 일괄 진단·수정. 정책 결정 시 ADR 동반.
