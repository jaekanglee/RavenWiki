"""wikisys.core — engine internals (vault registry + per-vault ops).

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
    log          — log.md (작업 이력) 관리 (v0.5.0+, 카파시 가이드)
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
]
