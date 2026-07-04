"""v0.7.67 (평가 A#4/B#6) — atomic_write_text 회귀 가드.

pre-v0.7.67 page/log writes used a plain `path.write_text(...)`: a crash
mid-write left a truncated file on disk (SoT corruption for pages; a torn
log.md for lock-free readers like digest/lint).
"""
from __future__ import annotations

from pathlib import Path

from raven.core.lock import atomic_write_text


def test_atomic_write_creates_file(tmp_path: Path):
    fp = tmp_path / "a.md"
    atomic_write_text(fp, "hello\n")
    assert fp.read_text(encoding="utf-8") == "hello\n"


def test_atomic_write_overwrite_leaves_no_tmp_files(tmp_path: Path):
    fp = tmp_path / "a.md"
    atomic_write_text(fp, "v1\n")
    atomic_write_text(fp, "v2\n")
    assert fp.read_text(encoding="utf-8") == "v2\n"
    leftovers = [p for p in tmp_path.iterdir() if p != fp]
    assert leftovers == []


def test_atomic_write_creates_parent_dirs(tmp_path: Path):
    fp = tmp_path / "content" / "sub" / "a.md"
    atomic_write_text(fp, "body\n")
    assert fp.read_text(encoding="utf-8") == "body\n"


def test_atomic_write_never_leaves_partial_file_on_failure(tmp_path: Path, monkeypatch):
    fp = tmp_path / "a.md"
    fp.write_text("original\n", encoding="utf-8")

    import raven.core.lock as lock_module

    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(lock_module.os, "replace", boom)
    try:
        atomic_write_text(fp, "corrupted-half-write")
    except OSError:
        pass
    # Original file untouched — no torn write landed.
    assert fp.read_text(encoding="utf-8") == "original\n"
    tmp_leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".a.md.")]
    assert tmp_leftovers == []  # tmp file cleaned up on failure
