---
title: 결정사항 후속 (D7-D9 — Multi-Vault 재설계)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, decisions, raven]
sources: [_meta/decisions-d1-d6.md]
confidence: high
---

# 결정사항 후속 (D7-D9 — M2 Multi-Vault)

> [[decisions-d1-d6]] (M1 결정)의 후속.
> M2 (2026-06-25) — vault 분리 + 멀티 vault + 에이전트 어댑터 재설계.

---

## 결정 매트릭스 (D7-D9)

| # | 결정 | 권장 | 기각 |
|---|---|---|---|
| **D7** | 데이터 위치 | **vault 분리 (코드 ≠ 런타임)** | 단일 vault (가정 ↓) |
| **D8** | Vault 구조 | **multi-vault + 중앙 레지스트리** | Obsidian식 (앱이 직접 스캔) |
| **D9** | 에이전트 인터페이스 | **Python adapter + scope** | shell wrapper (LLM 비효율) |

---

## D7 — vault 분리 (코드 ≠ 런타임)

**문제**: M1까지 vault = `~/Desktop/Dev/Project/Raven/{content,wiki.db,...}`. 코드베이스와 런타임 데이터 혼재.

**사용자 제약** (2026-06-25):
> "개발소스를 들고있는 폴더 내부에 런타임 데이터를 관리하겠다는게 아님"

**결정**: vault를 코드베이스 외부로 분리.

```
~/Desktop/Dev/Project/Raven/      ← 개발 코드 (raven/, dashboard/, scripts/)
~/vaults/                        ← vault 데이터 (런타임)
├── .registry.json
└── default/
    ├── .vault.json
    ├── content/
    ├── _meta/
    └── wiki.db
```

**환경변수 오버라이드** (사용자가 위치 자유롭게 변경 가능):
```bash
WIKI_VAULTS_DIR=~/Documents/vaults raven vault list
```

**근거**:
- 사용자 명시 제약 A
- 코드/데이터 분리 = 표준
- vault 위치 자유 = 유연성

**기각한 대안**:
- 단일 vault 유지: 사용자 비전 위배
- 사용자 home 하위: 위치 자유성 ↓

**부수 작업**: `~/Desktop/Dev/Project/Raven/{content,wiki.db,...}` → `~/vaults/default/`로 데이터 이동 (1단계).

---

## D8 — Multi-vault + 중앙 레지스트리

**문제**: M1 = 단일 vault. 사용자 비전 = **vault 여러 개** (사용자별/에이전트별 분리).

**결정**:
- `~/vaults/.registry.json` = 중앙 vault 인덱스
- 각 vault는 `.vault.json` = per-vault 메타 (name/mode/owner)
- 멀티 디렉토리 가능 (향후 `~/Documents/vaults/` + `~/vaults/` 혼재 가능)

**근거**:
- 사용자 비전: "vault들을 관리하고"
- Obsidian도 multi-vault 지원 (앱이 직접 스캔) → 차이: 우리는 중앙 인덱스
- 에이전트별 vault 분리 가능 (mode: agent / owner: hermes)

**기각한 대안**:
- Obsidian식 (앱 직접 스캔): 멀티 디렉토리 지원 약함
- 1 vault = 1 파일: vault 많아지면 복잡

**`mode` 필드** (Obsidian엔 없는 우리 고유):
```json
{"name": "default",      "mode": "personal", "owner": "user"}
{"name": "agent-output", "mode": "agent",    "owner": "hermes"}
```

→ 안정 궤도 후 단순화 가능 (현재는 보존).

---

## D9 — Python 어댑터 + scope

**문제**: 에이전트(Hermes/Claude/Codex)가 vault에 쓰려면:
- CLI 호출 (shell escaping, subprocess 오버헤드)
- 직접 파일 쓰기 (frontmatter/provenance 누락)
- 권한 제어 없음 (에이전트가 사람 vault 임의 수정)

**사용자 제약** (2026-06-25):
> "헤르메스의 각 에이전트들이 작업하고, 작업한 결과물을 Vault에 쓰고"

**결정**: `raven.agents` — Python 어댑터 + scope 강제 + provenance 자동.

```python
from raven.agents import Agent, AgentScope

hermes = Agent.named(
    "hermes-writer",
    scope=AgentScope(vault_names=("agent-output",), allow_delete=False),
)
hermes.vault("agent-output").write("content/x", body)
# → frontmatter에 자동:
#   agents:
#     - name: hermes-writer
#       timestamp: 2026-06-25T13:12:35
```

**핵심 차별점** (vs 단순 CLI):
- **scope 강제**: 에이전트가 허용 안 된 vault 쓰면 `PermissionError`
- **provenance 자동**: 누가/언제/왜 frontmatter에 기록
- **provenance 검색 가능**: `raven agent-list` (향후) → "어떤 에이전트가 뭘 썼나"
- **safety defaults**: `allow_delete=False` (명시적으로만 허용)

**기각한 대안**:
- shell wrapper: LLM이 매번 shell escape 필요 → 비효율
- 직접 파일 쓰기 (frontmatter 수동): 휴먼 에러
- 권한 없는 자유 쓰기: 사용자 데이터 안전성 ↓

---

## 영향 요약 (D7-D9의 결과)

| 컴포넌트 | 변경 |
|---|---|
| 코드베이스 구조 | `raven/{core,cli,api,agents}/` 신규 패키지 |
| 데이터 위치 | `~/vaults/<name>/` (외부) |
| CLI | `raven` 명령 9개 (vault/page/link/build/export) |
| GUI | vault picker + 동적 API fetch |
| HTTP API | 12 endpoints (FastAPI) |
| Python API | `Agent` + `AgentVault` (scope-based) |
| 문서 | raven-guide, raven-faq, raven-architecture |

---

## R7-R9 (M2 신규 리스크)

| # | 리스크 | 완화 |
|---|---|---|
| R7 | vault 위치 분실 (.registry.json) | 환경변수 오버라이드 + docs |
| R8 | 에이전트가 의도치 않게 사람 vault 수정 | `AgentScope.vault_names` 강제 |
| R9 | GUI stale cache (PWA) | `window.location.reload()` on vault switch |

---

## 다음 결정 후보 (D10+)

| 주제 | 결정 | 보류 이유 |
|---|---|---|
| Multi-user auth | Tailscale-only → Authentik? | 사용자 추가 시 |
| Vault 간 cross-link | `[[other-vault:foo]]` 문법? | 사용 패턴 관찰 필요 |
| 백업 cron | 일일 자동 백업 vs 수동 | 사용 패턴 관찰 필요 |
| vault별 SCHEMA override | 글로벌 vs per-vault? | 사용자 비전 확정 후 |
| MCP 서버 신규 | 기존 mcp/ 자산 활용 vs 신규? | 안정화 후 |

---

## 변경 이력

| 날짜 | 변경 | 이유 |
|---|---|---|
| 2026-06-25 | D7-D9 추가 | M2 multi-vault 재설계 |
| 2026-06-24 | D1-D6 (원본) | M1 결정 매트릭스 |
