---
title: plan-v0.3 — Vault/Page CRUD 강화 (v2, progressive delivery)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, plan, wikisys, v0.3]
sources: [_meta/decisions-d1-d6.md, _meta/decisions-d7-d9-multivault.md, _meta/requirements-v0.2-addendum.md]
confidence: high
---

# plan-v0.3 — Vault/Page CRUD 강화 (v2)

> v0.2 (2026-06-25) CRUD 표면을 점검 + **11개 구조적 결함 발견 → 보수적 progressive delivery**.
> 원칙: **단순 / 안정 / 호환**. v0.2 시그니처 유지 + 점진적 강화.
> **v1 → v2 변경**: B4 위험도 재평가, B12 발견, 4 인터페이스 동시 변경 = 너무 큼 → **progressive**.

---

## 1. v0.2 현재 상태 (변경 없음)

CLI 9 commands / API 12 endpoints / Agent 어댑터 / GUI. CRUD 자체는 다 있음.

## 2. 발견된 결함 11건 (v2 업데이트)

| # | 결함 | 위치 | v1 위험도 | v2 위험도 | 변경 사유 |
|---|---|---|---|---|---|
| **B1** | `page new` 자동 prefix 없음 | `cli/__main__.py:236` | HIGH | **HIGH** | ✅ |
| **B2** | frontmatter 로직 3곳 중복 | cli/api/agent | HIGH | **HIGH** | ✅ |
| **B3** | API `update_page` 가 `created` 갱신 안 함 | `api/server.py:222` | MED | MED | ✅ |
| **B4** | slug 검증 부재 (`..`, 절대경로) | 4곳 | HIGH | **MED** | ⚠️ 실제 exploit 가치는 낮음 (vault = 본인 home). 그래도 v0.3에 포함 (test + 가드) |
| **B5** | archive 평탄화 (nested slug 손실) | cli/agent | LOW | LOW | ✅ |
| **B6** | `.vault.json` path 하드코딩 | `vault.py:53` | MED | LOW | ⚠️ registry path가 따로 있으므로 OK. v0.4에서 환경변수 rename과 함께 |
| **B7** | `vault create` 가 빈 폴더만 (SCHEMA 없음) | `vault.py:43` | HIGH | **HIGH** | ✅ |
| **B8** | clone/import/rename 없음 | CLI/API | LOW | LOW | ❌ v0.4 |
| **B9** | `_archive` cleanup 없음 | — | LOW | LOW | ❌ v0.4 |
| **B10** | `vault remove` stale 가드 | `registry.py:137` | LOW | LOW | ❌ v0.4 |
| **B12** | **메타 write API 없음** — vault 생성 후 `_meta/SCHEMA.md` 업데이트 CLI/API 없음 | 없음 | (없음) | **MED** | ⚠️ v2에서 신규 발견. R4에 흡수 |

**v0.3 MUST: B1/B2/B4/B7 + B12 흡수 = 4+1 = 5건. SHOULD: B3/B5.**

## 3. 핵심 전략 변경: Progressive Delivery

### v1 문제 인식
- 4 인터페이스 동시 마이그레이션 = 작업량 폭증 (~400 LOC + 21 tests + 문서)
- 한 곳에 버그 → 4곳 다 영향 → 디버깅 비용 ↑
- **사용자 인용 "단순/안정" 우선** → 한 번에 큰 변경 위험

### v2 전략
**"CLI 먼저 → API → Agent → GUI" 순서로 릴리스 단위 분할.**

| 릴리스 | 범위 | 핵심 가치 | LOC |
|---|---|---|---|
| **v0.3.0** | CLI (page CRUD + vault create) | 가장 빈번한 사용 경로 단단화 | ~150 |
| **v0.3.1** | API 12 엔드포인트 | HTTP 사용자 안전성 | ~150 |
| **v0.3.2** | Agent 어댑터 | LLM 자동화 안전성 | ~50 |
| v0.3.3 (선택) | GUI 일관성 | 마지막 마감 | ~30 |

**각 릴리스는:**
- 독립 머지 가능 (revert 쉬움)
- 사용자 테스트 후 다음 단계
- 실패 시 한 단계만 롤백

**v0.3.0 (이번 plan의 범위):**
- R1 (slug 검증) **CLI만** — API/Agent는 다음 릴리스
- R2 (fm 단일화) **CLI만**
- R3 (자동 prefix) **CLI만**
- R4 (vault 부트스트랩) **CLI만** — API는 같은 함수 호출만 추가
- S2 (CLI `created` 보존)

→ **API/Agent는 v0.3.0 코드와 100% 호환** (시그니처 안 바뀜, 내부 구현만 변경). v0.3.1/2는 같은 `slug.py`/`fm.py` 모듈을 import만 하면 끝.

---

## 4. v0.3.0 MUST (5건, 이번 plan)

### R1. Slug 검증 모듈 (`wikisys/core/slug.py`)
```python
def validate(slug: str, *, vault_root: Path) -> Path:
    """Return absolute path if safe; raise ValueError otherwise.
    
    Reject: empty, absolute (start with / or ~), contains '..', contains \0,
            contains ':' (Windows drive), not within vault_root after resolve.
    """
```
- **사용**: CLI `page new/delete` + `vault create`(bootstrap path) 만
- **위치**: `wikisys/core/slug.py` (신규 ~50 LOC)
- **테스트**: 6 케이스 (정상/`..`/절대/`~`/NUL/outside)

### R2. Frontmatter 단일화 (`wikisys/core/frontmatter.py`)
```python
def parse(text: str) -> tuple[dict, str]: ...
def render(meta: dict, body: str, *, agents: Optional[Provenance]=None) -> str: ...
def merge(existing: dict, updates: dict) -> dict:
    """`created` 보존, `updated` 항상 today, tags는 list 강제."""
```
- **사용**: CLI `page new` + `page delete` (없음, fm만 다룸) + 향후 API/Agent
- **Agent의 `_render`/`_split_frontmatter`는 v0.3.2에서 흡수** (이번엔 안 함)
- **위치**: `wikisys/core/frontmatter.py` (신규 ~80 LOC)
- **테스트**: 8 케이스

### R3. `page new` 자동 prefix
```python
def _normalize_slug(slug: str) -> str:
    """If no '/' and 'content/' path doesn't exist, prepend 'content/'."""
```
- **단순 정책**: `wikisys page new foo` → `content/foo`
- `wikisys page new meta/welcome` → 그대로 (`meta/`는 사용자가 명시)
- **위치**: `cli/__main__.py` 안 inline (R1과 같은 파일, ~10 LOC)
- **테스트**: 2 케이스 (with/without prefix)

### R4. `vault create` 부트스트랩
```python
class Vault:
    @classmethod
    def create(cls, name, path, mode, owner, description, *, bootstrap: bool = True):
        ...
        if bootstrap:
            (path / "_meta").mkdir(parents=True, exist_ok=True)
            (path / "content").mkdir(parents=True, exist_ok=True)
            _copy_templates(path / "_meta")
```
- **템플릿**: `wikisys/core/templates/{SCHEMA,RULES}.md` (코드베이스 추적)
- **옵션 `--no-bootstrap`**: 기존 폴더 등록 시
- **위치**: `wikisys/core/vault.py` (~20 LOC 변경) + 신규 templates 2 파일
- **테스트**: 3 케이스 (bootstrap on/off/실패)

### S2. CLI `created` 보존 (page update는 CLI에 없음 — R2 fm 단일화의 `merge()`가 처리)
- `wikisys page new`만 있는 CLI는 항상 신규. 단, **vim으로 직접 수정한 후 frontmatter 다시 쓸 때 `created` 안 바뀌도록 보장**은 R2의 `merge()`가 담당.
- **테스트**: 1 케이스 (R2에 흡수)

### B12 흡수: 메타 write CLI (최소)
```bash
wikisys meta sync    # _meta/SCHEMA.md, RULES.md를 템플릿에서 재카피 (덮어쓰기)
```
- **위치**: `cli/__main__.py` 신규 sub-app `meta` (~30 LOC)
- **용도**: vault 생성 후 SCHEMA가 outdated일 때 수동 동기화
- **테스트**: 2 케이스 (실제 카피 + no-op)

---

## 5. v0.3.0 변경 영향

### 5.1 신규 파일
| 경로 | LOC |
|---|---|
| `wikisys/core/slug.py` | ~50 |
| `wikisys/core/frontmatter.py` | ~80 |
| `wikisys/core/templates/SCHEMA.md` | ~30 |
| `wikisys/core/templates/RULES.md` | ~20 |
| `tests/test_slug.py` | ~80 |
| `tests/test_frontmatter.py` | ~100 |
| `tests/test_cli.py` | ~60 |
| `tests/test_vault_create.py` | ~60 |

### 5.2 수정 파일
| 경로 | 변경 | LOC diff |
|---|---|---|
| `wikisys/core/__init__.py` | `slug_module`, `fm_module` export | +5 |
| `wikisys/core/vault.py` | `create()` 에 bootstrap 인자 | +20 |
| `wikisys/cli/__main__.py` | `page new`/delete + `vault create` 가 slug validate + fm 단일화 사용 + `meta sync` sub-app | +60 |

**총 ~565 LOC** (코드 ~250 + 테스트 ~300 + 템플릿 ~50).

### 5.3 하위호환
| 항목 | 호환성 |
|---|---|
| 기존 `wikisys vault list/use/info/create/register/remove` | ✅ 시그니처 동일 |
| 기존 `wikisys page new content/foo` | ✅ 동작 그대로 |
| `wikisys page new foo` | ⚠️ **신규: 자동 `content/foo`로 변환** — `wikisys page new _meta/welcome` 같은 명시 prefix는 그대로 |
| 기존 vault (`~/vaults/{default,second-vault}`) | ✅ **부트스트랩 영향 없음** (신규 vault만 bootstrap) |
| Agent `wikisys.agents.Agent` | ✅ v0.3.0은 CLI만 변경, API/Agent 시그니처 그대로 |
| API 12 endpoints | ✅ v0.3.0은 CLI만 변경 |

---

## 6. 단계별 실행 (E1-E10)

| 단계 | 작업 | 의존 | 산출물 |
|---|---|---|---|
| **E1** | `slug.py` + 6 테스트 | 없음 | `pytest tests/test_slug.py` pass |
| **E2** | `frontmatter.py` + 8 테스트 | 없음 | `pytest tests/test_frontmatter.py` pass |
| **E3** | `templates/{SCHEMA,RULES}.md` 추가 | 없음 | 2 파일 |
| **E4** | `Vault.create` bootstrap + 3 테스트 | E3 | `pytest tests/test_vault_create.py` pass |
| **E5** | CLI `page new`/delete + `vault create` 마이그레이션 | E1, E2, E4 | `pytest tests/test_cli.py` pass |
| **E6** | CLI `meta sync` sub-app + 2 테스트 | E3 | 신규 |
| **E7** | `wikisys.core.__init__` export 추가 | E1, E2 | import 가능 |
| **E8** | 기존 vault dry-run (default/second-vault) | E5 | 0 broken, 0 missing 유지 |
| **E9** | 문서 업데이트 (wikisys-guide.md, skill) | E5-E6 | 2 파일 패치 |
| **E10** | 수동 검증 5개 시나리오 | E8, E9 | DoD 체크리스트 |

**예상 총 LOC: ~565 (코드 ~250 + 테스트 ~300 + 템플릿 ~50 + 문서 ~50).**

---

## 7. 완료 기준 (v0.3.0 DoD)

- [ ] `pytest tests/test_slug.py tests/test_frontmatter.py tests/test_cli.py tests/test_vault_create.py` — 전체 pass (~19 신규 케이스)
- [ ] `wikisys vault create smoke /tmp/test-smoke` → `content/` + `_meta/{SCHEMA,RULES}.md` 존재
- [ ] `wikisys vault create existing /tmp/x --no-bootstrap` → 빈 폴더만 등록
- [ ] `wikisys page new foo --title X` → `content/foo.md` 생성 (자동 prefix)
- [ ] `wikisys page new meta/welcome --title W` → `_meta/welcome.md` 생성 (명시 prefix 보존)
- [ ] `wikisys page new ../../../tmp/pwn` → "❌ invalid slug" 에러
- [ ] `wikisys page new content/foo` (재실행) → "❌ exists" 에러 (정상)
- [ ] `wikisys meta sync --vault default` → `_meta/{SCHEMA,RULES}.md` 가 템플릿 내용으로 갱신
- [ ] 기존 `~/vaults/default` 동작 (page CRUD, link check, build) — 회귀 없음
- [ ] 커밋 메시지: `feat(crud): v0.3.0 — CLI safety + vault bootstrap (progressive)` + `feat(slug): validation module` + `feat(fm): frontmatter unification`

---

## 8. v0.3.1 (다음 릴리스, 이번 plan 범위 외)

- API 12 endpoints 모두 R1/R2/R3 흡수
- `wikisys.api.server` import 변경만 (slug.py/fm.py 호출)
- LOC: ~150 (대부분 import + 함수 호출 교체)

## 9. v0.3.2 (그 다음)

- `wikisys.agents.Agent` 의 자체 `_render`/`_split_frontmatter` 제거 → fm_module 사용
- scope 검증 강화 (B4 가드와 결합)
- LOC: ~50

## 10. v0.4 (이후)

- B8 (clone/import), B9 (archive cleanup), B10 (stale 가드)
- `.vault.json` path 환경변수 rename (B6)
- cross-vault wikilink

---

## 11. 결정 보류 (v2)

| # | 결정 | 선택지 | v2 추천 |
|---|---|---|---|
| **Q1** | 부트스트랩 기본 on? | on / off (opt-in) / 묻기 | **on** (단순/안정) |
| **Q2** | `page new foo` 충돌 시? | `content/foo` (없으면) / `foo` (있으면) / 항상 강제 | **`content/foo`** (메타 페이지는 명시) |
| **Q3** | archive mirror vs 평탄화 | mirror / 평탄화 유지 | **mirror** (v0.3.0 범위 밖, v0.4로) |
| **Q4** | clone (S3) v0.3 포함? | v0.3 / v0.4 | **v0.4** |
| **Q5 (신규)** | v0.3.0에 API/Agent 포함? | 모두 / CLI만 / CLI+Agent | **CLI만** (progressive delivery) |

---

## 12. 결정 기록

| 결정 | 내용 | 일자 |
|---|---|---|
| **D10** | 4 인터페이스 CRUD 로직은 `wikisys.core` 단일 함수로 통일 | 2026-06-25 |
| **D11** | slug 검증: `..`/`~`/절대/NUL 거부 + vault root 내 확인 | 2026-06-25 |
| **D12** | 신규 vault 부트스트랩 기본 on | 보류 (Q1) |
| **D13** | `page new foo` → 자동 `content/foo` | 2026-06-25 |
| **D14** | archive mirror 경로 | 보류 (Q3, v0.4) |
| **D15 (신규)** | v0.3.0은 CLI만. API는 v0.3.1, Agent는 v0.3.2 (progressive) | 2026-06-25 |

---

## 13. v1 → v2 변경 요약

| 항목 | v1 | v2 | 이유 |
|---|---|---|---|
| 범위 | 4 인터페이스 동시 | CLI만 (progressive) | "단순/안정" + revert 용이 |
| LOC | ~650 | ~565 (CLI만) | 단계별 분리 |
| 결함 | 10건 | **11건 (B12 추가)** | 메타 write 부재 발견 |
| B4 위험도 | HIGH | **MED** | 실제 exploit 가치는 낮음 |
| B6 위험도 | MED | **LOW** | registry path가 분리되어 OK |
| Q5 (신규) | 없음 | CLI만 우선 | progressive 결정 |
| S1 (archive mirror) | SHOULD | v0.4로 분리 | v0.3.0 단순화 |
| S2 (CLI created) | SHOULD | **MUST (R2 merge에 흡수)** | fm 단일화의 일부 |

**v2는 v1의 "보수적" + "progressive" 강화판.**
