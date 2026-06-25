"""wikisys.core — engine internals (vault registry + per-vault ops).

Split:
    registry — vault discovery (.registry.json + WIKI_VAULTS_DIR env override)
    vault    — single-vault handle (path, mode, owner, load .vault.json)
    db       — sqlite index (build_db, connect)
    lint     — vault-wide lint runner
    export   — static JSON export for the GUI
    link     — wikilink parse + audit
"""
from .registry import VaultRegistry, registry, REGISTRY_PATH, VAULTS_ROOT
from .vault import Vault, resolve_active_vault
from . import db as db_module
from . import lint as lint_module
from . import export as export_module
from . import link as link_module

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
]
