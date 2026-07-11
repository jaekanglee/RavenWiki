"""raven.core — engine internals (vault registry + per-vault ops).

Split:
    registry     — vault discovery (.registry.json + WIKI_VAULTS_DIR env override)
    vault        — single-vault handle (path, mode, owner, load .vault.json)
    db           — sqlite index (build_db, connect)
    lint         — vault-wide lint runner
    export       — static JSON export for the GUI
    link         — wikilink parse + audit
    slug         — vault-relative path validation (v0.3+)
    frontmatter  — unified FM parse/render/merge (v0.3+)
    archive      — _archive/ cleanup + restore (v0.4+)
    log          — log.md 작업 이력 관리
    contracts    — single write contract shared by all entrypoints (v0.6.2+)
"""
from .registry import VaultRegistry, registry, REGISTRY_PATH, VAULTS_ROOT
from .vault import Vault, resolve_active_vault
from . import db as db_module
from . import lint as lint_module
from . import export as export_module
from . import link as link_module
from . import slug as slug_module
from . import frontmatter as frontmatter_module
from . import archive as archive_module
from . import log as log_module
from . import contracts as contracts_module
from . import garden as garden_module
from . import recommend as recommend_module
from . import draft as draft_module

__all__ = [
    "VaultRegistry",
    "registry",
    "REGISTRY_PATH",
    "VAULTS_ROOT",
    "Vault",
    "resolve_active_vault",
    "db_module",
    "lint_module",
    "export_module",
    "link_module",
    "slug_module",
    "frontmatter_module",
    "archive_module",
    "log_module",
    "contracts_module",
    "garden_module",
    "recommend_module",
    "draft_module",
]
