"""raven — Multi-vault wiki engine + CLI + API + GUI.

Layered architecture:
    raven.core      — pure engine (registry, vault, db, lint, link, export)
    raven.agents    — agent adapters (LLM workers with scope + provenance, vendor-neutral)
    raven.cli       — Typer-based CLI (vault ls/use/crud/lint)
    raven.api       — FastAPI HTTP server (GUI backend)
    dashboard/        — React 19 SPA (read + write UI)
"""
__version__ = "0.5.7"
