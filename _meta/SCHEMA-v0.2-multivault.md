---
title: SCHEMA v0.2 — Multi-Vault 추가 사항
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, schema, raven]
sources: [_meta/SCHEMA.md]
confidence: high
---

# SCHEMA v0.2 — Multi-Vault 추가 사항

> 기존 [[SCHEMA]] (v2.4)는 **vault 내부** 규약.
> 이 문서는 **vault 외부** (vault 발견/메타/레지스트리) 스키마.

---

## Vault Root Schema

위치: `$WIKI_VAULTS_DIR/.registry.json` (기본 `~/vaults/.registry.json`)

```json
{
  "version": 1,
  "default": "<vault-name>",
  "vaults": {
    "<vault-name>": {
      "path": "<abs path>",
      "mode": "personal" | "shared" | "agent",
      "owner": "<who created/owns>",
      "created": "YYYY-MM-DD",
      "description": "<free text>"
    }
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `version` | int | ✅ | 스키마 버전. 현재 1 |
| `default` | str | ✅ | 기본 vault 이름. 비어있으면 첫 vault |
| `vaults` | dict | ✅ | name → meta |
| `vaults.<name>.path` | str | ✅ | vault 절대 경로 |
| `vaults.<name>.mode` | enum | ❌ (default: "personal") | personal/shared/agent |
| `vaults.<name>.owner` | str | ❌ (default: "user") | 누가 만들었나 (사람/에이전트) |
| `vaults.<name>.created` | date | ❌ | 생성일 (YYYY-MM-DD) |
| `vaults.<name>.description` | str | ❌ | 자유 설명 |

---

## Per-Vault Schema

위치: `<vault-root>/.vault.json`

```json
{
  "path": "<abs path>",
  "mode": "personal",
  "owner": "user",
  "created": "2026-06-25"
}
```

→ 레지스트리 항목의 subset (per-vault 자체 메타).
레지스트리와 동기화 책임은 `raven.core.registry`가 짐.

---

## Vault Directory Layout

```
<vault-root>/
├── .vault.json              ← per-vault 메타 (필수)
├── content/                  ← 사용자 마크다운 (필수)
│   ├── _template.md
│   ├── <slug>.md
│   └── <dir>/<slug>.md
├── _meta/                   ← 시스템 문서 (권장)
│   ├── SCHEMA.md
│   ├── RULES.md
│   └── ...
├── _archive/                ← 삭제 페이지 백업 (자동 생성)
│   └── <slug>-<timestamp>.md
├── wiki.db                  ← SQLite 인덱스 (자동 생성)
└── wiki.db.backup           ← DB 백업 (자동 생성)
```

**git 추적 권장**: `content/`, `_meta/`, `.vault.json` (+ `_archive/` 선택).
**git 추적 제외**: `wiki.db`, `wiki.db.backup` (regenerable).

---

## Frontmatter Schema (페이지)

기본은 [[SCHEMA]] §frontmatter 따름. M2에서 추가된 필드:

| 필드 | 타입 | 자동/수동 | 설명 |
|---|---|---|---|
| `agents` | list | **자동** (에이전트 write 시) | 작성 에이전트 provenance |

### `agents` 블록

```yaml
agents:
  - name: hermes-writer
    timestamp: 2026-06-25T13:12:35
    run_id: run-2026-06-25-001
    intent: 사용자 요청: hermes 위키 패턴 정리
```

| 하위 필드 | 설명 |
|---|---|
| `name` | Agent.named()의 이름 |
| `timestamp` | ISO 8601 (write 시점) |
| `run_id` | (선택) 호출자가 부여한 배치 ID |
| `intent` | (선택) 왜 이 페이지를 만들었나 |

**규칙**:
- 사람이 `raven page new`로 만든 페이지: `agents` 필드 없음
- 에이전트가 `av.write()`로 만든 페이지: `agents` 자동 삽입
- 사람이 편집 (overwrite): `agents` 보존 (누가 만들었는지 추적 유지)

---

## AgentScope Schema (Python)

에이전트 권한 정의 (Python API):

```python
@dataclass(frozen=True)
class AgentScope:
    vault_names: tuple[str, ...] = ()
    allow_create: bool = True
    allow_delete: bool = False
    default_type: str = "concept"
    default_tags: tuple[str, ...] = ("agent-output",)
```

| 필드 | 효과 |
|---|---|
| `vault_names=("agent-output",)` | agent-output만 접근 가능 |
| `vault_names=("<active>",)` | 현재 active vault에 바인딩 |
| `allow_create=True` | 새 페이지 생성 가능 (기본) |
| `allow_create=False` | 기존 페이지 overwrite만 |
| `allow_delete=False` | 삭제 거부 (기본 — 안전) |
| `allow_delete=True` | _archive로 이동 가능 |
| `default_type` | type 미지정 시 기본값 |
| `default_tags` | tags 미지정 시 기본값 |

---

## Environment Variables

| 변수 | 효과 | 기본 |
|---|---|---|
| `WIKI_VAULTS_DIR` | vaults root 위치 | `~/vaults` |
| `WIKI_VAULT` | 일시 active vault | (registry default) |

→ 두 변수 모두 **순수 override** (영구 변경 아님). 영구 변경은 `raven vault use <name>`.

---

## Schema Migration Policy

| 변경 종류 | 정책 |
|---|---|
| 신규 필드 (선택) | 추가 OK. 기존 vault는 default 값으로 동작 |
| 필드명 변경 | deprecated 표시 + alias 둘 다 허용 (v+0.1까지) |
| 필드 삭제 | major version bump + migration script |
| Vault 이름 규칙 | lowercase, kebab-case 권장 (영숫자 + `-`) |

현재 버전: **v1**. v2 이상은 호환성 깨는 변경이 필요할 때만.
