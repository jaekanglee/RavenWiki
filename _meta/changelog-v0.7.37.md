# raven v0.7.37 — vault 횡단 연결(read-only federation) + 도메인 격리(agents opt-in policy)

> **핵심**: 사용자가 여러 vault를 운영할 때 **"각 vault는 자기 도메인만, 그러나 서로 참조는 싶다"** 라는 두 마디 욕구를 한 사이클에 둘 다 해결합니다. ① `.vault.json` 에 `agents` allowlist를 opt-in 박으면 — **그 vault는 다른 actor의 write를 거부**합니다 (도메인 격리). ② `/api/crosslink/{name}` 신설로 — **현재 vault에 없는 slug를 등록된 다른 vault에서 read-only로 찾아**줍니다 (위키링크 횡단). 두 기능은 짝 — ① 이 write-side 보호, ② 가 read-side 발견.

릴리스 일자: 2026-07-01
이전: v0.7.36

---

## 1. 배경 — 사용자 의도

> 사용자가 3개 vault(`harumoa`, `hermes-infra`, `raven-dev`)를 각자 별 도메인으로 운용 중. "각자 도메인 유지하되 vault 경계를 넘는 연결은 가능해야"라는 두 마디 욕구가 v0.7.37의 출발점. antigravity로부터 받은 plan은 *"전부 통합"*이라 사용자 의도와 정면 충돌. **연결과 격리를 동시에** — 그게 v0.7.37의 구조.

기존 vault들에게는 **행동 변화 0**. 두 기능 모두 opt-in:
* `.vault.json` 에 `agents` 키 없음 → 모든 actor write 허용 (현재 동작 유지)
* federation endpoint가 호출되지 않으면 어떤 read도 변하지 않음

---

## 2. 변경 사항

### 2-1. `.vault.json` — `agents` 필드 허용 (v0.7.37+)

* **`raven/core/registry.py`**:
  * `VaultMeta` 데이터클레스에 `agents: tuple = ()` 필드 신설 (`@dataclass(frozen=True)` 호환).
  * `from_json` 정규화: `data["agents"]` 가 list/tuple 이면 `tuple(sorted(str(a) for a in agents_raw))`. 누락/잘못된 타입이면 빈 튜플 — **opt-in 표면**.
  * `to_json` 직렬화: agents가 비어있으면 JSON 에 미포함 (기본값 미노출). 1개 이상이면 `list(self.agents)` 정렬된 형태로 저장.
* `.vault.json` 예시 (`hermes-infra` 같은 격리가 필요한 vault):
  ```json
  {
    "path": "/Users/jaekanglee/Raven/hermes-infra",
    "mode": "personal",
    "owner": "user",
    "agents": ["default", "teambuilder", "design-spec-orchestrator"]
  }
  ```

### 2-2. `Vault.write_allowed_for(actor)` — write gate 헬퍼

* **`raven/core/vault.py`**:
  * `Vault` 클래스에 `write_allowed_for(actor: Optional[object]) -> bool` 메서드 추가.
  * 정책:
    * `meta.agents` 비어있으면 **모든 actor 허용** (back-compat).
    * `meta.agents` 정의돼 있고 actor id(`str`/`dict['name']`/`.name`)가 그 안에 있으면 **허용**.
    * 정의돼 있고 actor id 가 없으면 **거부**.
  * 정상 actor 정규화: `None → "anonymous"`, `str → 그대로`, `dict → str(name)`, 객체 → `str(getattr(o, 'name', 'anonymous'))`.
* **read-only 정책**: `write_allowed_for` 는 **오직 write** 만 gating. `search`, `get_page`, `graph`, `lint`, `log`, `wiki_*` read tools 는 절대 영향 안 받음. federation 의 자유 보장.

### 2-3. `contracts.write_page` — gate 강제 (write-side 의 단일 진입점)

* **`raven/core/contracts.py`** (`write_page()` 첫 단계 — slug 정규화보다 먼저):
  * `vault.write_allowed_for(actor)` 호출 결과 `False` 라면 `WriteResult(ok=False, ...)` 즉시 리턴 — 파일 시스템 0 건의 mutation.
  * 거부 결과 메시지: `"actor 'eve' not in vault's \`agents\` allowlist (...)"` + 사람의-가독 메시지 1 줄.
  * `actor` 미지정(`None`)도 `"anonymous"` 로 평가되므로 기본 write 는 거부 (opt-in 의 의도대로).
* v0.6.2+ 의 *write-path 단일화* 약속 유지 — 이 gate 는 **모든 write 호출 경로** (CLI/API/MCP) 에 자동 적용.

### 2-4. `/api/crosslink/{name}` — vault 횡단 wikilink 해결 (read-only federation)

* **`raven/api/server.py`**: 신규 endpoint `POST /api/crosslink/{name}`, payload `{slug: str}`.
* 동작 흐름:
  1. **origin vault 우선** — `name` 의 vault 안에 slug 가 있으면 `{found_in: "self", ...}` 리턴 (short-circuit).
  2. **federation** — origin 에 없으면 등록된 다른 vault 들을 registry.json 키 순서로 순회.
     * 정확히 1곳에만 slug 존재 → `{found_in: "<vault-name>", slug, title}`.
     * 여러 vault 가 같은 slug 보유 → **`{found_in: "ambiguous", candidates: [{vault, title}, ...]}`** — dashboard 에서 사용자 disambiguation (silent pick ❌).
     * 0곳 → `{ok: False, not_found: True}`.
  3. **best-effort** — vault 가 깨졌거나 path 부재 시 silent skip (federation 은 500 으로 **전체** 떨어지면 안 됨). 한 vault 가 unhealthy 라도 lookup 결과는 살아있는 vault 만 반영.
* slug 정규화: `shared` → `content/shared` (raven 표준 `normalize_prefix` 사용 — write-side 와 동일한 룰).
* **strictly read-only** — 어떤 vault 의 파일도 read 만, write/log/lock 모두 touch 안 함. 사용자가 federation endpoint 만 호출했다고 vault 에 side-effect 가 생기면 안 됨.

### 2-5. 회귀 가드 (자동 검증)

* **`tests/test_v0_7_37_agents_policy.py`** (신규, 13 케이스):
  * `VaultMeta.agents` round-trip / 정규화 (정렬 + str coerce).
  * `Vault.write_allowed_for` 분기 (모든 actor 허용/거부/admit, dict/object name 추출).
  * `contracts.write_page` end-to-end: 정책 없는 vault → 통과, 정책 있는 vault + unlisted actor → `WriteResult.ok=False` (filesystem 0 mutation), anonymous 거부.
  * 기본 모드(vaults without policy) 회귀: 백-호환 OK 검증.
* **`tests/test_v0_7_37_crosslink_federation.py`** (신규, 6 케이스):
  * self short-circuit / federation to single other / not-found / ambiguous (다중 후보) / read-only side-effect-free (file tree diff 비교, registry.json diff 비교) / unknown origin vault 는 fallback 으로 federation 도는 동작.
  * monkeypatch 가 WIKI_VAULTS_DIR 만 바꾸면 충분 — registry singleton 은 fresh factory 임을 test fixture 에 명시.

---

## 3. 다음 사이클 후보 (deferred)

* **Dashboard wikilink wire-in** — `MarkdownView.tsx` (혹은 `wikilink.ts`) 가 wikilink 클릭 시 `/api/crosslink` 을 먼저 확인하고 federated target 으로 navigate. 현재 API 만 있고 dashboard 클라이언트는 미연결. 사용자가 federation 이 실제로 필요함을 느끼면 다음 사이클에서 ~30~50줄 추가로 wire-in.
* **`agents` CLI surface** — `raven vault register <name> --allow-actor <id> [--allow-actor ...]` 같은 헬퍼. 사용자가 vault 만들 때 직접 policy 박기 편해짐. 우선순위 낮음 (사용자 수동으로 .vault.json 직접 편집 가능).

---

## 4. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `pytest tests/test_v0_7_37_agents_policy.py` | **13 passed** | 신규 가드 |
| `pytest tests/test_v0_7_37_crosslink_federation.py` | **6 passed** | 신규 가드 |
| `pytest tests/` 전체 | **525 passed, 2 skipped** | v0.7.36 = 519 → +19 신규 (13+6) — 추가 회귀 없음 |
| `npx tsc -b --noEmit` (dashboard) | **Success** | 출력 0 줄 |
| federation E2E (로컬) | **Success** | 2 vault + ambiguous 시나리오 직접 호출 검증 |
| 사용자 기존 vault 데이터 | **0 건 변동** | vault 별도 등록/해제/이동 없음, 정책 미정의 vault 는 자동으로 permissive |

---

## 5. 사용자 영향 (v0.7.37 사이클이 가능케 하는 것)

* **"다른 vault 의 문서로 손쉽게 가고 싶다"** — `/api/crosslink/{name}` 호출 한 번으로 끝. 동일 slug 가 여러 vault 에 있으면 후보 리스트를 돌려주므로 사용자가 의식적으로 선택.
* **"내 vault 에 다른 도메인 에이전트가 멋대로 쓰지 못하게"** — `.vault.json` 에 `agents` 리스트 박기. 기존 `write_page()` 게이트가 자동 적용 — 추가 코드 작성 0.
* **기존 vault** — `agents` 미정의 = 모든 actor 허용 (v0.7.36 이하 동작과 100% 동일). 채택은 본인 결정.

---

## 6. 다음 단계

* v0.7.38+: (후보) Dashboard federated wikilink wire-in (의미 ① 의 user-visible 마무리).
* 또는 사용자가 다음 사이클 다른 우선순위를 고를 수 있습니다.
