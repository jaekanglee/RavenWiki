"""raven.agents — adapters for non-human vault users (Hermes/Claude/Codex).

Why this exists:
    Humans use the CLI (`raven ...`) or the GUI (browser). Agents (LLM
    workers, codegen bots, log summarizers) use Python directly. They need:
      - a single importable surface (no subprocess, no shell escaping)
      - scope: "this agent only touches this vault(s)"
      - provenance: "who wrote this and when" — frontmatter `agents:` field
      - batch ops: ingest many pages in one call (single vault write, single
        DB rebuild)

Public surface (all under raven.agents):
    Agent          — handle for one named agent + scope
    AgentVault     — vault-bound operations available to agents
    Result         — small typed return for write operations
"""
from .agent import Agent, AgentVault, AgentScope, Provenance

__all__ = ["Agent", "AgentVault", "AgentScope", "Provenance"]
