"""Tests for the relations migration script."""
from __future__ import annotations

from pathlib import Path
from raven.core import frontmatter as fm_mod
from raven.core.vault import Vault
from scripts.migrate_relations import build_slug_map, extract_relations_from_text, infer_relation_type


def test_infer_relation_type() -> None:
    assert infer_relation_type("This system implements the Auth protocol.") == "implements"
    assert infer_relation_type("It is implemented by AuthRepository.") == "implemented_by"
    assert infer_relation_type("This database depends on local filesystem.") == "depends_on"
    assert infer_relation_type("Authentication uses JSON Web Tokens.") == "uses"
    assert infer_relation_type("Just referencing a page here.") == "related"


def test_extract_relations_from_text() -> None:
    text = "We have a concept called [[jwt]] which we use. And we implements [[auth-service]]."
    slug_map = {
        "jwt": "content/concept/jwt",
        "auth-service": "content/tool/auth-service"
    }
    rels = extract_relations_from_text(text, "content/source-doc", slug_map)
    
    assert len(rels) == 2
    
    # 1. uses/related for jwt
    r_jwt = [r for r in rels if r["target"] == "content/concept/jwt"][0]
    assert r_jwt["type"] in {"uses", "related"}
    assert "jwt" in r_jwt["reason"].lower()
    
    # 2. implements for auth-service
    r_auth = [r for r in rels if r["target"] == "content/tool/auth-service"][0]
    assert r_auth["type"] == "implements"


def test_migrate_relations_integration(tmp_path: Path, monkeypatch) -> None:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("test-migrate", tmp_path / "vault")
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Create target files
    (content_dir / "auth.md").write_text(
        "---\ntitle: Auth\ntype: tool\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\nAuth tool\n",
        encoding="utf-8"
    )
    (content_dir / "user-service.md").write_text(
        """---
title: User Service
type: concept
created: 2026-01-01
updated: 2026-01-01
relations:
  - type: uses
    target: content/auth
    evidence: ["manual"]
    reason: Already exists.
---

This service uses [[auth]] to authenticate. And depends on [[database-service]]? for persistence.
""",
        encoding="utf-8"
    )

    # 1. Build slug map and check
    slug_map = build_slug_map(vault)
    assert "auth" in slug_map
    assert slug_map["auth"] == "content/auth"

    # 2. Extract and check merges
    raw_text = (content_dir / "user-service.md").read_text(encoding="utf-8")
    meta, body = fm_mod.parse(raw_text)
    
    extracted = extract_relations_from_text(body, "content/user-service", slug_map)
    assert len(extracted) >= 1
    
    # The 'auth' relation in extracted should be uses (due to "uses [[auth]]")
    r_auth_ext = [r for r in extracted if r["target"] == "content/auth"][0]
    assert r_auth_ext["type"] == "uses"
    
    # Merge existing and extracted
    existing = meta.get("relations") or []
    merged = list(existing)
    added = 0
    for ext_rel in extracted:
        duplicate = False
        for exist_rel in existing:
            if exist_rel.get("target") == ext_rel["target"] and exist_rel.get("type") == ext_rel["type"]:
                duplicate = True
                break
        if not duplicate:
            merged.append(ext_rel)
            added += 1
            
    # Since 'content/auth' with 'uses' was already in existing, it should NOT be duplicated.
    # But 'database-service' (as a missing placeholder/broken target) should be added.
    assert added == 1
    assert any(r["target"] == "database-service" for r in merged)
