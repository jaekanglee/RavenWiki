# raven v0.6.33 — Tier integrity lint #14 (Karpathy 3-Layer 자동 검증)

> **핵심**: Karpathy LLM Wiki의 3-Layer 분리를 lint 레벨에서 자동 검증. 사람이 실수로 vault 안에 Tier 1 문서 (OPERATIONS.md, agent/*, raven-policy.md) 를 복사해도 즉시 critical로 감지.

릴리스 일자: 2026-06-30
이전: v0.6.32 (filesystem watcher_fs)

---

## 한 줄 요약

`raven/core/lint.py`에 `#14 tier_integrity` check 추가. vault content/ 에 Tier 1 leak 패턴 (OPERATIONS.md / agent/ / raven-policy.md) 발견 시 critical로 보고. North star "모든 운영 결정의 자석" 자동화.

## 1. 변경 사항

### 1-1. `raven/core/lint.py` (lint #14 추가)

```python
TIER1_LEAK_PATTERNS = (
    "OPERATIONS.md",
    "agent/",
    "raven-policy.md",
)

def check_tier_integrity(vault: Vault) -> list[dict]:
    """#14 tier_integrity — Karpathy 3-Layer 분리 강제."""
    for fp in vault.content_root.rglob("*"):
        for pattern in TIER1_LEAK_PATTERNS:
            if pattern in str(fp.relative_to(vault.content_root)):
                yield critical issue
```

+ `run_all()` 에 `check_tier_integrity` 호출 추가 (총 14 check)

### 1-2. `tests/test_tier_integrity_lint.py` (신규, 2 tests + 1 skip)

1. lint 모듈에 `check_tier_integrity` 함수 존재
2. Tier 1 leak (OPERATIONS.md) 가 critical로 감지 — 임시 vault fixture로 검증
3. non-markdown (.py in content/) 감지 — 미구현 시 skip (별도 후속)

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **411 passed** (v0.6.32: 409 → v0.6.33: 411, +2) |
| vitest | **20 files / 102 tests + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |

## 3. North Star 자동화

이 lint #14는 v0.6.31에서 선언한 north star의 **자동 검증 장치**:
- 사람/에이전트가 vault 운영 중 Tier 1 leak → lint가 즉시 critical → 수정 강제
- README/wikisys-policy.md의 3-Layer 선언이 **코드 레벨에서 강제됨**
- Karpathy LLM Wiki 본질 (Layer 2가 vault, Layer 1은 raven internal) 이 회귀로 깨지는 것 방지

## 4. 후속 작업 (메모리 §next session)

4. `raven-delegate.md` 톤 한 줄 추가 (Antigravity 가이드)
5. Worker result 어댑터 (Codex JSON + Antigravity plain text 통합)
6. **Tier 1 leak 검증 hook** — pre-commit / pre-push hook으로 PR 단계에서 차단 (lint가 아니라 git hook)