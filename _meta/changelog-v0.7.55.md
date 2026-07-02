# raven v0.7.55 — Lite bootstrap 4종 raw/ 정책 + MCP wiki_ingest user_command 플래그

> **핵심**: v0.7.50에서 결정된 raw/ = 사람 1차 운영 영역 (ADR-2026-07-02) 정책이 사용자 vault에 자동 박히도록 Lite bootstrap 5종(RULES/README/PROJECT-WORKFLOW/SCHEMA/log.md) 중 운영 가이드 2종(RULES/README)을 갱신했습니다. 또한 `wiki_ingest` MCP 도구에 사람 명시적 명령을 강제하는 `user_command: bool = False` 플래그를 추가해 에이전트 자율 raw/ 쓰기를 차단했습니다. Lite bootstrap 4종 + MCP 변경은 서로 다른 영역이지만 v0.7.50의 raw/ 정책 결론을 일관되게 적용하는 한 묶음 변경입니다.

릴리스 일자: 2026-07-02
이전: v0.7.54

---

## 1. 변경 사항

### 1-1. `raven/core/templates/system/RULES.md` — R6 섹션 추가

[v0.7.50 raw/ 정책](https://...) 박기. 새 R6 "raw/ 폴더 권한" 섹션:

- 사람 = full CRUD (조회/작성/수정/삭제/이동) — Dashboard `/raw` panel, `raven raw ...` CLI, OS 파일관리자
- 에이전트 = read-only (MCP `wiki_read`만 가능, `wiki_ingest`는 사람 명시 명령 필요)
- raw/ = source of truth — 에이전트 자율 변조 ❌ (사람이 검증한 자료만)

### 1-2. `raven/core/templates/system/README.md` — 권한 표 다듬기

기존 "에이전트 기준" 표현을 "주체 + 권한" 4-컬럼 표로 재구성:

| 경로 | 주체 | 권한 |
|---|---|---|
| `<vault>/raw/` | **사람 (1차)** | full CRUD |
| `<vault>/raw/` | **에이전트 (read-only)** | read only (wiki_ingest는 user_command 필수) |
| `<vault>/content/` | 에이전트 | read / write |
| `<vault>/_meta/` | 사람+에이전트 | 사람 자유, 에이전트 READ ONLY |
| `<vault>/log.md` | 도구 자동 | append only |

**원칙 추가**: "raw/ 는 사람이 1차로 관리 — north star '사람 1차 사용자' 정렬". 자세한 매트릭스는 RULES.md R6 참조.

### 1-3. `raven/mcp/tools/write.py` `wiki_ingest` — `user_command` 플래그 추가

`wiki_ingest()` 시그니처에 `user_command: bool = False` 매개변수 추가. `False`이면 (에이전트 자율 호출로 간주) 즉시 거부:

```json
{
  "ok": false,
  "error": "user_command_required",
  "message": "wiki_ingest requires user_command=True (ADR-2026-07-02). raw/ is human-first..."
}
```

에이전트 호출 경로(자기주도 ingest) 차단, 사람 호출 경로(CLI `raven raw ingest`, Dashboard `/raw` 패널)는 `user_command=True` 전달 → 정상 작동.

### 1-4. `raven/mcp/README.md` — wiki_ingest 시그니처 문서화

`wiki_ingest` 항목에 `*, user_command: bool = False` 키워드 추가 + "v0.7.55+ 사람 명시 명령 필수" 노트.

### 1-5. `tests/test_v0_7_55_wiki_ingest_user_command.py` — 신규 회귀 가드 4개

1. `test_wiki_ingest_without_user_command_is_rejected` — 기본값 호출 → 거부
2. `test_wiki_ingest_user_command_false_explicitly_rejected` — 명시적 False → 거부
3. `test_wiki_ingest_user_command_true_succeeds` — True → 정상 ingest
4. `test_wiki_ingest_default_param_is_false` — 시그니처 기본값 = False (에이전트 거부 기본값)

### 1-6. 기존 회귀 테스트 6개 갱신

`test_mcp_write_provenance.py` (3 test) + `test_mcp_concurrency.py` (2 test)에 `user_command=True` 추가 — **테스트는 사람 시나리오**임을 명시. (기존 ingest 테스트는 사람 운영자가 CLI로 호출하는 시나리오이므로 True 필수.)

### 1-7. raven-dev vault 갱신

`raven meta sync --vault raven-dev --force`로 5종 강제 복사. **vault 측 RULES.md raw/ 검색: 0 → 7, README.md: 3 → 8**. Lite bootstrap 정책이 raven-dev 운영 vault에 정상 적용.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `pytest tests/test_mcp_write_provenance.py tests/test_mcp_concurrency.py tests/test_tier_boundary.py tests/test_v0_7_8_mcp_only_for_agents.py` | 57/57 passed | 회귀 없음 |
| `pytest tests/test_v0_7_55_wiki_ingest_user_command.py` | 4/4 passed | 신규 회귀 가드 |
| `raven meta sync --vault raven-dev --force` | 5 파일 copied | vault 측 Lite bootstrap 갱신 |
| `grep -c raw/ vault` | RULES 7, README 8 | raw/ 정책 박힘 확인 |
| vendor 표기 검사 (`codex`/`claude`/`antigravity`/`agy` in core templates) | 0 hits | AGENTS.md §13 vendor neutrality 유지 |

---

## 3. 호환성 / 회귀 분석

- **위반 없음**: 사람 호출 경로(CLI/Dashboard)만 영향 — `user_command=True` 전달하면 기존과 100% 동일 동작.
- **에이전트 호출 차단**: MCP `wiki_ingest` 자율 호출 → `error: "user_command_required"` 즉시 거부 (no file mutation).
- **Lite bootstrap 5종 일관성**: `sync_meta(lite=True, force=True)`로 강제 갱신 — 기존 vault 4종 README/RULES가 새 정책으로 덮어쓰임. (Tier 1 leak 없음 — `_LITE_BOOTSTRAP_FILES` whitelist 그대로.)

---

## 4. 다음에 가능한 것

- **CLI `raven raw ingest` 명령 신설** — 사람 호출 경로 (Dashboard `/raw` panel 외)
- **Dashboard `/raw` panel에 `wiki_ingest` 버튼** — Drop된 파일을 raw/로 ingest
- **Lite bootstrap 자동 검증 (lint)** — vault의 5종이 코어와 일치하는지 lint check

---

## 5. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: ADR-2026-07-02 + Lite bootstrap 4종 갱신 의도 명확
- [x] **단순성 (YAGNI)**: 5종 중 raw/와 무관한 SCHEMA/log.md는 건드리지 않음 (surgical)
- [x] **Surgical (§3)**: 기존 회귀 테스트 6개는 `user_command=True`만 추가, 새 테스트 4개로 가드
- [x] **Goal-Driven**: 회귀 가드 4개 + 정량 검증 (grep raw/ 빈도) + lint vendor-neutrality
- [x] **4 저장 신호**: changelog 시간축 보존 ✓, tier_boundary whitelist 그대로 (Tier 1 leak ❌) ✓
