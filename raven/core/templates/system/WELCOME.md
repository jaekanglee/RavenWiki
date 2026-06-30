---
title: Welcome to your Raven vault
created: 2026-06-30
updated: 2026-06-30
type: rule
audience: human
confidence: high
---

# Welcome to your Raven vault

> **You are looking at a plain markdown vault.** Raven is an Obsidian-style
> knowledge tool: free-form notes, no rigid structure, you decide what
> goes where.

## 3 things to know

### 1. Start writing — any file, any folder
Your vault root has a `content/` folder. Create notes, sub-folders, projects —
anything goes. Raven indexes them automatically when you run `raven build`.

### 2. Open the dashboard
```bash
python -m raven.api       # → http://127.0.0.1:8765
cd dashboard && npm run dev  # → http://localhost:5173
```
Or use the CLI: `raven page new`, `raven page ls`, `raven page get`.

### 3. (Optional) Enable LLM Wiki patterns
By default, this is a human-first vault — no agent required. If you want
LLM Wiki-style features (raw/ source separation, log.md work log, agent
co-write), create `_meta/system/features.json`:

```json
{ "llm_wiki": true }
```

This unlocks:
- `raw/` folder as immutable source area
- `log.md` as append-only work log
- `_meta/agents/` for agent instructions
- Lint checks for LLM Wiki conventions

To turn it off again, set `llm_wiki: false` or delete the file. Your existing
notes stay untouched.

## Need more structure?

If you want the full Lite bootstrap (SCHEMA.md / RULES.md / AGENTS.md for
strict conventions), re-create with `--profile llm-wiki`:

```bash
raven vault create <name> <path> --profile llm-wiki
```

Or copy templates manually:

```bash
raven meta sync --lite   # copies SCHEMA + RULES + AGENTS into _meta/system/
```

## That's it

Raven is a tool — you decide how to use it. Have fun. 🪶
