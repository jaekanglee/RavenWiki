# Wiki Dashboard

React 19 SPA for browsing and editing Raven vaults.

## Stack
- **Vite 6** + **TypeScript 5.6** + **React 19**
- **Tailwind CSS 4** (via `@tailwindcss/vite`)
- **react-router-dom 7** — 4 routes (Home, Page, Search, Graph)
- **@xyflow/react 12** — graph view
- **MiniSearch 7** — BM25 client-side search
- **react-markdown 9** + remark/rehype plugins (gfm, math, katex, highlight)
- **vite-plugin-pwa** — auto-update service worker

## Architecture
Dashboard is an **API-backed read-write app**. It talks to `python -m raven.api`
for vault selection, page CRUD, folders, graph, search, lint, log, and digest
views.

The older static JSON export path is legacy. `dashboard/dist/api/` and
`dashboard/public/api/` may exist for deploy/static export compatibility, but
the normal development loop uses `/api/vaults/...`.

## Routes
- `/` — Home (vault cards, recent edits, stats)
- `/page/:slug` — PageView (markdown, backlinks, edit/delete)
- `/search` — full-page BM25 search
- `/graph` — interactive node graph (click → page)
- `/log` — work log
- `/lint` — lint results
- `/vaults` — vault management

## Wikilinks
`[[some/page]]` is rewritten to `<a href="/page/some/page">` by a custom
remark plugin (`src/lib/wikilink.ts`). Intent chars `!` and `?` are preserved.

## Develop
```bash
# 1. start API
python -m raven.api

# 2. start Dashboard
cd dashboard
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
- This is the human-facing app surface, roughly the role Obsidian's desktop app
  plays for a local vault.
- Edits go through the Raven HTTP API and core write contracts.
- Service worker is `autoUpdate` — refresh after deploy.
