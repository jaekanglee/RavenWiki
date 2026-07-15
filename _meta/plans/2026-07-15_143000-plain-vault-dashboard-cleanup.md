# Plain Vault + Dashboard Cleanup Implementation Plan

**Goal:** Make new Raven vaults plain Markdown workspaces by removing automatic agent-policy/bootstrap content and the Dashboard controls that manage it.

**Scope for this unit:** Phase 1 only. Retain current vault metadata and runtime sidecars; their external-state migration is a separate structural unit.

## Tasks

1. Add a failing core test: default `Vault.create()` creates only the registry metadata and `content/`, never `_meta/`, `log.md`, welcome files, or Git state.
2. Change `raven/core/vault.py` creation defaults and remove bootstrap, sync/verify, automatic log, and automatic Git initialization behavior.
3. Remove API/CLI/MCP guide/bootstrap/freshness surfaces and their tests; retain normal MCP page/search/graph tools.
4. Add a failing Dashboard source-contract test, then remove the guide route/viewer, VaultManage guide/bootstrap UI, and guide API client helpers.
5. Simplify `NewVaultWizard`: no profile/bootstrap/MCP setup or policy-filled index document; redirect a new empty vault to the normal empty-state flow.
6. Update relevant product documentation/changelog and run Python + Dashboard test/typecheck suites.

## Deferred deliberately

- Move `.vault.json`, `wiki.db`, `.mcp/`, and `.graph_positions.json` outside the vault.
- Rework log/lock/archive/draft surfaces beyond removing bootstrap dependencies.
- Existing-vault cleanup/migration command and deletion of user-owned legacy files.
