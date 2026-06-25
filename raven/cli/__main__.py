"""raven CLI entrypoint — `python -m raven.cli ...` or installed `raven ...`.

Design:
    - Typer sub-apps: `vault`, `page`, `link`, `build`, `export`
    - shared resolver: `--vault NAME` overrides active vault
    - all output is human-readable text + small JSON for machine consumers
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from raven.core import registry, resolve_active_vault, VAULTS_ROOT, REGISTRY_PATH
from raven.core import db_module, lint_module, export_module, link_module
from raven.core import slug_module, frontmatter_module, archive_module
from raven.core import log_module
from raven import migrate as migrate_module
from raven.core.vault import Vault

app = typer.Typer(
    name="raven",
    help="Multi-vault wiki engine — CLI for vault mgmt + page CRUD + linking.",
    no_args_is_help=True,
    add_completion=False,
)

vault_app = typer.Typer(help="Vault discovery / creation / registration.")
page_app = typer.Typer(help="Page CRUD inside the active vault.")
link_app = typer.Typer(help="Wikilink inspection.")
meta_app = typer.Typer(help="Vault meta docs (SCHEMA.md, RULES.md) management.")
archive_app = typer.Typer(help="Vault _archive/ management (list/clean/restore).")
log_app = typer.Typer(help="log.md (작업 이력) 관리 — 카파시 LLM Wiki 패턴.")
lint_app = typer.Typer(help="lint 12개 (카파시 가이드) — broken/orphan/contradictions/stale 등.")
migrate_app = typer.Typer(help="vault 마이그레이션 — lint 5 카테고리 dry-run/apply (v0.5.2+).")
app.add_typer(vault_app, name="vault")
app.add_typer(page_app, name="page")
app.add_typer(link_app, name="link")
app.add_typer(meta_app, name="meta")
app.add_typer(archive_app, name="archive")
app.add_typer(log_app, name="log")
app.add_typer(lint_app, name="lint")
app.add_typer(migrate_app, name="migrate")


# ────────────────────────── top-level ──────────────────────────


@app.command()
def where() -> None:
    """Show current raven config (vaults root, registry, active vault)."""
    typer.echo(f"📁 vaults root: {VAULTS_ROOT()}")
    typer.echo(f"📋 registry:    {REGISTRY_PATH()}")
    reg = registry()
    vaults = reg.list()
    if not vaults:
        typer.echo("⚠️  no vaults registered. Create one with `raven vault create <name> <path>`.")
        return
    typer.echo(f"\n🔐 active:      {reg._data.get('default', '(unset)')} (set with `raven vault use <name>`)")
    typer.echo(f"\n📚 vaults ({len(vaults)}):")
    for v in vaults:
        marker = "★" if v.default else " "
        typer.echo(f"  {marker} {v.name:14s} {v.mode:8s} {v.path}")


# ────────────────────────── vault ──────────────────────────


@vault_app.command("list")
def vault_list(
    json_out: bool = typer.Option(False, "--json", help="machine-readable output"),
) -> None:
    """List all vaults in the registry."""
    reg = registry()
    vaults = reg.list()
    if json_out:
        typer.echo(json.dumps([{
            "name": v.name,
            "path": str(v.path),
            "mode": v.mode,
            "owner": v.owner,
            "default": v.default,
        } for v in vaults], indent=2, ensure_ascii=False))
        return
    if not vaults:
        typer.echo("(empty — create with `raven vault create <name> <path>`)")
        return
    for v in vaults:
        marker = "★" if v.default else " "
        typer.echo(f"  {marker} {v.name:14s} {v.mode:8s} {v.path}")


@vault_app.command("use")
def vault_use(name: str) -> None:
    """Set registry default to <name>."""
    if registry().set_default(name):
        typer.echo(f"✅ default → {name}")
    else:
        typer.echo(f"❌ vault {name!r} not found", err=True)
        raise typer.Exit(1)


@vault_app.command("info")
def vault_info(name: Optional[str] = typer.Argument(None, help="vault name (default: active)")) -> None:
    """Show metadata + content stats for one vault."""
    v = resolve_active_vault(name)
    pages = list(v.content_root.rglob("*.md"))
    typer.echo(f"📚 {v.meta.name}")
    typer.echo(f"   path:        {v.root}")
    typer.echo(f"   mode:        {v.meta.mode}")
    typer.echo(f"   owner:       {v.meta.owner}")
    typer.echo(f"   created:     {v.meta.created or '(unknown)'}")
    typer.echo(f"   pages:       {len(pages)} .md files")
    typer.echo(f"   db present:  {v.db_path.exists()}")


@vault_app.command("create")
def vault_create(
    name: str,
    path: str,
    mode: str = typer.Option("personal", help="personal | shared | agent"),
    owner: str = typer.Option("user"),
    description: str = typer.Option(""),
    bootstrap: bool = typer.Option(True, "--bootstrap/--no-bootstrap", help="copy SCHEMA/RULES templates into _meta/"),
) -> None:
    """Create new vault on disk and register it."""
    v = Vault.create(
        name=name,
        path=Path(path).expanduser(),
        mode=mode,
        owner=owner,
        description=description,
        bootstrap=bootstrap,
    )
    if bootstrap:
        typer.echo(f"✅ vault created: {v.meta.name} → {v.root}")
        typer.echo(f"   bootstrapped: content/, _meta/{{SCHEMA.md, RULES.md}}")
    else:
        typer.echo(f"✅ vault registered (no bootstrap): {v.meta.name} → {v.root}")


@vault_app.command("register")
def vault_register(
    name: str,
    path: str,
    mode: str = typer.Option("personal"),
    owner: str = typer.Option("user"),
) -> None:
    """Register an existing folder as a vault (no file changes)."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        typer.echo(f"❌ not a directory: {p}", err=True)
        raise typer.Exit(1)
    from raven.core.registry import VaultMeta
    meta = VaultMeta(name=name, path=p, mode=mode, owner=owner)
    registry().add(meta)
    typer.echo(f"✅ registered: {name} → {p}")


@vault_app.command("clone")
def vault_clone(
    src: str = typer.Argument(..., help="source vault name"),
    name: str = typer.Argument(..., help="new vault name"),
    path: str = typer.Argument(..., help="absolute path for new vault"),
    mode: str = typer.Option(None, "--mode", help="override mode (default: copy from src)"),
    owner: str = typer.Option(None, "--owner", help="override owner (default: copy from src)"),
    no_meta: bool = typer.Option(False, "--no-meta", help="don't copy _meta/ from src"),
) -> None:
    """Clone an existing vault (content + _meta) to a new vault.

    Skips _archive/ and wiki.db. Useful for templates, sandboxes, branches.
    """
    src_meta = registry().get(src)
    if src_meta is None:
        typer.echo(f"❌ source vault {src!r} not found", err=True)
        raise typer.Exit(1)
    if registry().get(name) is not None:
        typer.echo(f"❌ name {name!r} already registered", err=True)
        raise typer.Exit(1)
    src_v = Vault.load(src_meta)
    try:
        new_v = Vault.clone(
            src=src_v,
            name=name,
            path=Path(path).expanduser(),
            mode=mode,
            owner=owner,
            copy_meta=not no_meta,
        )
    except (FileExistsError, ValueError) as e:
        typer.echo(f"❌ clone failed: {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✅ cloned: {src!r} → {name!r} at {new_v.root}")
    if no_meta:
        typer.echo("   (skipped _meta/ — run `raven meta sync` later to populate)")


# alias for `vault import` (same as clone)
@vault_app.command("import")
def vault_import_alias(
    src: str = typer.Argument(...),
    name: str = typer.Argument(...),
    path: str = typer.Argument(...),
    mode: str = typer.Option(None, "--mode"),
    owner: str = typer.Option(None, "--owner"),
    no_meta: bool = typer.Option(False, "--no-meta"),
) -> None:
    """Alias for `vault clone` (same behavior)."""
    vault_clone(src=src, name=name, path=path, mode=mode, owner=owner, no_meta=no_meta)


@vault_app.command("remove")
def vault_remove(name: str, force: bool = typer.Option(False, "--force")) -> None:
    """Unregister a vault (does NOT delete the folder)."""
    if not force:
        confirm = typer.confirm(f"Unregister vault {name!r}? Files will remain on disk.", default=False)
        if not confirm:
            raise typer.Abort()
    if registry().remove(name):
        typer.echo(f"✅ unregistered: {name}")
    else:
        typer.echo(f"❌ not found: {name}", err=True)
        raise typer.Exit(1)


# ────────────────────────── page ──────────────────────────


def _resolve_vault_or_die(name: Optional[str]) -> Vault:
    try:
        return resolve_active_vault(name)
    except Exception as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)


@page_app.command("ls")
def page_ls(
    type_filter: Optional[str] = typer.Option(None, "--type", "-t"),
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List pages in active vault."""
    v = _resolve_vault_or_die(vault)
    pages = sorted(v.content_root.rglob("*.md"))
    rows = []
    for p in pages:
        slug = str(p.relative_to(v.root)).replace(".md", "")
        # read frontmatter
        try:
            text = p.read_text()
        except Exception:
            continue
        title = ""
        ptype = ""
        if text.startswith("---"):
            try:
                fm = text.split("---", 2)[1]
                for line in fm.splitlines():
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip()
                    elif line.startswith("type:"):
                        ptype = line.split(":", 1)[1].strip()
            except Exception:
                pass
        if type_filter and ptype != type_filter:
            continue
        rows.append({"slug": slug, "title": title, "type": ptype})
    if json_out:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        typer.echo("(no pages)")
        return
    for r in rows:
        marker = f"[{r['type']}]" if r["type"] else "[?]"
        typer.echo(f"  {marker:13s} {r['slug']:40s} {r['title']}")


@page_app.command("get")
def page_get(
    slug: str,
    vault: Optional[str] = typer.Option(None, "--vault"),
) -> None:
    """Show one page (frontmatter + body)."""
    v = _resolve_vault_or_die(vault)
    fp = v.root / f"{slug}.md"
    if not fp.exists():
        typer.echo(f"❌ not found: {slug}", err=True)
        raise typer.Exit(1)
    typer.echo(fp.read_text())


@page_app.command("new")
def page_new(
    slug: str,
    title: str = typer.Option(..., "--title", help="page title"),
    type_: str = typer.Option("concept", "--type", help="concept|person|comparison|project|tool|rule|query|journal"),
    tags: str = typer.Option("", help="comma-separated tags"),
    vault: Optional[str] = typer.Option(None, "--vault"),
) -> None:
    """Create a new page with frontmatter + empty body.

    Slug handling (v0.3+):
        - 'foo' → 'content/foo' (auto prefix when no '/' in slug)
        - 'meta/welcome' → '_meta/welcome' (explicit prefix preserved)
        - Invalid slugs (.., ~, absolute, NUL, ':') are rejected.
    """
    v = _resolve_vault_or_die(vault)
    # R3: auto-prefix short names
    normalized = slug_module.normalize_prefix(slug)
    # R1: validate (raises SlugError on bad path)
    try:
        safe_path = slug_module.validate(normalized, vault_root=v.root)
    except slug_module.SlugError as e:
        typer.echo(f"❌ invalid slug: {e}", err=True)
        raise typer.Exit(1)
    fp = safe_path.with_suffix(".md")
    if fp.exists():
        typer.echo(f"❌ exists: {normalized}", err=True)
        raise typer.Exit(1)
    fp.parent.mkdir(parents=True, exist_ok=True)
    # R2: use unified frontmatter.render() — consistent with API/Agent
    today = __import__("datetime").date.today().isoformat()
    meta = frontmatter_module.merge(
        {},
        {
            "title": title,
            "type": type_,
            "tags": tags,
            "created": today,
            "updated": today,
        },
    )
    body = f"# {title}\n"
    rendered = frontmatter_module.render(meta, body)
    fp.write_text(rendered, encoding="utf-8")
    # v0.5.1+: log.md에 create entry 자동 append
    try:
        log_module.append(
            v,
            action="create",
            subject=normalized,
            files=[normalized],
            note=f"type={type_}",
        )
    except Exception:
        pass
    typer.echo(f"✅ created: {normalized}")


@page_app.command("delete")
def page_delete(
    slug: str,
    vault: Optional[str] = typer.Option(None, "--vault"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Archive page (moves to _archive/<original-path>-<timestamp>.md)."""
    v = _resolve_vault_or_die(vault)
    # R1: validate slug
    try:
        safe_path = slug_module.validate(slug, vault_root=v.root)
    except slug_module.SlugError as e:
        typer.echo(f"❌ invalid slug: {e}", err=True)
        raise typer.Exit(1)
    fp = safe_path.with_suffix(".md")
    if not fp.exists():
        typer.echo(f"❌ not found: {slug}", err=True)
        raise typer.Exit(1)
    if not force:
        confirm = typer.confirm(f"Archive {slug!r}?", default=False)
        if not confirm:
            raise typer.Abort()
    import datetime as _dt
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = v.root / "_archive"
    archive_dir.mkdir(exist_ok=True)
    # mirror original path under _archive (preserves nested structure)
    rel = fp.relative_to(v.root)
    dest = archive_dir / rel.parent / f"{rel.stem}-{ts}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    fp.rename(dest)
    # v0.5.1+: log.md에 archive entry 자동 append
    try:
        log_module.append(
            v,
            action="archive",
            subject=slug,
            files=[str(dest.relative_to(v.root))],
            note=f"원본: {slug}",
        )
    except Exception:
        pass
    typer.echo(f"✅ archived: {slug} → {dest.relative_to(v.root)}")


# ────────────────────────── meta (vault _meta/ management) ──────────────────────────


@meta_app.command("sync")
def meta_sync(
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
    with_log: bool = typer.Option(False, "--with-log", help="vault 루트에 log.md + raven-policy.md도 복사 (기존 파일 있으면 skip)"),
) -> None:
    """Re-copy SCHEMA.md / RULES.md from raven templates into _meta/.

    --with-log: vault 루트에 log.md + raven-policy.md도 복사 (없을 때만).
                기존 vault 보강용 (v0.5.0+, 카파시 가이드 도입 시).
    """
    v = _resolve_vault_or_die(vault)
    result = v.sync_meta(with_log=with_log)
    if json_out:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if result["copied"]:
        typer.echo(f"✅ synced: {', '.join(result['copied'])}")
    if result["errors"]:
        typer.echo(f"⚠️  errors / skipped:", err=True)
        for err in result["errors"]:
            typer.echo(f"   {err['file']}: {err['error']}", err=True)
    if not result["copied"] and not result["errors"]:
        typer.echo("⚠️  no templates found (package install broken?)")
    if with_log:
        typer.echo("💡 log.md + raven-policy.md 보강 완료 (없던 vault에 한해)")


# ────────────────────────── archive (vault _archive/ mgmt) ──────────────────────────


def _format_archive_entry(e) -> str:
    age = f"{e.age_days:.1f}d" if e.age_days is not None else "  ?  "
    ts = e.timestamp.strftime("%Y-%m-%d %H:%M") if e.timestamp else "(no ts)     "
    return f"  {age:>6s}  {ts}  {e.rel_path}  →  {e.original_slug}"


@archive_app.command("list")
def archive_list(
    vault: Optional[str] = typer.Option(None, "--vault"),
    older_than: int = typer.Option(0, "--older-than", help="only show entries older than N days (0 = all)"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List all archived files in the active vault."""
    v = _resolve_vault_or_die(vault)
    entries = archive_module.list_archived(v)
    if older_than > 0:
        entries = [e for e in entries if e.age_days is not None and e.age_days > older_than]
    if json_out:
        typer.echo(json.dumps([e.to_dict() for e in entries], indent=2, ensure_ascii=False))
        return
    if not entries:
        typer.echo(f"📭 {v.meta.name}: no archived files" + (f" older than {older_than}d" if older_than else ""))
        return
    typer.echo(f"📦 {v.meta.name} — {len(entries)} archived files:")
    for e in entries:
        typer.echo(_format_archive_entry(e))


@archive_app.command("clean")
def archive_clean(
    vault: Optional[str] = typer.Option(None, "--vault"),
    older_than: int = typer.Option(30, "--older-than", help="delete entries older than N days (0 = all)"),
    apply: bool = typer.Option(False, "--apply", help="actually delete (default: dry-run)"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Delete old archived files. Dry-run by default — use --apply to actually delete."""
    v = _resolve_vault_or_die(vault)
    result = archive_module.clean_archived(v, older_than_days=older_than, apply=apply)
    if json_out:
        typer.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    target_label = "deleted" if apply else "would delete"
    target_list = result.deleted if apply else result.would_delete
    if not target_list:
        typer.echo(f"📭 {v.meta.name}: nothing to clean (older-than={older_than}d)")
        return
    if not apply:
        typer.echo(f"🔍 DRY-RUN: {len(target_list)} files would be deleted (use --apply to proceed):")
    else:
        typer.echo(f"✅ cleaned {len(target_list)} files:")
    for e in target_list:
        typer.echo(_format_archive_entry(e))
    if result.errors:
        typer.echo(f"❌ {len(result.errors)} errors:", err=True)
        for err in result.errors:
            typer.echo(f"   {err['path']}: {err['error']}", err=True)


@archive_app.command("restore")
def archive_restore(
    archive_path: str = typer.Argument(..., help="vault-relative archive path, e.g. _archive/content/foo-20260625-123456.md"),
    vault: Optional[str] = typer.Option(None, "--vault"),
) -> None:
    """Restore an archived file back to its original slug location."""
    v = _resolve_vault_or_die(vault)
    result = archive_module.restore_archived(v, archive_path)
    if result.ok:
        typer.echo(f"✅ restored: {archive_path} → {result.restored_to}")
    else:
        typer.echo(f"❌ {result.error}", err=True)
        raise typer.Exit(1)


# ────────────────────────── link ──────────────────────────


@link_app.command("check")
def link_check(
    slug: Optional[str] = typer.Option(None, help="limit to one page (else whole vault)"),
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Find broken / missing wikilinks in the active vault."""
    v = _resolve_vault_or_die(vault)
    broken = link_module.find_broken(v, slug=slug)
    missing = link_module.find_missing(v, slug=slug)
    if json_out:
        typer.echo(json.dumps({"broken": broken, "missing": missing}, indent=2, ensure_ascii=False))
        return
    typer.echo(f"🔗 {v.meta.name} — {len(broken)} broken, {len(missing)} missing")
    if broken:
        typer.echo("\n❌ broken (auto link with no target):")
        for b in broken[:20]:
            typer.echo(f"   {b['source_slug']} → [[{b['target']}]]")
        if len(broken) > 20:
            typer.echo(f"   ... +{len(broken) - 20} more")
    if missing:
        typer.echo("\n🔍 missing (intentional placeholders, no target yet):")
        for m in missing[:20]:
            typer.echo(f"   {m['source_slug']} → [[{m['target']}]]?")
        if len(missing) > 20:
            typer.echo(f"   ... +{len(missing) - 20} more")
    if not broken and not missing:
        typer.echo("✅ all wikilinks resolve or are intentional")


# ────────────────────────── build / export ──────────────────────────


@app.command()
def build(
    vault: Optional[str] = typer.Option(None, "--vault"),
    db: Optional[Path] = typer.Option(None, "--db", help="output db path (default: <vault>/wiki.db)"),
    lint_after: bool = typer.Option(True, "--lint/--no-lint", help="build 직후 lint 12개 실행"),
) -> None:
    """Rebuild wiki.db for the active vault. lint 12개 자동 실행 (v0.5.1+)."""
    v = _resolve_vault_or_die(vault)
    result = db_module.build_db(v, db_path=db, run_lint=lint_after)
    if result["ok"]:
        typer.echo(f"✅ built: {result.get('db_path') or v.db_path}")
        if "pages" in result:
            typer.echo(f"   pages: {result['pages']}")
        if lint_after and "lint" in result:
            c = result["lint"]["counts"]
            typer.echo(f"   lint: {c.get('critical', '?')}C / {c.get('warning', '?')}W / {c.get('info', '?')}I")
    else:
        typer.echo(f"❌ build failed (rc={result.get('returncode')})", err=True)
        typer.echo(result.get("stderr_tail", ""), err=True)
        raise typer.Exit(1)


@app.command()
def export(
    vault: Optional[str] = typer.Option(None, "--vault"),
    out_dir: Optional[Path] = typer.Option(None, "--out", help="output dir (default: <codebase>/dashboard/public/api)"),
) -> None:
    """Export static JSON for the GUI (index/tree/graph/page-*/search)."""
    v = _resolve_vault_or_die(vault)
    result = export_module.export_static(v, out_dir=out_dir)
    if result.get("ok"):
        typer.echo(f"✅ exported: {result.get('out_dir')} (vault={v.meta.name})")
    else:
        typer.echo(f"❌ export failed: {result.get('reason', '?')}", err=True)
        typer.echo(result.get("stderr_tail", ""), err=True)
        raise typer.Exit(1)


# ────────────────────────── log (log.md 작업 이력) ──────────────────────────


def _format_log_entry(e: dict) -> str:
    """Format one log entry for human display."""
    header = f"  [{e['date']}] {e['action']:8s} | {e['subject']}"
    if e.get("details"):
        details_str = "; ".join(e["details"])
        return f"{header}\n      {details_str}"
    return header


@log_app.command("list")
def log_list(
    tail: Optional[int] = typer.Option(None, "--tail", "-n", help="최근 N개만 표시"),
    action: Optional[str] = typer.Option(None, "--action", "-a", help="액션 필터 (ingest/update/create/lint/build/...)"),
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """log.md의 작업 이력 조회."""
    v = _resolve_vault_or_die(vault)
    entries = log_module.list_entries(v, tail=tail, action=action)
    total = log_module.count(v)
    if json_out:
        typer.echo(json.dumps({
            "vault": v.meta.name,
            "total": total,
            "shown": len(entries),
            "entries": entries,
        }, indent=2, ensure_ascii=False))
        return
    typer.echo(f"📜 {v.meta.name} — {total} entries total, showing {len(entries)}")
    if not entries:
        typer.echo("   (empty — 첫 entry는 다음 작업 시 자동 생성)")
        return
    for e in entries:
        typer.echo(_format_log_entry(e))


@log_app.command("show")
def log_show(
    vault: Optional[str] = typer.Option(None, "--vault"),
    limit: int = typer.Option(20, "--limit", "-n"),
) -> None:
    """log.md 원본 (raw) 표시 — grep-style 확인용."""
    v = _resolve_vault_or_die(vault)
    path = log_module.log_path(v)
    if not path.exists():
        typer.echo(f"❌ log.md 없음: {path}", err=True)
        typer.echo(f"   자동 생성: `raven log append` 또는 `raven build`", err=True)
        raise typer.Exit(1)
    typer.echo(f"📄 {path} (last {limit} lines):\n")
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[-limit:]:
        typer.echo(line)


@log_app.command("append")
def log_append(
    subject: str = typer.Argument(..., help="entry 제목"),
    action: str = typer.Option("chore", "--action", "-a", help="ingest|update|create|archive|delete|lint|build|migrate|chore"),
    files: str = typer.Option("", "--files", help="콤마로 구분된 변경 파일 리스트"),
    note: str = typer.Option("", "--note", help="추가 메모"),
    vault: Optional[str] = typer.Option(None, "--vault"),
) -> None:
    """log.md에 수동 entry 추가 (자동 append 외 별도 기록용)."""
    v = _resolve_vault_or_die(vault)
    files_list = [f.strip() for f in files.split(",") if f.strip()] if files else None
    try:
        entry = log_module.append(
            v,
            action=action,
            subject=subject,
            files=files_list,
            note=note or None,
        )
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✅ appended: {entry.header()}")


@log_app.command("rotate")
def log_rotate(
    vault: Optional[str] = typer.Option(None, "--vault"),
    year: Optional[int] = typer.Option(None, "--year", help="rotate 파일명 연도 (기본: 현재 연도)"),
    force: bool = typer.Option(False, "--force", help="500 entries 미만이어도 강제 rotate"),
) -> None:
    """log.md를 log-YYYY.md로 rotate (500 entries 초과 시 자동)."""
    v = _resolve_vault_or_die(vault)
    total = log_module.count(v)
    if total < 500 and not force:
        typer.echo(f"⚠️  {total} entries (500 미만) — 강제 rotate는 --force")
        raise typer.Exit(1)
    target = log_module.rotate(v, year=year)
    typer.echo(f"✅ rotated: log.md → {target.name} ({total} entries 보관)")


@log_app.command("status")
def log_status(
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """log.md 상태 (entries 수, last entry, rotation 필요 여부)."""
    v = _resolve_vault_or_die(vault)
    path = log_module.log_path(v)
    total = log_module.count(v)
    entries = log_module.list_entries(v, tail=1)
    last = entries[0] if entries else None
    needs_rotate = total >= 500
    info = {
        "vault": v.meta.name,
        "log_path": str(path),
        "exists": path.exists(),
        "total_entries": total,
        "last_entry": last,
        "needs_rotate": needs_rotate,
        "rotate_threshold": 500,
    }
    if json_out:
        typer.echo(json.dumps(info, indent=2, ensure_ascii=False))
        return
    typer.echo(f"📜 {v.meta.name} log status:")
    typer.echo(f"   path:     {path}")
    typer.echo(f"   exists:   {path.exists()}")
    typer.echo(f"   entries:  {total} / 500")
    if last:
        typer.echo(f"   last:     [{last['date']}] {last['action']} | {last['subject']}")
    if needs_rotate:
        typer.echo(f"   ⚠️  rotation 권장: `raven log rotate`")


# ────────────────────────── lint (12 checks) ──────────────────────────


@lint_app.command("run")
def lint_run(
    vault: Optional[str] = typer.Option(None, "--vault"),
    check: Optional[str] = typer.Option(None, "--check", "-c", help="특정 check만 (#1-#12)"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="critical|warning|info 만 표시"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="이슈 전체 표시"),
    json_out: bool = typer.Option(False, "--json"),
    write_log: bool = typer.Option(False, "--log", help="log.md에 lint entry 자동 append"),
) -> None:
    """vault에 대해 lint 12개 실행. v0.5.1+ 카파시 가이드 100% 자동화."""
    v = _resolve_vault_or_die(vault)
    result = lint_module.run_all(v)
    issues = result["issues"]
    # filter
    if check:
        issues = [i for i in issues if i.get("id") == check]
    if severity:
        issues = [i for i in issues if i.get("severity") == severity]
    if json_out:
        typer.echo(json.dumps({
            "vault": result["vault"],
            "ok": result["ok"],
            "counts": result["counts"],
            "by_check": result["by_check"],
            "issues": issues,
        }, indent=2, ensure_ascii=False))
        return
    c = result["counts"]
    marker = "✅" if result["ok"] else "❌"
    typer.echo(f"{marker} {result['vault']} — {c['critical']}C / {c['warning']}W / {c['info']}I (total {c['total']})")
    if result["by_check"]:
        typer.echo(f"\n📊 by check:")
        for cid in sorted(result["by_check"].keys()):
            n = result["by_check"][cid]
            typer.echo(f"   {cid}: {n}")
    if verbose and issues:
        typer.echo(f"\n🔍 issues ({len(issues)}):")
        for iss in issues[:50]:
            typer.echo(f"  [{iss.get('id', '?'):3s}] {iss.get('severity', '?'):8s} {iss.get('slug', '?'):40s} {iss.get('message', '')}")
        if len(issues) > 50:
            typer.echo(f"   ... +{len(issues) - 50} more (--json으로 전체 확인)")
    # log 기록
    if write_log:
        try:
            log_module.append(
                v,
                action="lint",
                subject=f"lint 12개 ({c['critical']}C/{c['warning']}W/{c['info']}I)",
                extra={"by_check": json.dumps(result["by_check"], ensure_ascii=False)},
            )
        except Exception:
            pass
    # critical 있으면 exit 1
    if c["critical"] > 0:
        raise typer.Exit(1)


@lint_app.command("summary")
def lint_summary(
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """12개 check별 통계 (빠른 헬스체크)."""
    v = _resolve_vault_or_die(vault)
    result = lint_module.run_all(v)
    if json_out:
        typer.echo(json.dumps({
            "vault": result["vault"],
            "ok": result["ok"],
            "counts": result["counts"],
            "by_check": result["by_check"],
        }, indent=2, ensure_ascii=False))
        return
    c = result["counts"]
    typer.echo(f"📊 {result['vault']} lint summary:")
    typer.echo(f"   total:     {c['total']}")
    typer.echo(f"   critical:  {c['critical']} 🔴")
    typer.echo(f"   warning:   {c['warning']}  🟡")
    typer.echo(f"   info:      {c['info']}     🔵")
    typer.echo(f"\n   by check:")
    for cid in [f"#{i}" for i in range(1, 14)]:
        n = result["by_check"].get(cid, 0)
        bar = "█" * min(n, 20)
        typer.echo(f"     {cid}  {n:3d}  {bar}")


@lint_app.command("check")
def lint_check(
    check_id: str = typer.Argument(..., help="실행할 check id (#1-#13)"),
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """특정 check 1개만 실행 (디버깅/타겟 검증)."""
    v = _resolve_vault_or_die(vault)
    fn_name = f"check_{_CHECK_ID_TO_NAME.get(check_id, '')}"
    fn = getattr(lint_module, fn_name, None)
    if not fn:
        typer.echo(f"❌ unknown check: {check_id}. 1-13 중 하나.", err=True)
        raise typer.Exit(1)
    issues = fn(v)
    if json_out:
        typer.echo(json.dumps(issues, indent=2, ensure_ascii=False))
        return
    if not issues:
        typer.echo(f"✅ {check_id} ({_CHECK_ID_TO_NAME[check_id]}): no issues")
        return
    typer.echo(f"🔍 {check_id} ({_CHECK_ID_TO_NAME[check_id]}): {len(issues)} issues")
    for iss in issues:
        typer.echo(f"  [{iss.get('severity', '?'):8s}] {iss.get('slug', '?'):40s} {iss.get('message', '')}")


# check id → 함수 이름 매핑
_CHECK_ID_TO_NAME = {
    "#1": "orphans",  # #1 broken은 link_module
    "#3": "orphans",  # placeholder
    "#4": "orphans",
    "#5": "contradictions",
    "#6": "confidence_low",
    "#7": "stale",
    "#8": "page_size",
    "#9": "tag_audit",
    "#10": "frontmatter_completeness",
    "#11": "index_completeness",
    "#12": "log_size",
    "#13": "cognitive_governance",
}


# ────────────────────────── migrate (v0.5.2+) ──────────────────────────


_CATEGORY_LABELS = {
    "broken_to_missing": "broken wikilink → missing placeholder",
    "orphan_cleanup": "orphan 페이지 archive",
    "page_size_split": "200줄+ 페이지 분할 (수동)",
    "tag_promotion": "custom tag → core 승격 (수동)",
    "frontmatter_fill": "frontmatter created/updated 채움",
}


@migrate_app.command("plan")
def migrate_plan(
    vault: Optional[str] = typer.Option(None, "--vault"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="특정 카테고리만 (broken_to_missing, orphan_cleanup, ...)"),
    apply: bool = typer.Option(False, "--apply", help="실제 적용 (기본 dry-run)"),
    risk: Optional[str] = typer.Option(None, "--risk", help="적용 시 risk 단계만 (safe | review)"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """vault 마이그레이션 plan (lint 5 카테고리 분류).

    기본 = dry-run (데이터 변경 ❌). --apply 명시 시에만 실제 적용.
    """
    v = _resolve_vault_or_die(vault)
    cats = [category] if category else None
    plan = migrate_module.make_plan(v, categories=cats)
    if apply:
        if not typer.confirm(f"정말 {len(plan.fixes)}개 fix를 적용할까요?", default=False):
            typer.echo("❌ cancelled")
            raise typer.Abort()
        result = migrate_module.apply_plan(v, plan, risk_filter=risk)
        # log에 기록
        try:
            log_module.append(
                v, action="migrate",
                subject=f"migration apply (applied={len(result['applied'])}, skipped={len(result['skipped'])})",
                extra={"applied": str(len(result["applied"])), "skipped": str(len(result["skipped"]))},
            )
        except Exception:
            pass
        if json_out:
            typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return
        typer.echo(f"✅ applied: {len(result['applied'])}")
        for a in result["applied"][:20]:
            typer.echo(f"   [{a['category']:20s}] {a['slug']:40s} ({a['action']})")
        if len(result["applied"]) > 20:
            typer.echo(f"   ... +{len(result['applied']) - 20} more")
        typer.echo(f"\n⚠️  skipped: {len(result['skipped'])}")
        for s in result["skipped"][:10]:
            typer.echo(f"   {s['slug']:40s} ({s['reason']})")
        if result["errors"]:
            typer.echo(f"\n❌ errors: {len(result['errors'])}", err=True)
            for e in result["errors"]:
                typer.echo(f"   {e['slug']}: {e['error']}", err=True)
        return
    # dry-run
    summary = plan.summary()
    if json_out:
        typer.echo(json.dumps({
            **summary,
            "fixes": [
                {"category": f.category, "slug": f.slug, "description": f.description, "risk": f.risk}
                for f in plan.fixes
            ],
        }, indent=2, ensure_ascii=False))
        return
    typer.echo(f"📋 {summary['vault']} migration plan (DRY-RUN):")
    typer.echo(f"   total fixes:    {summary['total_fixes']}")
    typer.echo(f"   safe (auto):    {summary['by_risk']['safe']} ✅")
    typer.echo(f"   review (확인):  {summary['by_risk']['review']} 🟡")
    typer.echo(f"   manual (수동):  {summary['by_risk']['manual']} 🔵")
    if summary["lint_summary"]:
        typer.echo(f"\n   lint context: {summary['lint_summary']}")
    typer.echo(f"\n📊 by category:")
    for cat in migrate_module.CATEGORIES:
        n = summary["by_category"].get(cat, 0)
        if n == 0:
            continue
        typer.echo(f"   {cat:20s} {n:3d}  {_CATEGORY_LABELS.get(cat, '')}")
    if plan.fixes:
        typer.echo(f"\n🔍 fixes (first 20):")
        for f in plan.fixes[:20]:
            risk_icon = "✅" if f.risk == "safe" else "🟡" if f.risk == "review" else "🔵"
            typer.echo(f"   {risk_icon} [{f.category:18s}] {f.slug:35s} {f.description[:60]}")
        if len(plan.fixes) > 20:
            typer.echo(f"   ... +{len(plan.fixes) - 20} more")
    typer.echo(f"\n💡 적용:  raven migrate plan --vault {v.meta.name} --apply")
    typer.echo(f"   안전만: raven migrate plan --vault {v.meta.name} --apply --risk safe")


@migrate_app.command("apply")
def migrate_apply(
    vault: Optional[str] = typer.Option(None, "--vault"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    risk: Optional[str] = typer.Option(None, "--risk", help="safe | review (default: safe만)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="확인 prompt skip"),
) -> None:
    """plan + apply 한 번에. --yes 없으면 confirm."""
    v = _resolve_vault_or_die(vault)
    cats = [category] if category else None
    plan = migrate_module.make_plan(v, categories=cats)
    risk_filter = risk or "safe"
    if not yes:
        if not typer.confirm(f"정말 {len(plan.fixes)}개 fix (risk={risk_filter}) 적용?", default=False):
            typer.echo("❌ cancelled")
            raise typer.Abort()
    result = migrate_module.apply_plan(v, plan, risk_filter=risk_filter)
    try:
        log_module.append(
            v, action="migrate",
            subject=f"migration apply --risk {risk_filter} (applied={len(result['applied'])})",
        )
    except Exception:
        pass
    typer.echo(f"✅ applied: {len(result['applied'])}")
    typer.echo(f"⚠️  skipped: {len(result['skipped'])}")
    if result["errors"]:
        typer.echo(f"❌ errors: {len(result['errors'])}", err=True)


@migrate_app.command("categories")
def migrate_categories(json_out: bool = typer.Option(False, "--json")) -> None:
    """5개 카테고리 + 위험도 설명."""
    if json_out:
        typer.echo(json.dumps({c: _CATEGORY_LABELS[c] for c in migrate_module.CATEGORIES}, indent=2, ensure_ascii=False))
        return
    typer.echo("📋 migration categories (5):")
    for cat in migrate_module.CATEGORIES:
        typer.echo(f"   {cat:20s} — {_CATEGORY_LABELS[cat]}")
    typer.echo(f"\n💡 dry-run:  raven migrate plan --vault <name>")
    typer.echo(f"   apply:    raven migrate plan --vault <name> --apply")


# ────────────────────────── entrypoint ──────────────────────────


def main() -> int:
    try:
        app()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
