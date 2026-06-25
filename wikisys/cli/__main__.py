"""wikisys CLI entrypoint — `python -m wikisys.cli ...` or installed `wikisys ...`.

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

from wikisys.core import registry, resolve_active_vault, VAULTS_ROOT, REGISTRY_PATH
from wikisys.core import db_module, lint_module, export_module, link_module
from wikisys.core import slug_module, frontmatter_module, archive_module
from wikisys.core.vault import Vault

app = typer.Typer(
    name="wikisys",
    help="Multi-vault wiki engine — CLI for vault mgmt + page CRUD + linking.",
    no_args_is_help=True,
    add_completion=False,
)

vault_app = typer.Typer(help="Vault discovery / creation / registration.")
page_app = typer.Typer(help="Page CRUD inside the active vault.")
link_app = typer.Typer(help="Wikilink inspection.")
meta_app = typer.Typer(help="Vault meta docs (SCHEMA.md, RULES.md) management.")
archive_app = typer.Typer(help="Vault _archive/ management (list/clean/restore).")
app.add_typer(vault_app, name="vault")
app.add_typer(page_app, name="page")
app.add_typer(link_app, name="link")
app.add_typer(meta_app, name="meta")
app.add_typer(archive_app, name="archive")


# ────────────────────────── top-level ──────────────────────────


@app.command()
def where() -> None:
    """Show current wikisys config (vaults root, registry, active vault)."""
    typer.echo(f"📁 vaults root: {VAULTS_ROOT()}")
    typer.echo(f"📋 registry:    {REGISTRY_PATH()}")
    reg = registry()
    vaults = reg.list()
    if not vaults:
        typer.echo("⚠️  no vaults registered. Create one with `wikisys vault create <name> <path>`.")
        return
    typer.echo(f"\n🔐 active:      {reg._data.get('default', '(unset)')} (set with `wikisys vault use <name>`)")
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
        typer.echo("(empty — create with `wikisys vault create <name> <path>`)")
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
    from wikisys.core.registry import VaultMeta
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
        typer.echo("   (skipped _meta/ — run `wikisys meta sync` later to populate)")


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
    typer.echo(f"✅ archived: {slug} → {dest.relative_to(v.root)}")


# ────────────────────────── meta (vault _meta/ management) ──────────────────────────


@meta_app.command("sync")
def meta_sync(
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Re-copy SCHEMA.md / RULES.md from wikisys templates into _meta/.

    Overwrites existing files. Use after wikisys upgrade to refresh meta docs.
    """
    v = _resolve_vault_or_die(vault)
    result = v.sync_meta()
    if json_out:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if result["copied"]:
        typer.echo(f"✅ synced: {', '.join(result['copied'])} → {v.root / '_meta'}")
    if result["errors"]:
        typer.echo(f"❌ errors:", err=True)
        for err in result["errors"]:
            typer.echo(f"   {err['file']}: {err['error']}", err=True)
        raise typer.Exit(1)
    if not result["copied"]:
        typer.echo("⚠️  no templates found (package install broken?)")


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
    lint_after: bool = typer.Option(True, "--lint/--no-lint", help="run lint after build"),
) -> None:
    """Rebuild wiki.db for the active vault."""
    v = _resolve_vault_or_die(vault)
    result = db_module.build_db(v, db_path=db)
    if result["ok"]:
        typer.echo(f"✅ built: {result.get('db_path') or v.db_path}")
        if "pages" in result:
            typer.echo(f"   pages: {result['pages']}")
        if lint_after:
            lr = lint_module.run_lint(v)
            c = lr.get("counts", {})
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


def main() -> int:
    try:
        app()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
