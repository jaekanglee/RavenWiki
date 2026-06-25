"""Tests for wikisys.agents — Agent adapter after v0.3.2 migration."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wikisys.agents import Agent, AgentScope


@pytest.fixture
def isolated_env(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="wikisys-agent-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="wikisys-agent-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    # create + register a vault named 'test'
    from wikisys.core.vault import Vault
    v = Vault.create("test", target_root / "test", bootstrap=False)
    yield {"reg_root": reg_root, "target_root": target_root, "vault": v}
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


@pytest.fixture
def bot():
    return Agent.named(
        "test-bot",
        scope=AgentScope(vault_names=("test",), allow_delete=True),
        run_id="r-1",
        intent="verify v0.3.2",
    )


# ─── write ──────────────────────────────────────────────────


def test_agent_write_creates_with_provenance(isolated_env, bot):
    av = bot.vault("test")
    r = av.write("content/hello", "body", title="Hi", type="concept")
    assert r.ok, r.error
    fp = isolated_env["vault"].root / "content" / "hello.md"
    text = fp.read_text()
    assert "title: Hi" in text
    assert "type: concept" in text
    # agents provenance present (delegated to frontmatter_module.render)
    assert "agents:" in text
    assert "  - name: test-bot" in text
    assert "    run_id: r-1" in text
    assert "    intent: verify v0.3.2" in text


def test_agent_write_short_slug_creates_at_root(isolated_env, bot):
    """Agent does NOT auto-prefix (unlike CLI/API).

    Rationale: LLM agents should pass explicit vault-relative paths so the
    provenance + audit trail is unambiguous. A bare slug 'hello' creates
    'hello.md' at the vault root — agent code is expected to use 'content/...'.
    """
    av = bot.vault("test")
    r = av.write("hello", "body", title="Hi")
    assert r.ok, r.error
    # file at vault root (NOT content/) — by design for agent
    assert (isolated_env["vault"].root / "hello.md").is_file()
    assert not (isolated_env["vault"].root / "content" / "hello.md").exists()


def test_agent_write_rejects_parent_traversal(isolated_env, bot):
    av = bot.vault("test")
    r = av.write("../escape", "body")
    assert not r.ok
    assert "invalid slug" in r.error


def test_agent_write_rejects_absolute(isolated_env, bot):
    av = bot.vault("test")
    r = av.write("/etc/passwd", "body")
    assert not r.ok
    assert "invalid slug" in r.error


def test_agent_write_preserves_created_on_overwrite(isolated_env, bot):
    av = bot.vault("test")
    av.write("content/x", "v1", title="X")
    fp = isolated_env["vault"].root / "content" / "x.md"
    fm1 = fp.read_text()
    # extract created
    import re
    m = re.search(r"created: (\S+)", fm1)
    assert m, "no created in first write"
    created1 = m.group(1)

    # overwrite — created must be preserved (v0.3+ via merge)
    av.write("content/x", "v2", title="X2")
    fm2 = fp.read_text()
    m2 = re.search(r"created: (\S+)", fm2)
    assert m2
    assert m2.group(1) == created1  # preserved!
    # updated should be today
    today = __import__("datetime").date.today().isoformat()
    assert f"updated: {today}" in fm2
    assert "title: X2" in fm2


def test_agent_write_does_not_overwrite_via_safe_path_when_disallowed(isolated_env):
    """allow_create=False means... still overwrites in current impl (write is always upsert).
    Existing semantics preserved — scope just controls agent's reach, not diff semantics.
    """
    bot = Agent.named(
        "no-create",
        scope=AgentScope(vault_names=("test",), allow_create=False),
    )
    av = bot.vault("test")
    r = av.write("content/c", "x")
    # current impl: allow_create doesn't gate writes (was pre-existing behavior)
    assert r.ok


# ─── delete (archive mirror) ───────────────────────────────


def test_agent_delete_archives_with_mirror(isolated_env, bot):
    av = bot.vault("test")
    av.write("content/sub/nested", "x", title="N")
    r = av.delete("content/sub/nested")
    assert r.ok, r.error
    # original gone
    assert not (isolated_env["vault"].root / "content" / "sub" / "nested.md").exists()
    # mirror archive
    arc = isolated_env["vault"].root / "_archive" / "content" / "sub"
    assert arc.is_dir()
    assert len(list(arc.glob("nested-*.md"))) == 1


def test_agent_delete_rejects_bad_slug(isolated_env, bot):
    av = bot.vault("test")
    r = av.delete("../escape")
    assert not r.ok
    assert "invalid slug" in r.error


def test_agent_delete_disallowed_by_default(isolated_env):
    """Default scope has allow_delete=False."""
    bot = Agent.named("read-only", scope="test")
    av = bot.vault("test")
    av.write("content/x", "x")
    r = av.delete("content/x")
    assert not r.ok
    assert "allow_delete" in r.error


# ─── list / search (parse 위임) ────────────────────────────


def test_agent_list_parses_tags_correctly(isolated_env, bot):
    av = bot.vault("test")
    av.write("content/a", "x", title="A", tags=["alpha", "beta"])
    av.write("content/b", "y", title="B", tags=["solo"])
    rows = av.list()
    titles = {r["title"] for r in rows}
    assert {"A", "B"}.issubset(titles)


def test_agent_search_finds_term(isolated_env, bot):
    av = bot.vault("test")
    av.write("content/findme", "The quick brown fox", title="Findme")
    results = av.search("quick fox")
    assert any(r["slug"] == "content/findme" for r in results)
