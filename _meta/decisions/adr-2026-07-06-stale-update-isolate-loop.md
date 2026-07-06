---
title: "ADR: 에이전트 스테일 갱신·격리 루프 — 정의·권한·도구·테스트 4축"
date: 2026-07-06
status: accepted
audience: agent, human
supersedes: null
related:
  - AGENTS.md §0.5 (North Star: 사람 1차 사용자 + 원문 보존 + 증분 누적)
  - AGENTS.md §6 (저장 4신호: 재사용성·인수인계·맥락·실패기록)
  - AGENTS.md §3 (사용자 3종: 사람 / 단일 에이전트 / 멀티 에이전트)
  - AGENTS.md §6 (PlanNote 금지 — 결정과 작업의 분리)
  - docs/evaluations/2026-07-04-raven-architecture-evaluation.md (A#0, 테마 5)
  - docs/evaluations/2026-07-04-raven-product-evaluation.md (P0#0, §3.1, §6 #0)
  - docs/evaluations/2026-07-04-sibling-summary.md (자매 정합 표)
related_changelog: v0.7.68 부록 C (2026-07-06 평가 보완 v2)
type: rule
---

# ADR — 에이전트 스테일 갱신·격리 루프 정의·권한·도구·테스트 4축

> **한 줄**: Raven vault의 모든 페이지는 **stale / current / contested / archived 4상태** 명시적 상태 머신을 갖고,
> **에이전트는 stale 발견 → 갱신(부분 overwrite + provenance) 또는 격리(archive 이동) 액션을 자율 실행**한다.
> 본문 대규모 재작성은 ❌, 원문 보존 + 증분 누적만 ⭕. 이 루프의 **정의·권한·도구·테스트 4축**이 모두 갖춰질 때
> 사용자 north star (2026-07-06 확인)가 실행된다.

---

## 0. 맥락 (Context)

2026-07-04 평가에서 두 문서 모두 **에이전트가 vault를 자율 정합화한다**는 제품 정체성의 핵심 시나리오를 평가 누락했음이 발견됐다. 사용자 north star 재확인 (2026-07-06):

> "사람이 최초 작성한 문서를, 에이전트가 스테일/모순/링크깨짐을 발견하여 갱신(부분 overwrite + provenance) 또는 격리(archive 이동) 액션으로 vault를 최신 정합화 상태로 유지한다. 본문 대규모 재작성은 ❌, 원문 보존 + 증분 누적만 ⭕."

**현실 (v0.7.66 시점)**:
- `wiki_update`(MCP/CLI)는 부분 overwrite 가능하나 **frontmatter 오염 결함** 동반(평가 P0#3).
- `archive` 액션은 **CLI만 노출**, MCP에서 호출 불가 → 에이전트가 격리 트리거 못 함.
- `wiki_lint` #7 stale 룰은 존재하나 **상태 머신 부재** — 룰이 무엇을 보고 어떤 상태로 전이해야 하는지 미정의.
- 시나리오 테스트 0건 — "90일 stale 자동 감지 → 갱신" / "사실 변경 → 재검증" 루프 미실증.
- ADR 부재 — 평가 문서가 "권한 불명"이라 지적하나, 결정 자체가 없음.

이 ADR은 위 4축(정의·권한·도구·테스트)을 **결정**한다. 구현은 별도 사이클.

---

## 1. 결정 (Decision)

### 1.1 정의 (Schema) — 4상태 명시

모든 vault 페이지는 frontmatter `status:` 필드로 다음 4상태 중 하나를 갖는다:

| 상태 | 의미 | 진입 트리거 | 검색·링크 노출 |
|---|---|---|---|
| `current` | 사실 검증됨, 권위 있음 | 사람 최초 작성, 또는 에이전트 갱신 완료 | ✅ 정상 |
| `stale` | 90일+ 미검증 또는 사실 변경 의심 | lint #7 자동 감지 | ⚠️ 헤더 경고, 본문은 노출 |
| `contested` | 다른 페이지와 모순 발견 | lint #5 (모순 룰) 자동 감지 | ⚠️ 헤더 경고, 양쪽 cross-link |
| `archived` | 격리됨, 더 이상 활성 페이지 아님 | 사람/에이전트 격리 액션 | ❌ 검색·그래프 제외, 전문은 `archive/<date>/<slug>.md` 보존 |

- **전이 규칙**: current ↔ stale (검증 결과에 따라), stale → archived (사람 승인 시 또는 자동 격리 정책 만족 시),
  current ↔ contested (모순 발견/해소 시).
- **전이 기록**: 모든 상태 전이는 `agents:` 리스트에 `{actor, action: "stale_detected"|"updated"|"archived"|"revalidated", at, evidence}` 1줄 append.
- **파일 위치**: 상태 정의는 `_meta/SCHEMA.md` (사용자 vault 측 — Lite bootstrap 2종 중 1개) 의 frontmatter 명세에 추가.

### 1.2 권한 (Authority) — 5가지 액션 매트릭스

| 액션 | 사람 | 단일 에이전트 (MCP) | 멀티 에이전트 |
|---|---|---|---|
| 1. `wiki_lint` (stale 후보 감지) | ✅ | ✅ | ⚠️ read-only 권장 |
| 2. `wiki_stale_detect` (후보 목록 + evidence 반환) | ✅ | ✅ | ⚠️ read-only 권장 |
| 3. `wiki_update` (부분 overwrite + provenance 기록) | ✅ | ✅ | ⚠️ 사용자 책임 (ADR §3.2 충돌 — locks 없음) |
| 4. `wiki_archive` (이동 + frontmatter stamp) | ✅ (CLI + Dashboard) | ✅ (MCP 신규) | ⚠️ 사용자 책임 |
| 5. `wiki_revalidate` (stale → current 전이, evidence 기록) | ✅ | ✅ (stale → current만) | ⚠️ 사용자 책임 |

- **금지 행위**: 본문 50%+ 재작성 (`wiki_update`의 `content` 길이가 기존 본문 1.5배 초과 시 거부 + 경고). 이건 "대규모 재작성 ❌" north star의 실행 가드.
- **contested 전이**: 자동 금지 — 사람이 명시적으로 `contested: true` 박거나, lint #5가 cross-link 증거 제시 시에만.
- **archived → current 복귀**: 사람 승인 필수 (에이전트 자율 복귀 ❌).

### 1.3 도구 (Tooling) — MCP 신규 2개 + 기존 1개 확장

**신규 도구**:

```yaml
# raven/mcp/tools/stale.py
wiki_stale_detect:
  input:
    vault: str
    age_threshold_days: int = 90
    include_self_verified: bool = false
  output:
    candidates: [
      {slug, last_verified_at, status, evidence, suggested_action: "update"|"archive"|"revalidate"}
    ]
  side_effects: none (read-only)

wiki_archive:
  input:
    vault: str
    slug: str
    reason: str  # "stale_over_threshold"|"user_request"|"factual_obsolete"
    actor: str
    dry_run: bool = false
  output:
    archived_path: str  # "<vault>/archive/<YYYY-MM-DD>/<slug>.md"
    source_frontmatter_stamped: bool  # archive 원본의 frontmatter에 archived_at + reason 기록
  side_effects: 파일 이동 + 원본에 stamp 추가 (idempotent — 이미 archived면 no-op)
  guards:
    - slug validate (path traversal 차단)
    - FileLock 적용 (core/lock.py의 FileLock과 동일 경로 잠금)
    - provenance: archive 액션도 agents: 리스트에 기록
```

**기존 도구 확장**:

```yaml
wiki_update:
  added_check: content 길이가 기존 본문 1.5배 초과 시 400 + 경고 (대규모 재작성 가드)
  added_param: evidence: str  # 갱신 사유 (예: "new source: <url>") — provenance 강화
  added_param: revalidate: bool = false  # true면 status: stale → current 전이 + actors 기록
```

### 1.4 테스트 (Testing) — 시나리오 4종 + 회귀 가드

```python
# tests/scenarios/test_stale_loop.py
def test_stale_detected_after_threshold():
    """90일 전 last_verified → wiki_stale_detect가 후보로 반환"""

def test_stale_revalidated_with_evidence():
    """stale 페이지에 새 사실 출처 제시 → wiki_update(revalidate=true)로 current 전이, agents: 기록"""

def test_archive_moves_file_and_stamps_frontmatter():
    """stale 페이지에 wiki_archive 호출 → archive/<date>/<slug>.md로 이동 + 원본 archived_at + reason"""

def test_update_rejects_50pct_rewrite():
    """content 1.5배 초과 시 wiki_update 400 + '대규모 재작성 north star 위반' 메시지"""

# 회귀 가드 (P0)
def test_frontmatter_block_yaml_roundtrip():
    """A#3 회귀 — block YAML tags가 갱신 후에도 보존"""
def test_archive_path_traversal_blocked():
    """slug='../../etc' → 400 (A#1과 동일 방어)"""
```

- **테스트 파일 위치**: `tests/scenarios/` 신규 디렉터리 (Lite bootstrap과 분리, 사용자 vault 침범 ❌).
- **테스트 격리**: 각 시나리오는 임시 vault 생성 (`tmp_path`) 후 실행, 실 vault 미수정.
- **테스트 통과 기준**: 4종 모두 pass + 회귀 가드 2종도 pass.

---

## 2. 결과 (Consequences)

### Positive

1. **north star 실행 기반 확보**: 평가 누락 시나리오(테마 5 / §3.1 / A#0 / P0#0)가 결정으로 박힘 → 구현 사이클이 흔들리지 않음.
2. **에이전트 자율 정합화 루프 가시화**: 5가지 액션 × 4상태 전이가 표면화되어 평가·테스트·문서가 동일 그림 공유.
3. **원문 보존 north star의 실행 가드 신설**: content 1.5배 가드는 "대규모 재작성 ❌"를 코드 레벨에서 강제.
4. **모순 발견 표준화**: `contested` 상태 + cross-link + log.md 역추적이 한 묶음으로 자동화 (평가 B#5/#6/#7과 연결).
5. **MCP ↔ CLI 권한 평준화**: archive 액션이 CLI만 노출되던 비대칭 해소.

### Negative

1. **MCP 도구 수 +2**: 23 → 25종, 도구 발견 비용 증가. 완화: 도구 설명을 짧게 유지 + ADR §1.3 signature 명시.
2. **상태 머신 도입의 보수 비용**: 4상태 × N페이지 frontmatter 손상 시 복구 절차 필요. 완화: vault verify에 상태 정합성 체크 추가.
3. **content 1.5배 가드 false positive**: 정상 갱신(누락 보강)이 가드에 걸릴 수 있음. 완화: 1.5배는 soft limit, 사용자 override 옵션 (예: `force: true` + 감사 로그).
4. **시나리오 테스트 격리 비용**: `tmp_path` 4회 생성 = CI 시간 증가. 완화: pytest fixture 공유 + 병렬화.

### Trade-off 인정

- "에이전트 자율 권한 확대" ↔ "실행 가드 강제" — 본 ADR은 **상태 머신 + 가드 + provenance 기록**으로 자율 권한을 확보하되, **본문 50%+ 재작성 금지**로 안전성 확보. 사람 최종 승인(archived → current 복귀, contested 전이)은 사람 영역으로 유지 — north star 정합.

---

## 3. 하지 않을 것 (Out of Scope)

- **자동 archive (사람 승인 없는 격리)**: 본 ADR은 에이전트가 stale/archive 액션을 *발의*할 수 있되, 최종 결정은 사람 또는 명시적 정책(예: 365일+ stale 자동 격리)에 위임.
- **에이전트 간 협업 큐**: 멀티 에이전트가 동시 갱신 시 충돌 해결은 본 ADR 범위 밖 (AGENTS.md §3 "멀티 에이전트 experimental" 상태 유지).
- **자동 revalidate**: stale → current 전이는 evidence 필수, 자동 갱신 (예: 단순 시간 경과로 current 복귀) ❌.
- **대규모 재작성의 우회**: split + merge + archive + 새 페이지 생성의 합법적 우회 경로는 허용하되, 한 번의 `wiki_update`로 50%+ 본문 교체는 계속 금지.

---

## 4. 수용 기준 (Acceptance Criteria)

- [ ] `_meta/SCHEMA.md`에 status 4상태 정의 명시 (Lite bootstrap 시 사용자 vault에 자동 복사)
- [ ] `raven/mcp/tools/stale.py`에 `wiki_stale_detect`, `wiki_archive` 구현
- [ ] `raven/mcp/tools/write.py`의 `wiki_update`에 content 1.5배 가드 + `evidence`/`revalidate` 파라미터 추가
- [ ] `tests/scenarios/test_stale_loop.py` 4종 시나리오 + 회귀 가드 2종 pass
- [ ] changelog v0.7.69+ (또는 후속)에 "에이전트 스테일 루프 구현" 항목 1줄
- [ ] 평가 문서 v0.7.66+ 재평가에서 A#0/P0#0 해소 확인

---

## 5. 후속 (Follow-ups)

- v0.7.69+ 구현 사이클: 본 ADR §1.3 도구 골격 + §1.4 테스트 골격 작성. **Plan B**: 시나리오 테스트 골격 + MCP 인터페이스 초안.
- 평가 문서 v0.7.69+ 재평가 시: A#0/P0#0 권고가 본 ADR로 해소되었음을 changelog cross-link.
- Lite bootstrap에 `status` 4상태 정의가 자동 포함되는지 검증 (현재 Lite bootstrap은 SCHEMA.md + PROJECT-WORKFLOW.md + log.md 3종).

---

## 6. 메타

- **작성일**: 2026-07-06
- **작성자**: raven-orchestrator (사용자 north star 확인 후)
- **승인**: 사용자 명시 승인 대기 (`/3` 응답으로 사용자 Plan C 진행 승인 받음)
- **supersedes**: 없음 (첫 결정)
- **superseded by**: (후속 결정 발생 시 명시)

---

*이 ADR은 사용자 north star(2026-07-06 확인)와 평가 문서 보완 v2(2026-07-06)의 결정 골격이다. 평가 대상 코드의 north star 실행 기반 부재를 메타 평가는 지적했으나, 본 ADR이 결정 골격을 박음으로써 다음 구현 사이클이 흔들리지 않는다.*