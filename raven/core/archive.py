"""archive — manage _archive/ directory (cleanup + restore).

Public surface:
    list_archived(vault) -> list[ArchiveEntry]
        Walk _archive/, return entries with metadata (path, age, original_slug).

    clean_archived(vault, *, older_than_days, apply=False) -> CleanResult
        Delete archived files older than `older_than_days`.
        If apply=False (default), dry-run: returns what WOULD be deleted.
        If apply=True, actually deletes.

    restore_archived(vault, archive_path) -> RestoreResult
        Move file from _archive/ back to original slug location.
        archive_path: relative path under vault root, e.g.
            "_archive/content/foo-20260625-123456.md"
        The original slug is inferred by stripping the archive filename:
            "content/foo-20260625-123456.md" → original "content/foo"

Time format on archived filenames (set by CLI/API/Agent delete):
    "<original-stem>-YYYYMMDD-HHMMSS.md"
"""
from __future__ import annotations

import datetime as _dt
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .vault import Vault


# YYYYMMDD-HHMMSS suffix on archive filenames (matches CLI/API/Agent delete)
ARCHIVE_TS_RE = re.compile(r"-(\d{8}-\d{6})\.md$")


@dataclass
class ArchiveEntry:
    """One archived file with metadata."""

    rel_path: str        # vault-relative path, e.g. "_archive/content/foo-20260625-123456.md"
    abs_path: Path
    timestamp: Optional[_dt.datetime]  # parsed from filename, or None
    age_days: Optional[float]          # now - timestamp (in days)
    original_slug: str                 # inferred, e.g. "content/foo"

    def to_dict(self) -> dict:
        return {
            "rel_path": self.rel_path,
            "original_slug": self.original_slug,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "age_days": self.age_days,
        }


@dataclass
class CleanResult:
    would_delete: list[ArchiveEntry] = field(default_factory=list)
    deleted: list[ArchiveEntry] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    dry_run: bool = True

    def to_dict(self) -> dict:
        return {
            "ok": True,
            "dry_run": self.dry_run,
            "would_delete_count": len(self.would_delete),
            "deleted_count": len(self.deleted),
            "would_delete": [e.to_dict() for e in self.would_delete],
            "deleted": [e.to_dict() for e in self.deleted],
            "errors": self.errors,
        }


@dataclass
class RestoreResult:
    ok: bool
    original_slug: str = ""
    restored_to: str = ""
    error: Optional[str] = None


# ────────────────────────── list ──────────────────────────


def list_archived(vault: Vault) -> list[ArchiveEntry]:
    """Walk vault._archive/ and return all entries with parsed metadata."""
    archive_root = vault.root / "_archive"
    if not archive_root.exists():
        return []
    out: list[ArchiveEntry] = []
    now = _dt.datetime.now()
    for fp in sorted(archive_root.rglob("*.md")):
        rel = str(fp.relative_to(vault.root))
        ts, original = _parse_archive_filename(fp.name, fp.relative_to(archive_root))
        age = None
        if ts:
            age = (now - ts).total_seconds() / 86400.0
        out.append(ArchiveEntry(
            rel_path=rel,
            abs_path=fp,
            timestamp=ts,
            age_days=age,
            original_slug=original,
        ))
    return out


def _parse_archive_filename(name: str, rel_under_archive: Path) -> tuple[Optional[_dt.datetime], str]:
    """Parse 'foo-20260625-123456.md' → (timestamp, original slug).

    The original slug is the path under archive_root with the timestamp suffix
    stripped from the filename. e.g.
        archive_root / "content/sub/foo-20260625-123456.md"
        → original_slug = "content/sub/foo"
    """
    m = ARCHIVE_TS_RE.search(name)
    if not m:
        return None, str(rel_under_archive.with_suffix(""))  # fallback: no timestamp parsed
    ts_str = m.group(1)
    try:
        ts = _dt.datetime.strptime(ts_str, "%Y%m%d-%H%M%S")
    except ValueError:
        return None, str(rel_under_archive.with_suffix(""))
    # Strip "-TIMESTAMP" from stem to recover original name
    original_stem = name[: m.start()]  # everything before "-YYYYMMDD-HHMMSS.md"
    original_path = rel_under_archive.with_name(original_stem + ".md")
    return ts, str(original_path.with_suffix(""))


# ────────────────────────── clean ──────────────────────────


def clean_archived(
    vault: Vault,
    *,
    older_than_days: int = 30,
    apply: bool = False,
) -> CleanResult:
    """Delete archived files older than `older_than_days`.

    Args:
        vault: target vault.
        older_than_days: only files with age_days > this are candidates.
                         0 means "all archive files" (use with care).
        apply: if False (default), dry-run. If True, actually delete.

    Returns:
        CleanResult with would_delete (always populated) and deleted (if apply).
    """
    entries = list_archived(vault)
    candidates = [e for e in entries if e.age_days is not None and e.age_days > older_than_days]
    # If older_than_days=0, include all (even files with no parsed timestamp)
    if older_than_days <= 0:
        candidates = entries

    result = CleanResult(dry_run=not apply, would_delete=candidates)

    if apply:
        for e in candidates:
            try:
                e.abs_path.unlink()
                # also remove empty parent dirs under _archive
                _cleanup_empty_parents(e.abs_path, vault.root / "_archive")
                result.deleted.append(e)
            except Exception as ex:
                result.errors.append({"path": e.rel_path, "error": str(ex)})

    return result


def _cleanup_empty_parents(fp: Path, stop_at: Path) -> None:
    """Remove empty parent dirs up to (but not including) stop_at."""
    parent = fp.parent
    while parent != stop_at and parent.exists():
        try:
            parent.rmdir()  # only succeeds if empty
            parent = parent.parent
        except OSError:
            break  # not empty or permission denied — stop


# ────────────────────────── restore ──────────────────────────


def restore_archived(vault: Vault, archive_rel_path: str) -> RestoreResult:
    """Move a file from _archive/ back to its original slug location.

    Args:
        vault: target vault.
        archive_rel_path: vault-relative path of the archived file, e.g.
                          "_archive/content/foo-20260625-123456.md" — 또는
                          원래 slug (e.g. "content/foo", v0.7.66+). slug면
                          최신 아카이브 본을 선택한다.

    Returns:
        RestoreResult with original_slug and restored_to path.

    Raises no exception — returns RestoreResult(ok=False, error=...) on failure.
    """
    archive_root = vault.root / "_archive"

    # v0.7.66 (평가 P1#7): 원래 slug로도 복원 가능. `raven archive list`가
    # "아카이브 → 원본 slug" 매핑을 보여주면서 정작 restore는 전체 경로만
    # 받던 마찰 해소.
    if not archive_rel_path.replace("\\", "/").startswith("_archive/"):
        slug = archive_rel_path[:-3] if archive_rel_path.endswith(".md") else archive_rel_path
        matches = [e for e in list_archived(vault) if e.original_slug == slug]
        if not matches:
            return RestoreResult(
                ok=False,
                error=(
                    f"no archived file for slug: {slug!r} "
                    "(`raven archive list`로 아카이브 목록을 확인하세요)"
                ),
            )
        matches.sort(key=lambda e: e.timestamp or _dt.datetime.min)
        archive_rel_path = matches[-1].rel_path

    # validate input lives under _archive/
    candidate = (vault.root / archive_rel_path).resolve()
    try:
        candidate.relative_to(archive_root.resolve())
    except ValueError:
        return RestoreResult(ok=False, error=f"path not under _archive/: {archive_rel_path!r}")

    if not candidate.exists() or not candidate.is_file():
        return RestoreResult(ok=False, error=f"archive file not found: {archive_rel_path!r}")

    # Infer original slug
    rel_under_archive = candidate.relative_to(archive_root)
    _, original_slug = _parse_archive_filename(candidate.name, rel_under_archive)

    # Restore target
    target = vault.root / f"{original_slug}.md"
    if target.exists():
        return RestoreResult(
            ok=False,
            original_slug=original_slug,
            error=f"target already exists: {original_slug}",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(candidate), str(target))
    # cleanup empty parents
    _cleanup_empty_parents(candidate, archive_root)
    return RestoreResult(
        ok=True,
        original_slug=original_slug,
        restored_to=str(target.relative_to(vault.root)),
    )
