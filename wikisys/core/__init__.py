"""wikisys.core — engine internals (vault registry + per-vault ops).

Split:
    registry — vault discovery (.registry.json + WIKI_VAULTS_DIR env override)
    vault    — single-vault handle (path, mode, owner, load .vault.json)
    db       — sqlite index (build_db, lint)
    link     — wikilink parse + rewrite
    export   — static JSON export for the GUI
"""
from .registry import VaultRegistry, registry, REGISTRY_PATH, VAULTS_ROOT
from .vault import Vault, resolve_active_vault

__all__ = [
    "VaultRegistry",
    "registry",
    "REGISTRY_PATH",
    "VAULTS_ROOT",
    "Vault",
    "resolve_active_vault",
]
