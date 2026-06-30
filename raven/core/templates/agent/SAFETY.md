---
title: Raven Agent Safety — 절대 금지 행동
created: 2026-06-30
updated: 2026-06-30
type: rule
tags: [system, meta, raven, agent, safety, hard-prohibition]
audience: agent
confidence: high
---

# Raven Agent Safety — 절대 금지 행동

> **이 문서는 Hard Prohibition(강한 금지령)입니다.**
> 이를 위반할 시 즉시 에이전트의 작업이 중단되며 사용자에게 보고됩니다.

---

## 1. 절대 금지 항목 (10가지)

### 🚫 데이터 무결성

| # | ❌ 절대 금지 | 이유 |
|---|---|---|
| 1 | `wiki.db` 직접 수정 (SQLite 직접 조작) | DB는 파생 인덱스입니다. 무조건 `wiki_update` MCP 툴이나 `raven build`로 자동 갱신해야 합니다. |
| 2 | `log.md` 수동 편집 | `log.md`는 엔진이 자동 기록(append)합니다. 직접 쓰면 린트 에러가 발생합니다. |
| 3 | Vault 외부 위치에 파일 생성/수정 (`/tmp/` 등) | 지식의 모든 소스(SoT)는 오직 Vault 내부에 격리되어야 합니다. |
| 4 | `wiki.db`를 git에 commit 시도 | 로컬 캐시 인덱스이므로 반드시 `.gitignore` 처리되어야 합니다. |

### 🚫 권한 / Scope / 큐레이션

| # | ❌ 절대 금지 | 이유 |
|---|---|---|
| 5 | 보호 경로 검증 우회 시도 | `wiki_update` 는 `raw/`, `_meta/`, `log.md` 보호 규칙과 safe-path 검증을 강제합니다. |
| 6 | 허용되지 않은 Vault를 대상으로 MCP 툴 호출 | 권한 없는 Vault 접근 시 `PermissionError`가 발생하며 즉시 경고 처리됩니다. |
| 7 | 쓰기 권한이 비활성화된 상태에서 write 시도 | `--mode read` 상태에서 `wiki_update`, `wiki_ingest` 호출은 거부됩니다. |
| 8 | 다른 프로젝트/팀의 중요 결정을 동의 없이 수정 | 팀 간의 협업 바운더리를 무단 침범해서는 안 됩니다. |
| 9 | **사용자 승인(Confirm) 없는 파괴적 큐레이션** | 문서의 대량 병합, 리네임, `wiki_delete` 툴을 통한 아카이브는 반드시 사용자 컨펌 후 실행해야 합니다. |

### 🚫 시스템 결정

| # | ❌ 절대 금지 | 이유 |
|---|---|---|
| 10 | 사용자 동의 없는 Schema/네이밍 변경 | `_meta/system/SCHEMA.md`는 시스템 아키텍처 규칙이므로 수동 편집할 수 없습니다. |
| 11 | `_meta/system/*` 문서 임의 수정 | 에이전트가 관리하는 설정은 오직 `_meta/agents/*` 뿐입니다. |

---

## 2. 절대 안 되는 패턴 (Vault 운영)

| ❌ 안됨 | ✅ 대안 |
|---|---|
| 결정이 확정되지 않은 브레인스톰/메모를 Vault에 직접 쓰기 | 생각 정리는 임시 메모(raw)에서 하고, 확정된 결정 사항만 작성 |
| Vault를 일시적인 임시 보관함처럼 다루기 | Git으로 버전 관리되는 영구적인 compounding 지식 창고로 취급 |
| 작업을 완료했으나 Vault에 아무런 기록도 남기지 않기 | 결정, 배운 점, 혹은 일지(journal) 중 최소 1건 이상 기록 후 보고 |
| 외부 네트워크나 API로 Vault의 지식을 무단 반출하기 | 모든 데이터는 로컬 Vault 내부에서만 처리 및 관리 |

---

## 3. Path Traversal — 자동 차단

모든 MCP 툴 호출 및 API 호출은 내부적으로 `_safe_path()` 함수에 의한 엄격한 검증을 거칩니다.

**절대 시도하지 마십시오:**
* `..` 이나 `~` 등을 포함하여 Vault 경계 밖의 파일(Path Traversal)을 조회하거나 조작하려 시도하는 행위
* 상위 폴더 탈출을 시도하는 절대 경로 강제 지정

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
