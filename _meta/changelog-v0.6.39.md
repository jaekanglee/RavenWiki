# raven v0.6.39 — VaultMeta 확장 (allow_tier1_leak, features) + Tier 1 leak lint 옵션화

> **핵심**: 사용자 north star (v0.6.37) 적용 — "vault 자유, 정책 강제 ❌, 단 opt-in 안전벨트는 사용자 책임".
> `VaultMeta`에 `allow_tier1_leak` (Tier 1 leak lint 옵트인) + `features` (LLM Wiki 패턴 등 feature flag) 필드 추가.
> Tier 1 leak lint #14 옵션화: 기본 critical, `allow_tier1_leak=True` 시 warning 강등.

릴리스 일자: 2026-06-30
이전: v0.6.38 (Lite bootstrap 프로파일화)

---

## 한 줄 요약

VaultMeta 2개 필드 추가 + Tier 1 leak lint 옵션화. **mode 필드는 손대지 않음** (display-only metadata로 이미 강등됨, 코드 분기 0건 확인).

## 1. 변경 사항

### 1-1. `raven/core/registry.py` VaultMeta 확장

신규 필드:
- `allow_tier1_leak: bool = False` — Tier 1 문서(OPERATIONS.md/agent/*/raven-policy.md)를 vault에 import하고 싶을 때 True
- `features: tuple = ()` — feature flags (예: `(("llm_wiki", True),)`). 사용자 자유.

`to_json()` / `from_json()` 모두 두 필드 직렬화/역직렬화.

`mode` 필드는 그대로 유지하되 **display-only metadata**임을 docstring에 명시.

### 1-2. `raven/core/lint.py` Tier 1 leak lint 옵션화

`check_tier_integrity()`:
- 기본 (allow_tier1_leak=False): **critical** (현재와 동일, 안전망 유지)
- 옵트인 (allow_tier1_leak=True): **warning** 강등 (사용자 안전벨트 해제 명시)

```python
severity = "warning" if getattr(vault.meta, "allow_tier1_leak", False) else "critical"
```

### 1-3. `tests/test_v0_6_39_metadata_options.py` (신규, 9 tests)

회귀 가드:
1. VaultMeta에 allow_tier1_leak 필드
2. VaultMeta에 features 필드 (tuple — frozen dataclass 해시 가능)
3. to_json이 allow_tier1_leak 직렬화 (True일 때만)
4. to_json이 features 직렬화 (비어있지 않을 때만)
5. from_json이 allow_tier1_leak 역직렬화 (default False)
6. from_json이 features 역직렬화 (default 빈 dict → tuple)
7. lint #14가 allow_tier1_leak 반영
8. 기본 vault는 여전히 critical (안전망 유지)
9. roundtrip 검증 (직렬화 → 역직렬화 보존)

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **443 passed, 1 skipped** (v0.6.38: 434 → v0.6.39: 443, +9) |
| test_v0_6_39_metadata_options.py | **9 passed** (신규) |
| 기존 vault (raven-dev) | ✅ 영향 없음 — VaultMeta 확장만, 기존 데이터 호환 |
| mode 필드 | ✅ 손대지 않음 (display-only metadata, 코드 분기 0건) |

## 3. 의도

**mode 처리 결정**: Codex/Antigravity 검토 + grep 결과 mode가 **코드 분기에 사용되지 않음** (단순 메타데이터). v0.6.39에서는 mode 필드 자체를 손대지 않음. 사용자 옵트인 시 `allow_tier1_leak`로 안전벨트 해제 + `features`로 LLM Wiki 패턴 활성화.

**Tier 1 leak 정책 결정**: Antigravity 추천 채택 — **기본 critical (안전망 유지), `allow_tier1_leak=True` 시 warning 강등**. 사용자 명시적 옵트인 책임.

## 4. 사용자 시나리오

### 시나리오 A — 기본 (안전망 ON)
```bash
# 아무것도 안 해도 됨 — Tier 1 leak 감지되면 critical
# raven build → critical → commit 차단
```

### 시나리오 B — Tier 1 문서 vault에 import (옵트인)
```bash
# .vault.json에 allow_tier1_leak 추가
echo '{"allow_tier1_leak": true}' > ~/Raven/my-vault/.vault.json
# 또는 raven meta sync --full --force (v0.6.40+ 예정)
# → Tier 1 leak 감지되어도 warning (commit 가능)
```

### 시나리오 C — LLM Wiki 패턴 활성화 (v0.7.0 가이드)
```bash
# .vault.json에 features 추가 (v0.7.0+ 가이드 예정)
echo '{"features": {"llm_wiki": true}}' > ~/Raven/my-vault/.vault.json
# → _meta/system/features.json 통해 raw/ log.md _meta/agents/ 활성화
```

## 5. 다음 단계

- **v0.6.40**: AgentScope resource scope (`allowed_paths` / `deny_paths`)
- **v0.7.0**: `docs/vault-patterns.md` — Karpathy LLM Wiki +α 본격 도입 가이드 (features 활용법, raw/ log.md convention, _meta/agents/ 도입)

## 6. 호환성

- ✅ **v0.6.38 vault**: VaultMeta 두 필드 default (False / 빈 tuple) → 기존 vault 정상 동작
- ✅ **mode 필드**: 손대지 않음 (display-only metadata 유지, 32+ 곳 호환)
- ✅ **Tier 1 leak lint**: 기본 critical 유지 (안전망) — 회귀 0
- ⚠️ **VaultMeta.to_json 시그니처**: `dict[str, Any]`로 타입 명시 (정확성, 동작 동일)