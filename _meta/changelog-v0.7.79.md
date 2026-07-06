# Changelog v0.7.79 — verify-all 회귀 가드 + README vendor 예시 (2026-07-06)

> **BLUF**: 사용자 정확한 진단 흐름 연속 — v0.7.75 verify-all endpoint 회귀 가드 4개 추가 (회귀 안전성), README.md 에이전트 인터페이스 섹션 vendor 예시 다중화 (사람 운영자가 외부 MCP 클라이언트 운영자에게 정확한 설정 위치 안내). per-feature commit 2개.
>
> 이전 changelog: `_meta/changelog-v0.7.78.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `1d4c108` | A. verify-all pytest 회귀 가드 4개 | `tests/test_bootstrap_verify.py` | +107 |
| `1ebbdfc` | B. README.md — 에이전트 인터페이스 섹션 vendor 예시 다중화 | `README.md` | +71/−11 |

---

## A. verify-all pytest 회귀 가드 4개 (`1d4c108`)

v0.7.75에서 추가된 `POST /api/vaults/verify-all` endpoint의 회귀 안전성 확보.

### 4개 가드

| 가드 | 검증 |
|---|---|
| `test_api_verify_all_returns_200_and_envelope` | 응답 envelope 스키마 (ok/total/ok_count/mismatch_count/results) + per-vault 항목 |
| `test_api_verify_all_reports_mismatch_per_vault` | 부분 mismatch 시 **409 ❌** (list view 의미, 200으로 흡수) |
| `test_api_verify_all_handles_corrupt_vault_gracefully` | vault별 예외 흡수 (monkeypatch로 simulate corruption) |
| `test_api_verify_all_with_no_vaults` | 빈 registry (total=0 ok=True) |

### 기존 가드 유지

- `POST /api/vaults/{name}/verify` 단일 vault 3개 가드 (200/409/404)
- Lite bootstrap 함수 단위 16개 가드 (verify_bootstrap / verify_and_warn / template_map)

**검증**: pytest 23 passed (기존 19 + 신규 4).

---

## B. README.md 에이전트 인터페이스 섹션 확장 (`1ebbdfc`)

사용자 진단 (v0.7.74): *"사람 운영자가 외부 MCP 클라이언트 운영자에게 vault를 주고 필요한 세팅을 지시할 수 있어야."*

README.md는 사람 운영자 가이드이므로 vendor 예시 OK (Lite bootstrap 정책은 *vault 내용*에만 적용 — README는 무관).

### 변경

| 영역 | 이전 | 이후 |
|---|---|---|
| **stdio 패턴 스니펫** | ❌ 없음 | ✅ Claude Desktop JSON 예시 + `{command, args}` |
| **HTTP 패턴 스니펫** | Claude Desktop만 | Claude Desktop + Cursor JSON 예시 |
| **vendor-neutral 본문** | "예: Claude Desktop" | "Claude Desktop / Cursor / Hermes / Codex / Antigravity / 기타 표준 구현체" |
| **권한 모드** | ❌ 없음 | 3종 표 + "admin은 사람 운영자 전용" 명시 |
| **첫 도구 호출 패턴** | ❌ 없음 | tools/list 흐름 + `vault=<이름>` 인자 필수 안내 |
| **cross-link** | _meta/diagrams만 | + PROJECT-WORKFLOW.md §1.5.1 |

### vendor-neutral 검증

- **본문**: vendor-neutral (JSON-RPC, Model Context Protocol)
- **예시**: Claude Desktop + Cursor (사람 운영자가 외부 운영자에게 *파일 위치* 참고용으로 전달)

**검증**: 변경 라인 수만 (markdown, TypeScript/Python 무관).

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `pytest tests/test_bootstrap_verify.py -q` | 23 passed |
| `git push origin master` | 완료 |

---

## §2 — 외부 MCP 클라이언트 운영자 walkthrough (검증 시나리오)

> "사람 Raven 운영자가 외부 MCP 클라이언트 운영자에게 vault 전달 + 설정 안내"

1. **README.md 전달** (또는 vault + 함께 §1.5.1 extract)
2. **운영자 가이드 §에이전트 인터페이스**:
   - "어떤 MCP 클라이언트든 표준 protocol — Claude Desktop / Cursor / Hermes / Codex / Antigravity / 기타"
   - **stdio 패턴 스니펫** (로컬 sub-process, 권장)
   - **HTTP 패턴 스니펫** (원격 — Claude Desktop / Cursor 각각 파일 위치)
3. **첫 도구 호출**: `vault=<이름>` 인자 — 운영자에게 등록된 이름 확인
4. **문제 시**: §1.5.1 트러블슈팅 4가지

→ 외부 운영자가 README만 읽고 자기 MCP 클라이언트에 정확히 Raven 추가 가능.

---

## §3 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.74 | PROJECT-WORKFLOW.md §1.5 + Wizard MCP snippet |
| v0.7.75 | VaultManage 자동 verify-all + 일괄 업뎃 banner |
| v0.7.76 | CDS 토큰 30곳 정리 + label 이모지 + 즐겨찾기 hover |
| v0.7.77 | §1.5.1 표준 MCP 패턴 + Wizard 동기화 |
| v0.7.78 | §0 vault 경계 명시 |
| v0.7.79 | **verify-all 회귀 가드 + README vendor 예시 다중화** |

→ 회귀 안전성 (verify-all) + 사람 운영자 가이드 (README) 동시 강화. 외부 MCP 클라이언트 운영자가 README만 읽고 정확히 설정 가능.