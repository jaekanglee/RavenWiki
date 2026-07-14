# Raven Agent-Policy Separation Implementation Plan

> **For Hermes:** Execute only after the user approves this plan and selects the independent policy-bundle destination. Keep commits user-approved.

**Goal:** Raven retains only an enforceable, product-owned vault/MCP contract; the current agent behavior and vault-operation guidance is extracted into a user-owned policy bundle that Raven never creates, overwrites, syncs, or treats as normative.

**Architecture:** Split the current Lite bootstrap into (1) Raven-owned technical facts and hard safety boundaries, and (2) user-owned governance and delegation policy. Raven remains multi-agent-capable through primitives (permissions, auditability, idempotency, conflict signals), not through centrally prescribed agent roles, approval flows, or curation behavior.

**Tech stack:** Python vault bootstrap/sync (`raven/core/vault.py`), Markdown templates, MCP guide read/diff allowlists, pytest. No new dependency and no fifth entrypoint.

---

## 0. Scope and non-goals

### In scope

- Stop Raven from writing or overwriting root-level agent convention files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`).
- Replace the policy-heavy meaning of Lite bootstrap `PROJECT-WORKFLOW.md` with a short Raven-owned technical contract.
- Extract the current non-product policy into a handoff bundle that the user can move to an independently managed location.
- Keep Raven’s safety/technical guarantees explicit and testable.
- Preserve existing vault data and existing bootstrap files; migration must be opt-in and non-destructive.

### Explicit non-goals

- Raven does **not** become a multi-agent orchestrator, role manager, task queue, policy editor, or prompt registry.
- Raven does **not** generate a new user `AGENTS.md` or a replacement user policy.
- Raven does **not** auto-delete existing pointer stubs or alter user files.
- This migration does not change Markdown SoT, the four entrypoints, or Dashboard scope.
- This migration does not redesign all data-schema/lint semantics in the same patch. Runtime rules are separately classified before any behavior change.

---

## 1. Ownership model to freeze in an ADR

Create an ADR before code changes because this changes the boundary between product contract and user governance.

| Layer | Owner | Raven may update? | Examples |
|---|---|---:|---|
| **Raven contract** | Raven product | Yes, through upgrade/sync | Markdown SoT, query-index rebuildability, MCP tool schemas, read/write/admin modes, path restrictions, audit/log mechanics, errors and limits |
| **LLM Wiki data profile** | Raven product, optional at enablement | Yes, only as an explicit profile contract | Supported frontmatter fields, relation representation, parser/lint behavior |
| **Vault operating policy** | Vault owner | No | What deserves recording, approval gates, review expectations, preferred folders, archival/curation cadence |
| **Agent role policy** | User/agent operator | No | Researcher vs writer vs reviewer scope, allowed tools, report format, escalation rules |
| **Task assignment** | User/orchestrator | No | Goal, target documents, acceptance criteria, deadline/priority |

**Decision rule:** a statement belongs to Raven only if the product technically enforces it or must document a stable public interface. If it tells an agent *when*, *why*, or *whether* to make a knowledge judgment, it belongs to the user policy bundle.

---

## 2. Extract exactly what is currently conflated

### 2.1 Keep in Raven-owned contract

From `raven/core/templates/agent/PROJECT-WORKFLOW.md` and `SCHEMA.md`, retain only:

- Markdown is canonical; `wiki.db` is a rebuildable query index.
- The official MCP endpoint, `tools/list` discovery, tool input/output semantics, and the actual `read/write/admin` capability boundary.
- Tool-enforced protection: direct agent writes to protected paths fail; `log.md` mechanics are append/audit based.
- The exact data fields, link syntax, relation payload format, and lint result meanings that Raven actually parses or enforces.
- The fact that a vault may have a user-owned policy, without requiring one or interpreting it.
- Upgrade/freshness mechanics only for Raven-owned artifacts.

### 2.2 Extract into user-owned policy bundle

Extract/adapt these current contents because they are governance or delegation, not a Raven interface contract:

| Current source | Content to extract | Why it is user-owned |
|---|---|---|
| `PROJECT-WORKFLOW.md` §0 Quick Start | mandatory reading sequence and "understanding complete" threshold | Each operator decides onboarding depth and order |
| §0.5 Layer 2 operational interpretation | who curates, what agents may decide, human/agent division beyond hard permissions | Delegation model is user policy |
| §3 | the four save signals and their exemptions | Records-worthiness is a vault quality policy |
| §4 | BLUF, length, prose, summary, link-context style rules | Writing/editorial policy |
| §5 | recommended content folder layout | Vault-specific information architecture |
| §6.1–6.5 | self-review, RAG habits, curation order, repair/archive/proposal behavior | Operational judgment and maintenance policy |
| §7–§7.5 | publication triggers, type-by-type autonomy, agent roles, multi-agent folder/lock workflow | Role allocation and collaboration policy |
| §8.5 | what an agent should remember/judge and when | Agent/operator governance |
| `SCHEMA.md` type table | "agent write" column and human-review claims | A policy table mixed into a data schema |
| `SCHEMA.md` status narrative | auto-promotion/review expectations not strictly implemented as contract | Must be classified as policy unless code guarantees it |

### 2.3 The extracted handoff artifact

Create **one migration-only export**, not an active Raven template:

`docs/migrations/agent-policy-bundle-v1.md`

It contains three clearly marked copyable documents:

1. `VAULT-POLICY.md` — vault purpose, write/approval/curation rules.
2. `AGENT-ROLE.md` — a role-specific policy skeleton; user duplicates it per agent if desired.
3. `TASK-BRIEF.md` — a one-task assignment skeleton.

The export must label every section as **user-owned**, state that Raven will never sync or overwrite it, and avoid claiming Raven requires it. It is a one-time handoff artifact, not a new bootstrap file.

**Recommended independent destination after user confirmation:**

`~/Raven-operator-policies/`

This is outside registered vaults and the Raven repository. It is a recommendation, not an automatic directory creation. The user may instead choose another private repo, a prompt/profile system, or a vault-local user-managed path.

---

## 3. Target Lite bootstrap shape

### Product-owned files only

```text
_meta/agents/
├── SCHEMA.md                 # Raven data/profile contract only
└── RAVEN-CONTRACT.md         # Raven tool/access/safety contract only
log.md                        # product audit/work log format
```

`RAVEN-CONTRACT.md` is the long-term accurate name. During the compatibility window, keep `_meta/agents/PROJECT-WORKFLOW.md` as a thin redirect that says this file moved and is no longer a policy document; do not silently remove it from existing vaults.

### User-owned files are external to bootstrap

```text
~/Raven-operator-policies/          # example only; selected by user
├── VAULT-POLICY.md                  # one vault’s governance
├── agents/
│   ├── researcher.md
│   ├── writer.md
│   └── reviewer.md
└── tasks/
    └── <task>.md
```

Raven must not scan, index, sync, checksum, render, or validate this directory. The user passes the relevant document to an agent directly.

---

## 4. Implementation sequence

### Task 1: Add the boundary ADR and a source-classification matrix

**Files:**
- Create: `_meta/decisions/adr-2026-07-14-raven-contract-and-user-agent-policy-boundary.md`
- Create: `docs/migrations/agent-policy-source-classification.md`

**Steps:**
1. State the ownership model from §1 as the decision.
2. Inventory every heading in the current `PROJECT-WORKFLOW.md` and the two policy-bearing `SCHEMA.md` areas.
3. Mark each entry: `Raven contract`, `LLM Wiki data profile`, `user policy`, or `remove as stale`.
4. Add an explicit backward-compatibility rule: no existing vault file is deleted or overwritten automatically.
5. Verify no new type taxonomy, entrypoint, dependency, or database is introduced.

**Acceptance:** Every current instruction has an owner; no line remains "shared by implication."

### Task 2: Produce the user-owned policy handoff bundle before deleting any guidance

**Files:**
- Create: `docs/migrations/agent-policy-bundle-v1.md`
- Create: `docs/migrations/agent-policy-extraction-map.md`

**Steps:**
1. Copy only the policy-classified material from Task 1 into the bundle, rewriting product assertions as user-selectable policy fields.
2. Keep practical prompts/options, but remove words implying Raven mandates them.
3. Add a front page explaining: copy this bundle to the user-selected independent destination; Raven will not read or update it.
4. Include a provenance map from each bundle section back to the current template headings, so no guidance disappears silently.
5. Have the user review the bundle content and choose its final independent destination before any copy there.

**Acceptance:** The user can operate an agent with the exported bundle even if Raven’s bootstrap files do not exist.

### Task 3: Create the thin Raven-owned contract template

**Files:**
- Create: `raven/core/templates/agent/RAVEN-CONTRACT.md`
- Modify: `raven/core/templates/agent/PROJECT-WORKFLOW.md`
- Modify: `raven/core/templates/agent/SCHEMA.md`
- Test: `tests/test_vault_create.py` plus a new focused contract-content test

**Steps:**
1. Write `RAVEN-CONTRACT.md` as a concise factual reference: SoT/index, MCP endpoint/discovery, permission modes, tool-enforced protected paths, audit/log semantics, and data-contract cross-references.
2. Remove operational policy sections from `PROJECT-WORKFLOW.md`; retain it temporarily as a compatibility redirect to `RAVEN-CONTRACT.md` and a statement that policy is user owned.
3. Remove the `agent write` column from the schema type taxonomy and move non-enforced review/autonomy wording into the exported bundle.
4. For each status/type behavior, verify code first. Keep only machine-enforced behavior in `SCHEMA.md`; move advisory behavior to the bundle.
5. Add tests that assert the new contract has no role assignment, mandatory curation cadence, save-signal mandate, or agent workflow prescription.

**Acceptance:** A fresh Raven contract explains what the software does, never tells an operator how to run their agents.

### Task 4: Stop root pointer-file takeover

**Files:**
- Modify: `raven/core/vault.py`
- Modify: `tests/test_vault_create.py`
- Add or modify: sync/create regression tests under `tests/`

**Steps:**
1. Remove `AGENT_POINTER_STUB_FILES`, `AGENT_POINTER_STUB_CONTENT`, and `_write_agent_pointer_stubs()` from the create/sync path.
2. Ensure `Vault.create()` and `sync_meta()` never create, overwrite, rename, or delete root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, or `.windsurfrules`.
3. Add parametrized tests that pre-create each of those files with user text, run vault creation/sync, and assert byte-for-byte preservation.
4. Update bootstrap documentation/tests to describe only the Raven-owned files.
5. Do not automatically remove pre-existing Raven-generated stubs. Add a future explicit, dry-run-only cleanup command proposal only if the user asks for it.

**Acceptance:** Raven cannot clobber an operator’s conventional agent instruction file.

### Task 5: Update guide APIs, freshness, and sync semantics without absorbing user policy

**Files to inspect/modify after contract test discovery:**
- `raven/mcp/tools/` guide-read/diff implementation
- `raven/api/` guide endpoints
- bootstrap freshness/verification implementation and tests
- `raven/core/vault.py`

**Steps:**
1. Update the guide whitelist to expose only `SCHEMA.md`, `RAVEN-CONTRACT.md`, and `log.md` as Raven-owned artifacts.
2. Preserve compatibility for `PROJECT-WORKFLOW.md` reads during the deprecation period, but mark it deprecated in the response rather than treating it as current policy.
3. Ensure freshness hashes cover only Raven-owned artifacts; never hash or inspect the external user-policy directory.
4. Make sync update only Raven-owned artifacts and only under the existing non-overwrite/explicit-force rules.
5. Add negative tests proving a user `AGENTS.md` and a user-chosen external policy path never appear in guide/freshness output.

**Acceptance:** Product maintenance remains possible without claiming authority over operator policy.

### Task 6: Migration and documentation

**Files:**
- Modify: `README.md`
- Modify: `_meta/index.md`
- Create: `_meta/changelog-v<next>.md`
- Modify: relevant CLI/API/MCP guide documentation

**Steps:**
1. Explain the two distinct layers using one short responsibility table.
2. Document the non-destructive migration path for existing vaults: existing workflow file remains; users may export policy; no auto rewrite/deletion.
3. Describe how an operator supplies independent policy to an agent: out-of-band prompt/profile/repository, not a Raven-owned feature.
4. Keep multi-agent language capability-oriented: Raven offers safety primitives; the operator determines coordination.
5. Do not mention or add vendor-specific configuration examples.

**Acceptance:** A new user can understand the boundary without reading source code; an existing user has a safe upgrade path.

### Task 7: Verification and release gate

**Commands (exact targets finalized after Task 5 discovery):**

```bash
scripts/.venv/bin/python -m pytest tests/test_vault_create.py -q
scripts/.venv/bin/python -m pytest tests/test_mcp_write_provenance.py -q
scripts/.venv/bin/python -m pytest tests -q
scripts/.venv/bin/python -m compileall -q raven
npm --prefix dashboard run build
git diff --check
```

**Additional behavioral checks:**

1. Create a temporary LLM-Wiki vault and verify it gets only the Raven-owned contract files and `log.md`.
2. Create all five conventional root instruction files with unique text; run create/sync; verify hashes are unchanged.
3. Verify guide/freshness endpoints expose only Raven-owned files.
4. Verify the extracted user-policy bundle is not copied into a new vault and has no runtime references.
5. Read the generated migration docs back and verify every extracted section has a source mapping.

**Commit discipline:** Logical commits only after user review of each meaningful unit; no implicit commit.

---

## Risks and mitigation

| Risk | Mitigation |
|---|---|
| Existing users rely on `PROJECT-WORKFLOW.md` | Keep compatibility redirect; do not delete automatically |
| Existing root stubs are user-modified | Never clean them automatically; explicit user-requested migration only |
| Moving prose causes product behavior/doc mismatch | Classify each claim against code before moving; tests enforce only actual contracts |
| User policy export accidentally becomes a new Raven template | Keep it in `docs/migrations/`, never add it to bootstrap map, guide allowlist, or sync logic |
| Multi-agent safety gets weakened | Preserve product primitives: capability modes, path guards, audit, idempotency, conflict signaling |
| Scope expands into a generic agent platform | ADR non-goals and tests prevent roles/tasks/policies from becoming Raven features |

---

## User decision required before implementation

The only required choice is where to place the extracted policy bundle after its review. Recommended default:

```text
~/Raven-operator-policies/
```

Raven will not create or manage that directory. If the user prefers a separate private repository, another agent-profile system, or a vault-local user folder, use that destination instead.

---

## Anti-Pattern Checklist (25개)

| # | 안티패턴 | 이 계획의 처리 | 상태 |
|---:|---|---|:---:|
| 1 | 다중 SoT | Markdown remains SoT; no new index/policy DB | ✅ |
| 2 | 폴더 조기 분리 | No content taxonomy migration; external policy is a handoff directory, not vault content structure | ✅ |
| 3 | orphan 즉시 경고 | Not changed | ✅ |
| 4 | backlinks 부재 | Not changed | ✅ |
| 5 | AI roadmap 부재 | LLM Wiki boundary is explicit; no chat feature introduced | ✅ |
| 6 | 신기술 우선 | Existing Markdown/Python/MCP mechanisms only | ✅ |
| 7 | 프로젝트명 종속 | Policy bundle is vault/operator-generic | ✅ |
| 8 | AI chat creep | No chat/orchestrator feature | ✅ |
| 9 | vendor lock-in | Vendor-neutral conventions; no vendor config files are generated | ✅ |
| 10 | SoT/Index 혼동 | Contract explicitly keeps Markdown SoT and DB query index separate | ✅ |
| 11 | slug 전략 부재 | Not changed | ✅ |
| 12 | `_meta/` 전면 면제 | Raven contract remains under `_meta/agents`; user policy stays outside product ownership | ✅ |
| 13 | vector 후보 미정 | Out of scope; no search redesign | ✅ |
| 14 | backup 우선순위 혼동 | No backup behavior change | ✅ |
| 15 | rigid tag taxonomy | No taxonomy expansion; user policy is not a tag contract | ✅ |
| 16 | universal outbound-link floor | Not changed | ✅ |
| 17 | broken/missing conflation | Not changed | ✅ |
| 18 | slug rename 정책 부재 | Existing policy remains; no automatic user-file migration | ✅ |
| 19 | graph library 미정 | Not changed | ✅ |
| 20 | MCP 권한 모델 부재 | Preserve and clarify capability modes as Raven contract | ✅ |
| 21 | 태그 정규화 부재 | Not changed | ✅ |
| 22 | 오래된 기술 기본값 | No dependency/version change | ✅ |
| 23 | vault/project framing 모호 | Ownership matrix distinguishes product, vault, operator, agent, task | ✅ |
| 24 | 응답/요구 범위 불일치 | Scope limited to policy ownership and handoff | ✅ |
| 25 | 2차 자가 리뷰 생략 | Run a source-to-code classification review before implementation; user reviews export before migration | ✅ |
