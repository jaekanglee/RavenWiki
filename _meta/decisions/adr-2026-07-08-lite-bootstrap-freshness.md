---
title: Lite bootstrap freshness 가드 (A+B 조합)
created: 2026-07-08
type: rule
tags: [adr, lite-bootstrap, freshness, layer-2, agent-autonomy]
audience: agent
confidence: high
status: current
related:
  - _meta/decisions/adr-2026-07-08-agent-issue-autonomy.md
  - _meta/decisions/adr-2026-07-06-stale-update-isolate-loop.md
aliases: [adr-lite-bootstrap-freshness]
---

# ADR: Lite bootstrap freshness 가드 (A+B 조합)

> **BLUF**: agent가 stale한 lite bootstrap(SCHEMA/PROJECT-WORKFLOW.md) 지침을 기억하고 작업하는 문제를 막기 위해, **(A) 세션 시작 가드 + (B) 도구 호출 hook** 2중 가드를 도입한다. 강제 read는 하지 않고, **stale_detect-style 경고 + log.md audit + 사람 알림 (선택)** 으로 운영한다. 강제 read = 사용자 원칙 "매번 필수 ❌" 위배.

## 1. 맥락 (Context)

### 1.1 문제

Lite bootstrap 3종 (SCHEMA.md / PROJECT-WORKFLOW.md / log.md)이 갱신되어도:
- agent는 메모리에 캐시된 옛 정책 기억
- 다음 세션에서 _meta/agents/ 새로 읽지 않고 stale 적용
- 사람 운영자 입장에선 "지침 업데이트했는데 에이전트가 옛날 거 쓰네" 발생

### 1.2 사용자 north star

- "매번 사람 명시 ❌" (사용자 메모리 Decision fatigue)
- "에이전트 자율성 ↑" (v0.7.113 합의)
- "사람 curation 옵션" (v0.7.107 Layer 2)

### 1.3 기존 인프라

- `wiki_get_guide_diff(kind)` (v0.7.95+): 설치 템플릿 vs vault 부속 unified diff
- `wiki_stale_detect()` (v0.7.106 ADR): stale 후보 + evidence + suggested_action
- `_meta/agents/` lite bootstrap (v0.7.65+): vault 진입 시 자동 주입

### 1.4 충돌 분석

| 권 | 내용 | 충돌? |
|---|---|---|
| 사용자 원칙 "매번 필수 ❌" | 강제 read = X | ✅ 해소 |
| Layer 2 north star | 사람 curation 옵션 | ✅ 정합 |
| v0.7.113 type:issue 자율성 | agent가 옛 정책 기억하면 무효 | ✅ 정합 |
| 사용자 선호 single-digit reply | 알림 spam ❌ | ✅ 가드 (silent warn 기본) |

## 2. 결정 (Decision)

### 2.1 A + B 2중 가드

```yaml
A: 세션 시작 가드 (Pass 1)
  - agent가 첫 wiki_search/wiki_update 호출 시:
    - 서버가 응답에 `_meta/agents/{SCHEMA,PROJECT-WORKFLOW}.md` SHA256 hash 첨부
    - agent가 캐시한 hash와 다르면:
      - [ ] log.md audit append (auto-log)
      - [ ] tools/list 응답 또는 첫 호출 응답에 "freshness: stale" 헤더
      - [ ] agent는 다음 wiki_search 1회 강제 (강제가 아니라 cache invalidation)
    - agent가 캐시 hash 없거나 무시하면 다음 세션으로 carry

B: 도구 호출 hook (Pass 2)
  - **MCP HTTP-only 정책 (v0.7.81+)**: X-Guide-Hash 헤더는 MCP HTTP transport 전용.
    stdio 미지원 — stdio 클라이언트는 헤더 전달 불가하므로 wiki_check_freshness()
    도구 호출로 동등 진단. (PWW §1.2 — "HTTP localhost만 지원")

  - write 도구 (wiki_update / wiki_ingest / wiki_archive) 호출 시:
    - 서버가 hash 재계산 + 응답 헤더에 다시 첨부 (X-Guide-Hash echo)
    - 캐시 hash와 다르면 응답 body 안에 `freshness_warning` 필드 첨부
    - agent는 인지 + 다음 wiki_update에 cache 갱신
    - 강제 reject ❌ (사용자 원칙 "매번 필수 ❌")

  - read 도구 (wiki_search / wiki_get_page / wiki_lint) 호출 시:
    - 동일하게 X-Guide-Hash 헤더 echo
    - 단 freshness_warning은 optional (성능 영향 최소화)
```

### 2.2 silent warn 기본 + 사람 알림 옵션

```yaml
# 기본 동작
agent: log.md audit + 다음 호출 cache 갱신 (silent)
사람: 알림 없음 (inbox spam 방지)

# 선택적 알림 (사용자 turn 명시 시)
"지침 갱신 알림 켜줘" → Telegram/Home 채널에 "lite bootstrap 갱신됨" 발송
기본 OFF — 메모리/시간 낭비
```

### 2.3 hash stamp 자동 관리

```yaml
# _meta/agents/.guide-version (자동 stamp, Tier 2 Raven 제품 영역)
SCHEMA.md: <sha256>
PROJECT-WORKFLOW.md: <sha256>
log.md: <line_count>:<mtime>     # append-only라 hash 대신 줄 수/mtime

# stamp 갱신 트리거 (Raven 제품 hook만 — 에이전트 write 금지)
- raven build                     # 자동 stamp 갱신
- raven meta sync (Lite bootstrap) # 사람 운영자가 명시 실행
- 직접 _meta/agents/* 수정 시 (사람 운영자, 그리고 raven build가 다음 호출에서 stamp 재계산)

# 에이전트 write ❌ — ADR §2.6 명시. _meta/agents/ Tier 2 영역이지만 .guide-version은
# Raven 제품 hook만 갱신. 에이전트가 직접 stamp를 덮쓰는 구조적 여지를 차단.
```

### 2.4 MCP 도구 변경

```yaml
# 신규: wiki_check_freshness(vault, kind?)
wiki_check_freshness(vault="raven-dev", cache_hash=None)
  → {
    "vault": "raven-dev",
    "guides": {
      "SCHEMA": {
        "vault_hash": "abc123...",
        "cache_match": false,           # cache_hash=None이면 None (graceful)
        "lines": 457,
        "exists": true,
      },
      "PROJECT-WORKFLOW": { ... },
      "log": { "lines": 1234, "mtime": 1718000000.0, "exists": true },
    },
    "stamp": { "SCHEMA": "abc123", "PROJECT-WORKFLOW": "def456" },
    "stale": true,
    "stale_kinds": ["SCHEMA", "PROJECT-WORKFLOW"],
  }

# 기존 도구 응답 헤더 추가 (X-Guide-Hash, X-Guide-Stale)
# 백엔드: API/MCP 도구 호출 응답에 metadata 첨부
```

### 2.5 SCHEMA / PWW 갱신

- `_meta/SCHEMA.md` §13 lint 추가: **#19 guide freshness** — type=issue 무관 vault-wide lint
- `_meta/SCHEMA.md` §lint 표: #19 = info 등급 (조용히 알림)
- `raven/core/templates/agent/PROJECT-WORKFLOW.md` §1.1: `wiki_check_freshness` 신규 도구 표 추가
- `raven/core/templates/agent/PROJECT-WORKFLOW.md` §8.5: "에이전트 스스로 판단/기억할 영역"에 "지침 freshness 인지" 항목 추가
- `_meta/agents/*` 동기화

### 2.6 변경 안 하는 것

- **강제 read** ❌ (사용자 원칙 "매번 필수 ❌")
- **Telegram/Home 자동 알림** ❌ (기본 OFF, 명시 요청 시만)
- **agent 인증서 / 토큰** ❌ (단순 hash 비교)
- **`type: decision` 권한** = 사람 1차 그대로
- **Tier 1 (`_meta/system/`, `_meta/agents/`) write 가드** = 기존 정책 유지 (hash stamp는 `_meta/agents/.guide-version`로 Tier 2 영역에 둠)

## 3. 결과 (Consequences)

### 3.1 긍정

- agent가 stale 지침 기억하는 문제 자연 해소 (silent warn)
- 사람 운영자 inbox spam ❌
- 사용자 원칙 "매번 필수 ❌" 정합
- v0.7.113 type:issue 자율성과 정합 (옛 §7.1 자동 차단)
- 모든 vault에 공통 적용 (Lite bootstrap 켠 vault)

### 3.2 부정 / 리스크

- agent가 freshness_warning 무시하면 옛 정책 유지 — **audit log가 마지막 안전망** (사람 turn에서 log.md 보고 인지)
- hash stamp 자동 갱신 안 되면 false stale — `_meta/agents/.guide-version` 빌드/sync hook 필요
- silent warn이 너무 silent 하면 문제 — **log.md audit이 충분한 가시성** (사람이 log tail 확인 시 인지)

### 3.3 회귀 가드 (3종)

```yaml
# 1. SCHEMA.md §lint #19 guide freshness 정의 (info 등급)
# 2. PROJECT-WORKFLOW.md §1.1 wiki_check_freshness 도구 표
# 3. 테스트 — vault 부속 hash 변경 시 freshness_warning 첨부 확인
```

## 4. 다음 단계

```yaml
1. _meta/decisions/adr-2026-07-08-lite-bootstrap-freshness.md (본 ADR) ✅
2. raven/core/lint.py — #19 check_guide_freshness 신규 (info)
3. raven/mcp/tools/guide.py — wiki_check_freshness() 신규 도구
4. raven/api/server.py — write/read 도구 응답에 X-Guide-Hash 헤더 추가
5. raven/core/templates/agent/{SCHEMA,PROJECT-WORKFLOW}.md 갱신
6. raven/core/registry.py — vault.build() 시 _meta/agents/.guide-version 자동 stamp
7. _meta/agents/* 동기화
8. tests/test_mcp_check_freshness.py + tests/test_lint_guide_freshness.py 회귀 가드
9. _meta/changelog-v0.7.114.md
10. 두-repo commit + raven-dev active.md
