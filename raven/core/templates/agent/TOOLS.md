---
title: Raven Agent Tools — 인터페이스 사용법
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, raven, agent, tools, api]
audience: agent
confidence: high
---

# Raven Agent Tools — 인터페이스 사용법

> raven vault를 도구로 사용하는 4가지 인터페이스 + scope 규칙.
> **어떤 인터페이스를 쓰든 같은 scope 규칙이 적용됩니다.**

---

## 1. 4개 인터페이스 (상황별 선택)

| 인터페이스 | 형태 | 언제 쓰나 | 호출 예시 |
|---|---|---|---|
| **CLI** | shell subprocess | 사람이 보는 결과 출력, 단순 명령 | `raven page new foo --type concept` |
| **HTTP API** | FastAPI (:8765) | 원격 호출, GUI 백엔드 | `curl :8765/api/vaults/wiki/pages/foo` |
| **Python (raven.agents)** | in-process | 당신 같은 위임 에이전트 (PREFERRED) | `Agent.named("wiki-writer", scope="wiki").vault().write(...)` |
| **GUI** | React/Vite (:5173) | 사람 시각화, graph view | (직접 호출 안 함) |

→ **에이전트는 `raven.agents.Agent` 사용이 정답**. subprocess / curl은 우회이며 예외적.

---

## 2. 5개 기본 명령어 (가장 자주 씀)

```bash
# 페이지 생성 (frontmatter 자동)
raven page new content/foo \
  --title "Foo" --type concept --tags "core, ai"

# 페이지 조회 (frontmatter + body)
raven page get content/foo

# 페이지 목록 (filter: tag/type/has-contradictions)
raven page ls --tag harumoa --type rule

# vault 재빌드 (wiki.db 재생성) + lint 자동 실행
raven build

# 작업 이력 조회
raven log list --tail 5
```

---

## 3. Python API (Agent) — 권장

```python
from raven.agents import Agent, AgentScope

# scope 기반 — vault 외부 read/write 절대 ❌
agent = Agent.named(
    "wiki-writer",
    scope=AgentScope.single("wiki"),   # 또는 ("harumoa",) 등
)

# write — frontmatter 자동, log.md 자동 append
result = agent.vault("wiki").write(
    slug="content/foo",
    title="Foo",
    body="...",
    type="concept",
    tags=["core"],
)
# → result.ok / result.error / result.path

# read
body = agent.vault("wiki").read("content/foo")
exists = agent.vault("wiki").exists("content/foo")

# list
pages = agent.vault("wiki").list(type="rule", tag="harumoa")
```

---

## 4. Scope 규칙 (가장 중요)

| 규칙 | 설명 |
|---|---|
| `vault_names` | 에이전트가 접근 가능한 vault 이름 목록. `("<active>",)` 도 가능 |
| `allow_create` | 새 페이지 생성 가능 여부 |
| `allow_delete` | 삭제(=archive) 가능 여부 |
| `default_type` | write 시 type 미지정 시 기본값 |
| `default_tags` | write 시 자동 부착 태그 |

### 절대 금지 패턴

- ❌ `scope.allows()` 우회 — `_safe_path()` 검증을 우회하는 path 직접 구성
- ❌ scope 외 vault의 `vault(name)` 호출 → `PermissionError`
- ❌ `read()` / `exists()` 에 `..` / `~` / 절대 경로 slug → 자동 차단됨 (P0 패치 이후)
- ❌ shell 명령으로 직접 `.md` 파일 write (`echo > ...` 등)

---

## 5. 결과 처리 패턴

```python
result = agent.vault("wiki").write(slug="...", body="...")

if not result.ok:
    # 실패 보고 — 사용자에게 그대로 노출
    return {"ok": False, "error": result.error}

# 성공 — 4항목 보고 (사용자 정책)
return {
    "ok": True,
    "wrote": result.path,                    # 1) 어디 저장
    "references": ["content/harumoa/..."],  # 2) 참조한 파일
    "skipped": [],                          # 3) 저장 안 한 것 + 이유
    "next": "content/harumoa/backend-stack",# 4) 다음 작업자가 먼저 볼 것
}
```

---

## 6. 절대 사용하지 말 것

| ❌ 안됨 | 이유 |
|---|---|
| `Path.write_text()` 직접 호출 | scope/log 자동화 우회 |
| shell `cat` / `grep`으로 vault 탐색 | fs 직접 접근 = scope 무시 |
| GUI 호출 (HTTP 5173) | 사람용, agent 부적합 |
| curl로 HTTP API 직접 | 위임 모드에서는 raven.agents 정답 |

---

## 관련

- [README.md](README.md) — 진입점
- [WORKFLOW.md](WORKFLOW.md) — 트리거별 행동
- [SAFETY.md](SAFETY.md) — 금지 행동
- `_meta/system/SCHEMA.md` — frontmatter 규약 (참조만, 변경 ❌)
- `_meta/system/RULES.md` — 편집 5규칙 (참조만, 변경 ❌)
