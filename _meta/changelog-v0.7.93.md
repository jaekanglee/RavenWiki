# Changelog v0.7.93 — 표준 surface 정합 명시 (REST ↔ MCP, layer 경계)

> **BLUF**: v0.7.91에서 Lite bootstrap 3종을 MCP `wiki_get_guide` (Tier 2 / 에이전트) 로 신설. Dashboard drawer (Tier 1 / 사람 운영자) 가 같은 3종을 REST `/api/vaults/{name}/guide/{kind}` 로 조회 중. **두 surface는 contract 1:1 (화이트리스트 + 응답 shape)** — 같은 데이터를 layer가 다른 진입점으로 조회. **v0.7.93 정책 결정**: Dashboard는 REST 유지 (Tier 1 ↔ Tier 1 = 자연스러움, MCP는 Tier 2 진입점 = layer 경계 보존). AGENTS.md §5.5 + Dashboard GuidesViewer에 표준 surface 안내 1줄 추가. **코드 0줄 변경, 정책 정합**. 회귀 631/631 PASS.

이전 changelog: `_meta/changelog-v0.7.92.md`

---

## §0 — 변경 요약 (1 안내 + 1 문구, **코드 0줄 변경**)

| 파일 | 변경 | LOC |
|---|---|---|
| `dashboard/src/components/GuidesViewer.tsx` | "MCP `wiki_get_guide(vault, kind)` 도 가능 (v0.7.91+)" 1줄 안내 추가 | +8 |
| `AGENTS.md §5.5` | Lite bootstrap 3종 read 사례 명시: 사람 운영자 = REST, 에이전트 = MCP, contract 1:1 + layer 경계 보존 이유 | +1 |
| `_meta/changelog-v0.7.93.md` (신설) | 본 changelog | — |

---

## §1 — 왜 코드 0줄 변경인가

### 1.1 layer 모델 재확인

Raven의 Tier 모델 (AGENTS.md §3, §5.5):
- **Tier 1 = 제품 (Layer 1) = 사람 운영자 도구**: CLI / HTTP API / Dashboard
- **Tier 2 = 활용 (Layer 2) = LLM 에이전트**: MCP only (단일 진입점)

`wiki_get_guide` (v0.7.91) 의 설계 의도:
- **MCP 표면 = Tier 2 표준 (에이전트용)** — 외부 LLM 에이전트가 R9 ("vault 외부 시스템 ❌") 회피하면서 표준 protocol로 Lite bootstrap read
- **REST 표면 = Tier 1 표준 (사람 운영자용)** — Dashboard drawer / curl / 스크립트

Dashboard가 Tier 1 도구라는 사실은 변하지 않음. v0.7.89 REST 신설, v0.7.91 MCP 신설, v0.7.93 **두 표면 공존 = 의도된 layer 경계**.

### 1.2 검토한 대안 (3가지)

| 대안 | 거부 이유 |
|---|---|
| **A1. Dashboard → MCP 직접 호출 (SSE/stateful)** | Tier 1 도구가 Tier 2 표면 직접 사용 = layer 경계 약화. 코드 +200줄, session handshake + SSE 처리 + MCP down 시 fallback. **over-engineering** — 사람 운영자 도구가 R9 회피할 이유 없음 (R9 = 에이전트 정책). |
| **A3. MCP 우선 + REST fallback (이중 surface)** | 두 경로 동시 운영 = 디버깅 surface 2x, 테스트 2x. **복잡성 > 가치**. 사용자가 "MCP 응답 vs REST 응답 불일치" 디버깅하는 시나리오 ❌. |
| **A2 (현재 결정). REST 유지 + 표준 surface 명시** | 코드 0줄. 안내 1줄. **구조적으로 정합** (Tier 1 ↔ Tier 1). **사용자 가치**: 사람 운영자가 "MCP도 같은 surface" 인지 = agent 협업 워크플로우 명확. |

### 1.3 v0.7.91 신설의 진짜 의도 재확인

`wiki_get_guide` 신설 이유는 README/ADR §2.1 "R9 정합" 입니다:
> "에이전트가 PROJECT-WORKFLOW 본문을 보려면 vault 파일시스템 read가 사실상 유일한 방법. R9의 strict 해석으로는 위반."

이건 **에이전트의 문제** (외부 LLM). 사람 운영자는 Dashboard가 있으니 vault 파일시스템 직접 read 불요. R9 = "에이전트가 vault 외부 시스템 ❌" = 사람 운영자에는 적용 ❌.

→ **A2 결정 정합**: 사람 운영자 = REST (자연스러움) / 에이전트 = MCP (R9 회피).

## §2 — 안내 1줄 (GuidesViewer)

GuidesViewer 좌측 하단 안내 문구에 추가:

```
외부 LLM 에이전트는 표준 MCP
wiki_get_guide(vault, kind)
로도 같은 3종을 조회할 수 있습니다 (v0.7.91+).
```

→ 사람 운영자가 "MCP도 있구나" 인지 → 외부 에이전트와 같은 surface 인지 = agent 협업 워크플로우 명확.

## §3 — AGENTS.md §5.5 보강 (1줄)

기존 §5.5 ("에이전트 ↔ Raven = MCP만") 끝에 사례 1개 추가:

> Lite bootstrap 3종 read 사례 (v0.7.93+): 사람 운영자 = `GET /api/vaults/{name}/guide/{kind}` (Dashboard drawer) / 외부 에이전트 = `wiki_get_guide(vault, kind)` (MCP). **contract 1:1 (화이트리스트 + 응답 shape)** — 같은 surface를 두 layer가 다른 진입점으로 조회. **Dashboard가 MCP를 직접 호출하지 않는 이유**: Tier 1 (사람 도구) ↔ Tier 1 (REST) 가 자연스럽고, MCP는 Tier 2 (에이전트) 진입점. layer 경계 보존.

→ 운영자/에이전트가 Raven의 layer 모델을 1순으로 이해 가능. v0.7.88 (Layer 1/2 정합) + v0.7.91 (MCP 신설) + v0.7.93 (REST ↔ MCP 사례) = layer 모델 3-step evolution 정합.

## §4 — 검증

### 4.1 pytest 회귀

```
$ pytest tests/ -q --ignore=tests/curator
631 passed, 1 skipped, 1 warning in 39.87s
```

(v0.7.92 baseline 631 동일, 0 회귀)

### 4.2 Dashboard build

```
$ cd dashboard && npm run build
✓ built in 1.82s (변경 minimal, surgical)
```

### 4.3 Layer 정책 정합 grep

```
$ rg -n 'Tier 1| Tier 2|Layer 1|Layer 2' AGENTS.md
... (기존 §0.5, §3, §5.5) — 정합
```

## §5 — 후속 작업 (deferred)

- **Dashboard에서 MCP 직접 호출 (B안 / C안)**: 사용자/스테이크홀더가 "Dashboard도 MCP 우선" 명시 요청 시 별도 사이클 (A1 / A3 검토, R9 / layer 정합 재논의).
- **MCP guide 결과 캐싱 (v0.7.91+ 후속)**: 멀티 vault에서 `wiki_get_guide` 반복 호출 시 cache. Lite bootstrap sync 정책과 결합.
- **Lite bootstrap 3종 read 외 추가 surface**: 현재는 guide만. 운영자가 다른 파일을 "lite bootstrap" 으로 분류 시 `LITE_GUIDE_KINDS` 확장 (정책 결정 = ADR 필요).
