"""wikisys — Multi-vault wiki engine + CLI + API + GUI.

Layered architecture:
    wikisys.core      — pure engine (registry, vault, db, lint, link, export)
    wikisys.agents    — agent adapters (Hermes / Claude / Codex workers)
    wikisys.cli       — Typer-based CLI (vault ls/use/crud/lint)
    wikisys.api       — FastAPI HTTP server (GUI backend)
    dashboard/        — React 19 SPA (read + write UI)
"""
__version__ = "0.2.0"
