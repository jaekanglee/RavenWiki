"""Plain vault creation contract — no Raven policy content is injected."""
from pathlib import Path

from raven.core.vault import Vault


def test_default_create_leaves_a_plain_markdown_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path / "registry"))
    root = tmp_path / "notes"

    vault = Vault.create("notes", root)

    assert vault.root == root.resolve()
    assert (root / "content").is_dir()
    for forbidden in (
        "_meta",
        "log.md",
        "WELCOME.md",
        ".git",
        ".gitignore",
    ):
        assert not (root / forbidden).exists(), forbidden
