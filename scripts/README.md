# wiki/scripts

Build, lint, and maintain the `~/wiki` SQLite query index (`wiki.db`).

## Files

- `build_db.py` — scans the vault, parses frontmatter + wikilinks, builds `wiki.db` (SQLite v2.4 schema)
- `lint.py` — read-only audit of `wiki.db` against 9 SCHEMA-defined rules; writes report to stdout, exits 1 on any CRITICAL
- `tests/` — pytest suite (TDD; covers schema, slug rules, wikilink intents, FTS5, backlinks, idempotency, lint rules)
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

Lint the DB (read-only — no markdown re-parse):

```bash
cd ~/wiki
python3 scripts/lint.py                # exit 1 if any CRITICAL issue
python3 scripts/lint.py --db /path/to/wiki.db --vault /path/to/vault
python3 scripts/lint.py --quiet        # summary line only
```

## Test

```bash
cd ~/wiki/scripts
source .venv/bin/activate
pytest
```

## Schema (v2.4)

See `~/wiki/SCHEMA.md`. Tables: `pages`, `tags`, `links`. FTS5: `pages_fts`. Views: `v_backlinks`, `v_pages_with_tags`. Triggers keep `pages_fts` in sync with `pages`.

## Lint rules (9)

Spec: `SCHEMA.md` §"Lint 자동 탐지" (L140-150). All read `wiki.db`; never re-parse markdown.

| # | Rule | Severity | Source |
|---|---|---|---|
| 1 | `broken_link` | 🔴 critical | `links.intent == 'broken'` |
| 2 | `missing_frontmatter` | 🔴 critical | `pages.created` NULL/empty |
| 3 | `missing_link` | 🔵 info | `links.intent == 'missing'` |
| 4 | `orphan` | 🟡 warning | `inbound==0 AND age > 7d` |
| 5 | `oversized` | 🟡 warning | `raw_content` lines > 200 |
| 6 | `weak_connection` | 🔵 info | `type ∈ {concept, person, tool}` AND `outbound < 2` (comparison exempt) |
| 7 | `custom_tag` | 🔵 info | tag not in core taxonomy (`CORE_TAGS` in `lint.py`) |
| 8 | `contested` | 🔵 info | `pages.contested == 1` |
| 9 | `stale` | 🔵 info | `updated > 90d` AND no recent `raw/` source |

`stale` accepts a `--vault` flag and suppresses the warning when the matching
`raw/<stem>.md` was modified within 90d (so re-renders don't age out).

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
