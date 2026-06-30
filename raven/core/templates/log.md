# Vault Log

> Chronological record of all vault actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, create, archive, delete, lint, build, migrate, chore
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.
>
> Grep tip: `grep "^## \[" log.md | tail -5` → last 5 entries.

## [YYYY-MM-DD] create | log.md initialized
- reason: vault created via Lite bootstrap
- files: [log.md]