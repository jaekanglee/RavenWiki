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
app.add_typer(vault_app, name="vault")
app.add_typer(page_app, name="page")
app.add_typer(link_app, name="link")


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
) -> None:
    """Create new vault on disk and register it."""
    v = Vault.create(
        name=name,
        path=Path(path).expanduser(),
        mode=mode,
        owner=owner,
        description=description,
    )
    typer.echo(f"✅ vault created: {v.meta.name} → {v.root}")


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
    """Create a new page with frontmatter + empty body."""
    v = _resolve_vault_or_die(vault)
    fp = v.root / f"{slug}.md"
    if fp.exists():
        typer.echo(f"❌ exists: {slug}", err=True)
        raise typer.Exit(1)
    fp.parent.mkdir(parents=True, exist_ok=True)
    today = __import__("datetime").date.today().isoformat()
    fm_lines = [
        "---",
        f"title: {title}",
        f"type: {type_}",
        f"tags: [{tags}]" if tags else "tags: []",
        f"created: {today}",
        f"updated: {today}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    fp.write_text("\n".join(fm_lines))
    typer.echo(f"✅ created: {slug}")


@page_app.command("delete")
def page_delete(
    slug: str,
    vault: Optional[str] = typer.Option(None, "--vault"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Archive page (moves to _archive/<slug>-<timestamp>.md)."""
    v = _resolve_vault_or_die(vault)
    fp = v.root / f"{slug}.md"
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
    dest = archive_dir / f"{slug.replace('/', '_')}-{ts}.md"
    fp.rename(dest)
    typer.echo(f"✅ archived: {slug} → {dest.relative_to(v.root)}")


# ────────────────────────── link ──────────────────────────


@link_app.command("check")
def link_check(
    slug: Optional[str] = typer.Option(None, help="limit to one page (else whole vault)"),
    vault: Optional[str] = typer.Option(None, "--vault"),
) -> None:
    """Find broken / missing wikilinks. (Stub — full impl in next phase.)"""
    v = _resolve_vault_or_die(vault)
    typer.echo(f"🔗 scanning: {v.meta.name}")
    typer.echo("   (full wikilink audit available after core/link.py is wired)")


# ────────────────────────── build / export ──────────────────────────


@app.command()
def build(
    vault: Optional[str] = typer.Option(None, "--vault"),
) -> None:
    """Rebuild wiki.db for active vault (full impl next phase)."""
    v = _resolve_vault_or_die(vault)
    typer.echo(f"🔨 rebuilding wiki.db: {v.meta.name}")
    typer.echo(f"   (delegates to scripts/build_db.py in next phase)")


@app.command()
def export(
    vault: Optional[str] = typer.Option(None, "--vault"),
    out_dir: Optional[Path] = typer.Option(None, "--out", help="output dir (default: <codebase>/dashboard/public/api)"),
) -> None:
    """Export static JSON for GUI (full impl next phase)."""
    v = _resolve_vault_or_die(vault)
    typer.echo(f"📤 exporting static JSON: {v.meta.name}")
    typer.echo(f"   out: {out_dir or '(default)'}")
    typer.echo(f"   (delegates to scripts/export_static.py in next phase)")


def main() -> int:
    try:
        app()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
