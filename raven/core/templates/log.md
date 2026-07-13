# Vault Log

> Chronological record of vault actions. Append-only.
> Format: `## [YYYY-MM-DD] action | 사람이 이해할 작업 요약`
> MCP write: `summary`에는 무엇이 달라졌는지, `reason`에는 왜 바꿨는지를 한 줄로 남긴다.
> 경로·코드·건수만 제목에 나열하지 말고, actor/path/idempotency key는 detail 감사 정보로 둔다.
> Actions: ingest, update, create, archive, delete, lint, build, migrate, rename, chore
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.
>
> Grep tip: `grep "^## \[" log.md | tail -5` → last 5 entries.

## [YYYY-MM-DD] create | log.md initialized
- reason: vault created via Lite bootstrap
- files: [log.md]