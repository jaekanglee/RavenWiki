# Wiki Dashboard

React 19 SPA for browsing the Wiki vault.

## Stack
- **Vite 6** + **TypeScript 5.6** + **React 19**
- **Tailwind CSS 4** (via `@tailwindcss/vite`)
- **react-router-dom 7** — 4 routes (Home, Page, Search, Graph)
- **@xyflow/react 12** — graph view
- **MiniSearch 7** — BM25 client-side search
- **react-markdown 9** + remark/rehype plugins (gfm, math, katex, highlight)
- **vite-plugin-pwa** — auto-update service worker

## Architecture
Dashboard is a **static site**. It reads JSON files under `public/api/`:
- `index.json` — list of all pages (sidebar tree source)
- `graph.json` — nodes + edges for the graph view
- `page-<slug>.json` — individual page payload (content, tags, backlinks)
- `search.idx.json` — pre-built MiniSearch index (TODO: emit from export)

`scripts/export_static.py` reads `wiki.db` (SQLite) and emits all of the above
to `dashboard/public/api/`.

## Routes
- `/` — Home (recent edits, total page count)
- `/page/:slug` — PageView (markdown + backlinks)
- `/search` — full-page BM25 search
- `/graph` — interactive node graph (click → page)

## Wikilinks
`[[some/page]]` is rewritten to `<a href="/page/some/page">` by a custom
remark plugin (`src/lib/wikilink.ts`). Intent chars `!` and `?` are preserved.

## Develop
```bash
# 1. export vault data
cd scripts
.venv/bin/python export_static.py
cd ../dashboard

# 2. install + dev server
npm install
npm run dev  # http://localhost:5173
```

## Build
```bash
npm run build  # → dist/ (deploy to Caddy)
```

## Test
```bash
npm run test
```

## Notes
- This is a **read-only** client. Edits go through the MCP server
  (`mcp/cli.py --write` / `--admin`).
- Service worker is `autoUpdate` — refresh after deploy.
- PWA icon is the emoji 📚 as inline SVG.
