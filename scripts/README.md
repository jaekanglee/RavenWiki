# wiki/scripts

Build, lint, and maintain the `~/wiki` SQLite query index (`wiki.db`).

## Files

- `build_db.py` — scans the vault, parses frontmatter + wikilinks, builds `wiki.db` (SQLite v2.4 schema)
- `tests/` — pytest suite (TDD; covers schema, slug rules, wikilink intents, FTS5, backlinks, idempotency)
- `tests/fixtures/sample-vault/` — minimal vault used by the tests

## Setup

```bash
cd ~/wiki/scripts
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

`uv` is recommended (system `python3` may not ship pip). If you don't have `uv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

Build the real vault DB:

```bash
cd ~/wiki
python3 scripts/build_db.py            # default vault = ~/wiki
python3 scripts/build_db.py /path/to/vault   # explicit vault root
```

Build writes `wiki.db` in the vault root. The DB is gitignored — it's a regenerable index, not SoT.

## Test

```bash
cd ~/wiki/scripts
source .venv/bin/activate
pytest
```

## Schema (v2.4)

See `~/wiki/SCHEMA.md`. Tables: `pages`, `tags`, `links`. FTS5: `pages_fts`. Views: `v_backlinks`, `v_pages_with_tags`. Triggers keep `pages_fts` in sync with `pages`.

## Slug strategy (v2.2)

1. `slug:` from frontmatter wins
2. otherwise vault-relative path with `.md` stripped
3. `content/` prefix removed from the front (`content/llm-wiki` → `llm-wiki`)
4. `_meta/` prefix kept (`_meta/system-design` stays as-is)
5. All-caps slugs (e.g. `SCHEMA`, `RULES`) preserved verbatim

## Wikilink intent (v2.3)

- `[[link]]` → intent `auto`
- `[[link]]!` → intent `broken` (CRITICAL — explicit dead link)
- `[[link]]?` → intent `missing` (placeholder, INFO)

## Excluded paths

`raw/`, `_archive/`, `scripts/`, `node_modules/` are skipped on scan.
