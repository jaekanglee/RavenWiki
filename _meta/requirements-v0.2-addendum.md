---
title: 요구사항 v0.2 추가 (Multi-Vault)
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, requirements, raven]
sources: [_meta/requirements.md]
confidence: high
---

# 요구사항 v0.2 추가 (Multi-Vault)

> [[requirements]] (M1 니즈/제약)의 후속.
> M2 (2026-06-25)에서 사용자 비전 재정의로 추가/변경된 요구사항.

---

## 추가된 사용자 니즈 (N7-N10)

| # | 니즈 | 근거 |
|---|---|---|
| **N7** | **vault를 어디든 지정 가능** | "내가 원하는 아무 곳의 폴더를 vault로" |
| **N8** | **멀티 vault 지원** | 사용자 + 에이전트별 vault 분리 |
| **N9** | **에이전트가 vault의 일급 시민** | "헤르메스 각 에이전트가 작업, 결과물 vault에 쓰기" |
| **N10** | **사람 + 에이전트 동일 인터페이스** | "CLI도 가능, 대시보드도 가능" |

### N7 세부
- vault 경로 자유 (`~/vaults/`, `~/Documents/`, iCloud 등)
- 환경변수 `WIKI_VAULTS_DIR`로 통째로 위치 변경
- 기본값은 `~/vaults` (단순)

### N8 세부
- 여러 vault 동시 운영
- vault 간 데이터 격리
- vault 전환 (CLI `vault use`, GUI picker)

### N9 세부
- Python 어댑터 (`raven.agents`)
- shell escape 없이 직접 호출
- scope 기반 권한 (어떤 vault 쓸 수 있는지)
- provenance 자동 (누가/언제/왜)

### N10 세부
- 4가지 인터페이스 (CLI / GUI / Python / HTTP)
- 어느 인터페이스로 작업해도 같은 결과
- vault picker UI (Obsidian식)

---

## 추가된 제약 (C6-C7)

| # | 제약 | 영향 |
|---|---|---|
| **C6** | **개발 소스 ≠ 런타임 데이터** | 코드베이스 폴더 안에 vault 데이터 ❌ |
| **C7** | **에이전트 격리** | 사람 vault와 에이전트 vault 명확히 분리 |

### C6 세부
- 사용자 명시: "개발소스를 들고있는 폴더 내부에 런타임데이터를 관리하겠다는게 아님"
- vault는 `~/vaults/<name>/` 외부 위치
- 코드베이스 = `~/Desktop/Dev/Project/Raven/`

### C7 세부
- 에이전트 권한은 `AgentScope.vault_names` 화이트리스트
- scope 밖 vault 쓰기 → PermissionError
- 기본 `allow_delete=False` (안전)

---

## 변경된 니즈 (N1-N6 진화)

| # | M1 (단일 vault) | M2 (multi-vault) |
|---|---|---|
| N1 (Obsidian 없이) | ✅ | ✅ (강화: "Obsidian 모티브만 빌려서") |
| N2 (개발자 친화) | ✅ | ✅ |
| N3 (Tailscale) | ✅ | ✅ |
| N4 (폰/웹) | ✅ | ✅ |
| N5 (자동 정리) | ✅ (Karpathy 패턴) | ✅ (에이전트 자체가 사용자) |
| N6 (표준 인터페이스) | ✅ (MCP) | ✅ (4-way: CLI/GUI/Python/HTTP) |

→ N5/N6가 M2에서 가장 큰 진화.

---

## 비-목표 (Non-Goals) 갱신

| 추가 | 설명 |
|---|---|
| ~~단일 vault~~ | ❌ multi-vault (M2에서 정반대로) |
| 에이전트 전용 vault | ✅ (권장, 강제 ❌) |

---

## 사용자 인용 (M2 추가)

> "나는 옵시디언처럼 특정 볼트를 정해놓고, 그 볼트안에 MD파일들을 계층별로 구성할 수 있게하고싶음"
> "웹 대시보드를 구축해서 GUI로이 작업들을 하고싶음"
> "내가 사람이 수동으로 이 Vault를 관리도 하겠지만 추후에는 헤르메스의 각 에이전트들이 작업하고, 작업한 결과물을 Vault에 쓰고"

→ **원칙**: Obsidian식 사용성 + GUI + CLI + Python 자유 + 에이전트 협업

---

## 충족 매트릭스

| 니즈 | 충족 방법 |
|---|---|
| N7 (vault 어디든) | `WIKI_VAULTS_DIR` env + `raven vault create <name> <path>` |
| N8 (멀티 vault) | `.registry.json` + `raven vault {list,use,...}` |
| N9 (에이전트) | `raven.agents.Agent` + `AgentScope` |
| N10 (4 인터페이스) | CLI + GUI + Python + HTTP 모두 작동 |
| C6 (분리) | `~/vaults/` 외부 + env override |
| C7 (격리) | `AgentScope.vault_names` + `allow_delete=False` 기본 |

---

## 다음 결정 후보

| 주제 | 결정 시점 |
|---|---|
| 다중 사용자 (multi-tenant) | 사용자 2명 이상 시 |
| vault 간 cross-link | 사용 패턴 관찰 후 |
| 백업 자동화 cron | 데이터 누적 후 |
| vault별 SCHEMA override | 사용자 비전 확정 후 |
