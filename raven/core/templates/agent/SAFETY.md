---
title: Raven Agent Safety — 절대 금지 행동
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, raven, agent, safety, hard-prohibition]
audience: agent
confidence: high
---

# Raven Agent Safety — 절대 금지 행동

> **이 문서는 hard prohibition입니다.**
> 어기면 사용자 컨펌 없이 즉시 작업 중단 + 사용자에게 보고.

---

## 1. 절대 안 되는 것 (10가지)

### 🚫 데이터 무결성

| # | ❌ 안됨 | 이유 |
|---|---|---|
| 1 | `wiki.db` 직접 수정 (SQLite 핸들) | regenerable 인덱스 — `raven build`로 재생성 |
| 2 | `_meta/log.md` 수동 편집 | 자동 append — 직접 쓰면 lint 실패 |
| 3 | vault 외부 위치에 write (`/tmp/foo.md` 등) | SoT = vault 내부, 외부 = scope 밖 |
| 4 | `wiki.db`를 git에 commit | `.gitignore` 필수 — 사용자 정책 |

### 🚫 권한 / scope

| # | ❌ 안됨 | 이유 |
|---|---|---|
| 5 | `scope.allows()` 우회 — 직접 path 구성 | P0 패치로 read 경로도 slug 검증됨. 우회 시도 = 사용자 탐지 |
| 6 | scope 외 vault의 `vault(name)` 호출 | `PermissionError` 자동 발생 — 무시 ❌ |
| 7 | `allow_create=False` 인데 새 slug write | 미집행 발견됨 (codex audit). 시도 = 사용자 알림 |
| 8 | 다른 팀 vault 결정 위임 | 팀 경계 침범 = wiki-orchestrator 정책 위반 |

### 🚫 시스템 결정

| # | ❌ 안됨 | 이유 |
|---|---|---|
| 9 | 사용자 동의 없는 schema/네이밍 변경 | `_meta/system/SCHEMA.md` 영역 — architect 결정 |
| 10 | `_meta/system/*` 자동 수정 | agent 영역은 `_meta/agent/*` 만 |

---

## 2. 절대 안 되는 패턴 (vault 운영)

| ❌ 안됨 | ✅ 대안 |
|---|---|
| 결정 전 brainstorm을 vault에 쓰기 (raw는 메모장에) | 결정 확정 후 write |
| vault를 영구 저장소처럼 사용 | git 추적이 SoT, vault는 인덱스 |
| wiki-orchestrator에게 자기 팀 결정 위임 | 오케 자신이 결정 + write |
| vault 외부 송신 (외부 API 업로드) | vault 내부 + 사용자 read |
| 사용자 동의 없는 schema/네이밍 변경 | architect 위임 |
| 메모리에만 결과 보관 (휘발) | vault에 결정/lesson write (영구) |
| Phase 끝났는데 vault write 0건으로 보고 | 결정 1건 + lesson 1건이라도 write 후 보고 |

---

## 3. Path Traversal — P0 패치 이후 자동 차단

`server.py:210` GET, `agent.py:244` read/exists 모두 `_safe_path()` 통과.

**그래도 시도하지 말 것**:

| 입력 | 결과 |
|---|---|
| `get_page("wiki", "../escape")` | HTTP 400 (`invalid slug`) |
| `get_page("wiki", "~/.ssh-test")` | HTTP 400 |
| `Agent.read("../escape")` | `None` 반환 (예외 swallow) |
| `Agent.exists("~/.ssh-target")` | `False` 반환 |

**시도 자체가 사용자 알림 대상** — 정상 slug만 사용.

---

## 4. 시스템 vs agent 영역 침범 ❌

| 영역 | 당신이 read OK | 당신이 write OK |
|---|---|---|
| `content/<team>/*` | ✅ (scope 안) | ✅ (scope 안, 트리거 시점만) |
| `_meta/system/*` | ✅ (참조만) | ❌ 사용자 컨펌 필요 |
| `_meta/agent/*` | ✅ (당신의 가이드) | ⚠️ 본인 가이드 갱신은 사용자 컨펌 |
| `_meta/log.md` | ✅ | ❌ 자동 append만 |
| `_archive/` | ✅ (read) | ❌ archive 로직은 core만 |
| `wiki.db` | ❌ (직접 SQL ❌) | ❌ |
| vault 외부 | ❌ | ❌ |

---

## 5. 외부 위임 (codex / claude code) 시

당신이 다른 LLM을 위임 호출할 때 첨부할 system prompt 위치:

```
~/.hermes/profiles/wiki-orchestrator/prompts/raven-delegate.md
```

→ 위임 호출 1회 시 자동 로드 권장.

**위임자 절대 안 됨**:
- ❌ system prompt 없이 위임자 호출 → vault 규칙 무시 가능
- ❌ 5필터 (재사용/인수인계/근거/실패함정/공통규칙) 무시 write
- ❌ `raw/` 폴더 수정
- ❌ 외부 위임자에게 다른 팀 결정 위임

---

## 6. 작업 완료 전 5개 체크

- [ ] 결정 / lesson 있으면 `raven page new` 했는가?
- [ ] `raven lint run` 통과? (🔴 0)
- [ ] log.md 자동 append 확인? (`raven log list --tail 3`)
- [ ] 사용자에게 "어디 저장됐는지" 보고했는가?
- [ ] 다른 팀 결정 참조 시 wikilink (`[[...]]`)로 연결했는가?

---

## 7. 위반 발견 시

1. **즉시 중단** + 사용자에게 Telegram 보고
2. 변경한 파일 revert (`git checkout <file>`)
3. lesson 후보 작성 (사용자 컨펌 후 `content/<team>/lessons/<date>-<profile>`)
4. violation severity에 따라 scope 재발급 / 영구 박탈 (사용자 결정)

---

## 관련

- [README.md](README.md) — 진입점
- [TOOLS.md](TOOLS.md) — 인터페이스 + scope 규칙
- [WORKFLOW.md](WORKFLOW.md) — 트리거 / Phase 게이트
- `_meta/system/SCHEMA.md` — frontmatter 규약 (참조만)
