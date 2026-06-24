# Wiki MCP Server

Model Context Protocol server for the wiki vault. Exposes 7 tools + 5 resources
backed by `wiki.db` (SQLite, SCHEMA v2.4).

## Install

```bash
cd /Users/jaekanglee/Desktop/Dev/Project/Wiki
source scripts/.venv/bin/activate
pip install "mcp[cli]>=1.0"      # FastMCP SDK (transitively brings httpx, etc.)
pip install python-frontmatter    # already in scripts/pyproject.toml
```

## Usage

### stdio (local Hermes / desktop MCP client)

```bash
# Default — read-only
python -m mcp.server

# With write access (wiki_update / wiki_ingest)
python -m mcp.server --mode write

# With admin access (+ wiki_delete / wiki_rename)
python -m mcp.server --mode admin
```

To run as a module from the vault root:

```bash
cd /Users/jaekanglee/Desktop/Dev/Project/Wiki
scripts/.venv/bin/python -m mcp.server --mode read
```

### HTTP (Tailscale remote)

```bash
python -m mcp.server --transport http --host 127.0.0.1 --port 8765 --mode read
# Streamable-HTTP transport; bind to Tailscale IP for remote access.
```

### CLI flags

| Flag | Default | Notes |
|---|---|---|
| `--transport` | `stdio` | `stdio` (local) or `http` (remote) |
| `--host` | `127.0.0.1` | HTTP bind host (use Tailscale IP for remote) |
| `--port` | `8765` | HTTP bind port |
| `--vault` | parent of `mcp/` | vault root path |
| `--mode` | `read` | `read` / `write` / `admin` |

## Tools (7)

### Read (always available)

- `wiki_search(query: str, top_k: int = 10) -> list[dict]` — FTS5 BM25 search.
- `wiki_get_page(slug: str) -> dict | None` — single page with content, frontmatter, backlinks, outbound links, tags.
- `wiki_lint() -> dict` — run `scripts/lint.py` and return `{critical, warning, info, total, issues[]}`.
- `wiki_graph(project: str | None = None, fmt: str = "json") -> dict` — full link graph; optional substring filter on slug.
- `wiki_log(tail_n: int = 20) -> list[dict]` — last N non-empty log.md lines.

### Write (requires `--mode write` or `--admin`)

- `wiki_update(slug: str, content: str, frontmatter: dict | None = None) -> dict` — overwrite a vault page (slug must include a category, e.g. `concepts/wiki`).
- `wiki_ingest(source: str, project: str | None = None, mode: str = "auto") -> dict` — copy a raw source into `<vault>/raw/<project>/`.

### Admin (requires `--mode admin`)

- `wiki_delete(slug: str) -> dict` — *(M3 stub: returns `{ok: false, message: "not yet implemented"}`)*
- `wiki_rename(old_slug: str, new_slug: str) -> dict` — *(M3 stub: returns `{ok: false, message: "not yet implemented"}`)*

## Resources (5, always read-only)

- `wiki://index` — full page catalog.
- `wiki://page/{slug}` — one page with envelope `{found, slug, page}`.
- `wiki://graph` — full link graph + counts.
- `wiki://log/recent` — last 5000 chars of `log.md`.
- `wiki://schema` — raw `SCHEMA.md` text.

## Permission model

| Mode | Tools registered |
|---|---|
| `read` (default) | search, get_page, lint, graph, log |
| `write` | + update, ingest |
| `admin` | + delete, rename |

Permission checks live in `mcp/tools/__init__.py::check_permission()` and are
also enforced inside each write tool via `VaultContext.require()`.

## Architecture

```
mcp/
├── __init__.py
├── server.py        # CLI entry, FastMCP bootstrap, transport, mode gating
├── resources.py     # 5 wiki:// resources
├── db.py            # read-only sqlite helpers (single connection per call)
├── tools/
│   ├── __init__.py  # VaultContext, PermissionError_, check_permission
│   ├── read.py      # 5 read tools (search / get_page / lint / graph / log)
│   └── write.py     # 2 write tools (update / ingest)
└── tests/
    ├── conftest.py
    ├── test_db.py
    └── test_tools.py
```

## Tests

```bash
cd /Users/jaekanglee/Desktop/Dev/Project/Wiki
scripts/.venv/bin/python -m pytest mcp/tests/ -v
```

Tests run against the live `wiki.db`. If absent, `pytest.skip` is invoked
from the `wiki_db` fixture.

## Notes on the `mcp` namespace

Our local package is named `mcp` (sibling of `wiki.db`). The real MCP SDK
(`mcp[cli]` ≥ 1.x) also ships an `mcp` package and provides `mcp.server.fastmcp.FastMCP`.

`mcp/server.py` handles the namespace collision by deferring the FastMCP
import to runtime and temporarily un-registering our local `mcp.*` from
`sys.modules` so the SDK can be loaded. The local package is restored
afterwards so tool body imports (`from mcp.tools import …`) still resolve.

If you add new tools or resources, prefer placing imports **inside** the
register function rather than at module top level to avoid this dance.