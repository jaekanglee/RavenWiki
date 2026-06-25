"""raven.curator.sync — collection sync (vault FS ↔ yaml diff).

v3 합의안 흐름:
1. SCAN vault root의 모든 폴더/파일 (1-depth)
2. LOAD _meta/collections.yaml
3. COMPARE
   - in yaml, not in fs      → MISSING (grace 체크)
   - in fs, not in yaml      → CANDIDATE (auto_detect=true면 등록 제안)
   - in both                 → OK
4. APPLY policy
   - warn (default):
     - MISSING < 7일  → 경고 로그, continue
     - MISSING ≥ 7일  → soft-archive (archived=true), continue
     - CANDIDATE      → dry-run report에만 (실제 등록은 사람 확인)
   - conflict:
     - MISSING ≥ 7일 또는 path overlap → HARD STOP
5. WRITE sync_reports + log.md (--no-log opt-out)
6. OUTPUT
   - --json: stdout JSON
   - default: stdout human table
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import db, schema


# ────────────────────────── result types ──────────────────────────

@dataclass
class Finding:
    """sync 1건 발견."""

    kind: str                      # missing | candidate | ok | conflict
    collection_id: Optional[str] = None
    path: Optional[str] = None
    detail: str = ""


@dataclass
class SyncReport:
    """sync 출력."""

    findings: List[Finding] = field(default_factory=list)
    would_archive: List[str] = field(default_factory=list)
    candidates: List[Finding] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    policy: str = "warn"
    dry_run: bool = True

    def to_json(self) -> Dict[str, Any]:
        return {
            "policy": self.policy,
            "dry_run": self.dry_run,
            "findings": [
                {"kind": f.kind, "collection_id": f.collection_id, "path": f.path, "detail": f.detail}
                for f in self.findings
            ],
            "would_archive": self.would_archive,
            "candidates": [
                {"collection_id": f.collection_id, "path": f.path, "detail": f.detail}
                for f in self.candidates
            ],
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def to_human(self) -> str:
        lines: List[str] = []
        if self.errors:
            lines.append("🔴 ERRORS:")
            for e in self.errors:
                lines.append(f"  - {e}")
        if self.would_archive:
            lines.append("🟡 would_archive (grace ≥ 7일):")
            for cid in self.would_archive:
                lines.append(f"  - {cid}")
        if self.candidates:
            lines.append("🔵 CANDIDATES (FS에만 있음, 사람 확인 필요):")
            for c in self.candidates:
                lines.append(f"  - {c.path}  →  collection 후보 (auto_detect=true면 등록 가능)")
        if self.warnings:
            lines.append("⚠️  WARNINGS:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        missing_now = [f for f in self.findings if f.kind == "missing"]
        if missing_now:
            lines.append("🟠 MISSING (yaml O, FS X — grace 진행 중):")
            for m in missing_now:
                lines.append(f"  - {m.collection_id} ({m.path}): {m.detail}")
        if not lines:
            lines.append("✅ sync OK — yaml ↔ FS 일치")
        return "\n".join(lines)


# ────────────────────────── helpers ──────────────────────────

# yaml 의 path → vault_root 기준 절대 경로로 매핑.
# yaml paths는 "content/<project>" 같은 vault-relative prefix.
def _expand_paths(vault_root: Path, paths: List[str]) -> List[Path]:
    return [vault_root / p for p in paths]


def _detect_first_depth_dirs(vault_root: Path) -> List[Path]:
    """vault_root/content/ 의 1-depth 폴더 + vault_root/_meta 같은 special.

    sync 대상: content/<x>/ 폴더만 (FS가 1-depth 폴더 = collection 후보).
    """
    content = vault_root / "content"
    if not content.exists():
        return []
    return [p for p in content.iterdir() if p.is_dir() and not p.name.startswith(".")]


# ────────────────────────── core sync ──────────────────────────

# grace 7일 (v3 합의). 차후 collection별 override 가능.
DEFAULT_GRACE_DAYS = 7


def _parse_iso_date(s: str) -> Optional[dt.date]:
    """YYYY-MM-DD 또는 ISO 8601 → date. 실패 시 None."""
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def _days_since(date_str: Optional[str]) -> Optional[int]:
    """ISO date string → 오늘 기준 며칠 경과. None이면 None."""
    d = _parse_iso_date(date_str) if date_str else None
    if d is None:
        return None
    today = dt.date.today()
    return (today - d).days


def sync(
    vault_root: Path,
    collections_yaml_path: Path,
    grace_days: int = DEFAULT_GRACE_DAYS,
    policy: str = "warn",
    apply_archive: bool = False,
    db_path: Optional[Path] = None,
    now: Optional[int] = None,
) -> SyncReport:
    """sync 본체.

    Args:
        vault_root: vault 루트
        collections_yaml_path: yaml 절대 경로
        grace_days: missing grace 일수
        policy: 'warn' | 'conflict'
        apply_archive: True면 grace ≥ 7일 컬렉션을 yaml에 archived: true로 저장
        db_path: curation_history.db 경로
        now: unix ts

    Returns:
        SyncReport
    """
    ts = now if now is not None else int(time.time())
    report = SyncReport(policy=policy, dry_run=not apply_archive)

    # 1. yaml 로드
    if not collections_yaml_path.exists():
        report.errors.append(f"collections.yaml 없음: {collections_yaml_path}")
        return report

    try:
        yaml_obj = schema.load_and_validate(collections_yaml_path)
    except schema.CollectionsYamlError as e:
        report.errors.append(f"yaml 검증 실패: {e}")
        return report

    # 2. FS scan
    fs_dirs = _detect_first_depth_dirs(vault_root)
    fs_dir_names = {p.name for p in fs_dirs}

    # 3. yaml → fs 매핑
    yaml_path_to_id: Dict[str, str] = {}
    yaml_id_to_paths: Dict[str, List[str]] = {}
    for c in yaml_obj.collections:
        yaml_id_to_paths[c.id] = list(c.paths)
        for p in c.paths:
            yaml_path_to_id[p] = c.id

    # 4. 비교
    for c in yaml_obj.collections:
        for p in c.paths:
            abs_p = vault_root / p
            if not abs_p.exists():
                # missing in FS
                days = None
                archived_at = c.archived_at
                if archived_at:
                    days = _days_since(archived_at)
                if days is not None and days >= grace_days:
                    # soft-archive 대상
                    report.would_archive.append(c.id)
                    if policy == "conflict":
                        report.errors.append(
                            f"conflict: {c.id} ({p}) missing ≥ {grace_days}일"
                        )
                    report.findings.append(Finding(
                        kind="missing",
                        collection_id=c.id,
                        path=p,
                        detail=f"missing ≥ {grace_days}일 (would_archive)",
                    ))
                else:
                    if policy == "conflict":
                        report.errors.append(
                            f"conflict: {c.id} ({p}) missing"
                        )
                    report.findings.append(Finding(
                        kind="missing",
                        collection_id=c.id,
                        path=p,
                        detail=f"missing ({days if days is not None else 'unknown'}일 경과)",
                    ))
            else:
                report.findings.append(Finding(
                    kind="ok",
                    collection_id=c.id,
                    path=p,
                    detail="exists",
                ))

    # FS에 있는데 yaml에 없는 것 (candidates)
    for fs_dir in fs_dirs:
        # yaml paths의 1-depth dir name과 비교
        rel = f"content/{fs_dir.name}"
        if rel not in yaml_path_to_id:
            # candidate
            candidate = Finding(
                kind="candidate",
                path=rel,
                detail=f"FS에만 존재: {fs_dir.name}/",
            )
            report.candidates.append(candidate)
            report.findings.append(candidate)

    # 5. apply_archive (yaml 저장)
    if apply_archive and report.would_archive:
        # yaml_obj의 collections 중 would_archive id 찾기 → archived=True
        for c in yaml_obj.collections:
            if c.id in report.would_archive:
                c.archived = True
                if not c.archived_at:
                    c.archived_at = dt.date.today().isoformat()
        schema.save(yaml_obj, collections_yaml_path)

    # 6. sync_reports DB 기록
    try:
        conn = db.connect(db_path)
        db.init_schema(conn)
        db.insert_sync_report(
            conn,
            trigger="manual",
            dry_run=not apply_archive,
            policy=policy,
            findings_json=json.dumps(report.to_json(), ensure_ascii=False),
            would_archive=",".join(report.would_archive),
            ts=ts,
        )
        conn.close()
    except Exception as e:
        report.warnings.append(f"sync_reports 기록 실패 (best-effort): {e}")

    return report


# ────────────────────────── log.md append ──────────────────────────

def append_log(
    vault_root: Path,
    report: SyncReport,
    no_log: bool = False,
) -> None:
    """sync event를 vault/_meta/log.md에 자동 append (--no-log opt-out)."""
    if no_log:
        return
    if not (report.findings or report.candidates or report.would_archive or report.errors):
        return  # no-op (silent)

    log_path = vault_root / "_meta" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    ts = dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        "",
        f"## {ts} — raven collection sync ({report.policy}, {'apply' if not report.dry_run else 'dry-run'})",
        "",
    ]
    if report.errors:
        lines.append(f"**errors**: {len(report.errors)}")
        for e in report.errors:
            lines.append(f"- 🔴 {e}")
    if report.would_archive:
        lines.append(f"**would_archive**: {', '.join(report.would_archive)}")
    if report.candidates:
        lines.append(f"**candidates**: {len(report.candidates)} (사람 확인 필요)")
        for c in report.candidates[:5]:
            lines.append(f"- 🔵 {c.path} → collection 후보")
        if len(report.candidates) > 5:
            lines.append(f"- ... +{len(report.candidates) - 5} more")
    if report.warnings:
        lines.append(f"**warnings**: {len(report.warnings)}")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
