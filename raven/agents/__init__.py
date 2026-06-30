"""raven.agents — adapters for non-human (LLM agent) vault users with scope + provenance.

Why this exists:
    Humans use the CLI (`raven ...`) or the GUI (browser). Agents (any LLM
    worker, codegen bot, log summarizer — vendor-neutral) use Python directly.
    They need:
      - a single importable surface (no subprocess, no shell escaping)
      - scope: "this agent only touches this vault(s)"
      - provenance: "who wrote this and when" — frontmatter `agents:` field
      - batch ops: ingest many pages in one call (single vault write, single
        DB rebuild)

Public surface (all under raven.agents):
    Agent          — handle for one named agent + scope
    AgentVault     — vault-bound operations available to agents
    Result         — small typed return for write operations

v0.6.36+: vendor-neutral. raven does not bake specific vendor names into this
module. Any LLM worker (CLI, IDE assistant, autonomous agent, etc.) can use
this adapter as long as it can call Python directly.
"""
from .agent import Agent, AgentVault, AgentScope, Provenance

__all__ = ["Agent", "AgentVault", "AgentScope", "Provenance"]
