"""raven.cli — Typer-based command-line interface.

Commands:
    vault list                          List all vaults in the registry
    vault use <name>                    Set default vault (writes to .registry.json)
    vault info [name]                   Show vault metadata + content stats
    vault create <name> <path>          Create new vault + register
    vault register <name> <path>        Register an existing folder as a vault
    vault remove <name>                 Unregister (does NOT delete folder)
    page ls [--vault NAME] [--type T]   List pages in active vault
    page get <slug>                     Show one page (frontmatter + body)
    page new <slug> --title --type      Create new page (interactive)
    page update <slug> --content FILE   Overwrite page body
    page delete <slug>                  Archive page (moves to _archive/)
    link check [slug]                   Find broken / missing wikilinks
    build                               Rebuild wiki.db for active vault
    export                              Static JSON for GUI
"""
