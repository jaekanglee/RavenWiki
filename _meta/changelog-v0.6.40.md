# raven v0.6.40 — AgentScope resource scope (allowed_paths / deny_paths)

> **핵심**: 사용자 north star (v0.6.37) 적용 — "vault 자유, 정책 강제 ❌, 단 opt-in 안전벨트는 사용자 책임."
> `AgentScope`에 path-level scope 추가. 기존 vault_names 격리는 그대로 유지 (vault-level), path-level은 **사용자 opt-in**.

릴리스 일자: 2026-06-30
이전: v0.6.39 (VaultMeta 확장 + Tier 1 leak lint 옵션화)

---

## 한 줄 요약

AgentScope에 `allowed_paths` / `deny_paths` (glob pattern) 추가. AgentVault.write()가 scope 위반 시 Result(ok=False) 반환. **기존 동작 100% 호환** (둘 다 비어있으면 path scope 무시).

## 1. 변경 사항

### 1-1. `raven/agents/agent.py` AgentScope 확장

신규 필드:
- `allowed_paths: tuple[str, ...] = ()` — glob 패턴 allowlist
- `deny_paths: tuple[str, ...] = ()` — glob 패턴 denylist (wins over allow)

신규 메서드:
- `allows_path(slug: str) -> bool` — fnmatch glob 매칭
  - deny_paths 매칭 → False (deny wins)
  - allowed_paths 비어있음 → True (현재 동작)
  - allowed_paths 매칭 → True
  - 미매칭 → False

### 1-2. `AgentVault.write()` path scope check

```python
if not self.agent.scope.allows_path(slug):
    return Result(
        ok=False,
        slug=slug,
        error=f"agent {self.agent.name!r} not allowed at path '{slug}' "
              f"(allowed_paths={...}, deny_paths={...})",
    )
```

### 1-3. `tests/test_v0_6_40_resource_scope.py` (신규, 8 tests)

회귀 가드:
1. AgentScope에 allowed_paths 필드
2. AgentScope에 deny_paths 필드
3. allows_path() 메서드 존재 (fnmatch 사용)
4. deny_paths 매칭 우선 (deny wins)
5. allowed_paths 비어있으면 모두 허용
6. allowed_paths 매칭 시 True
7. allowed_paths 미매칭 시 False
8. write()가 scope 위반 시 Result(ok=False) 반환

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **451 passed, 1 skipped** (v0.6.39: 443 → v0.6.40: 451, +8) |
| test_v0_6_40_resource_scope.py | **8 passed** (신규) |
| 기존 vault_names 격리 | ✅ 그대로 유지 |
| 기존 AgentVault.write | ✅ 둘 다 비어있으면 path scope 무시 (현재 동작 100% 호환) |

## 3. 의도

사용자 north star ("vault 자유, 정책 강제 ❌")와 데이터 안전 양립:

**vault-level 격리** (v0.6.39 이전):
- AgentScope.vault_names = ("harumoa-staging",)
- → 다른 vault에 write 거부
- → 동일 vault 내에서는 자유

**path-level 격리** (v0.6.40+, opt-in):
- AgentScope.allowed_paths = ("content/compiled/**", "content/claims/**")
- AgentScope.deny_paths = ("raw/**", "_meta/system/**")
- → 명시한 경로만 허용, 명시한 경로는 차단
- → 비어있으면 무시 (사용자 자유)

## 4. 사용자 시나리오

### 시나리오 A — 기본 (path scope 없음, 현재 동작)
```python
Agent.named("harumoa-writer", scope=AgentScope(vault_names=("harumoa-staging",)))
# → vault-level 격리만, path 자유
av.write("anything/here", body)  # OK
```

### 시나리오 B — path scope opt-in (LLM Wiki 패턴)
```python
Agent.named(
    "harumoa-compiler",
    scope=AgentScope(
        vault_names=("harumoa-staging",),
        allowed_paths=("content/compiled/**", "content/claims/**"),
        deny_paths=("raw/**", "_meta/system/**"),
    ),
)
# → compiled/claims만 write 가능, raw/system은 절대 불가
av.write("content/compiled/foo", body)        # OK
av.write("content/draft/foo", body)            # ❌ allow 미스매치
av.write("raw/articles/x", body)               # ❌ deny 매치
av.write("_meta/system/SCHEMA.md", body)       # ❌ deny 매치
```

### 시나리오 C — deny만 (allowlist 없이)
```python
Agent.named(
    "harumoa-safe-writer",
    scope=AgentScope(
        vault_names=("harumoa-staging",),
        deny_paths=("raw/**",),
    ),
)
# → 모든 곳 OK, 단 raw/만 차단
av.write("anywhere/x", body)        # OK
av.write("raw/articles/x", body)    # ❌ deny 매치
```

## 5. 다음 단계

- **v0.7.0**: `docs/vault-patterns.md` — Karpathy LLM Wiki +α 본격 도입 가이드
  - features.llm_wiki 활성화 시 raw/ log.md _meta/agents/ 패턴
  - AgentScope resource scope 활용 예시 (compiled/claims 자동 write)
  - allow_tier1_leak + Tier 1 leak lint 옵션화 활용

## 6. 호환성

- ✅ **v0.6.39 이전 코드**: AgentScope 두 필드 default = 빈 tuple → 기존 코드 정상 동작
- ✅ **기존 harumoa-writer 등 어댑터**: path scope 미사용 → 영향 없음
- ✅ **MCP / CLI / API**: 영향 없음 (Agent adapter 내부 변경만)
- ⚠️ **API consumers**: write() Result error 메시지 형식 변경 가능 (scope 위반 시)