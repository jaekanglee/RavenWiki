"""raven.curator.schema — collections.yaml 로드 + 검증.

v3 합의안 4박 + 1:
- collections.yaml 위치 = `<vault>/_meta/collections.yaml` (vault 내부)
- 최상단 `schema_version: 1` 필수 (마이그레이션 훅)
- defaults + collections[] 두 섹션
- path 검증: `**` recursion ❌, bare `*` ❌ (단, `*.md` 단일 레벨 ✅), `..` ❌
- yaml 작성 + execute 시점 양쪽에서 동일 검증 함수 호출 (DRY)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


SCHEMA_VERSION = 1
DEFAULT_SYNC_POLICY = "warn"
DEFAULT_FIRST_RUN_STRATEGY = "skip_silent"
VALID_FIRST_RUN_STRATEGIES = ("skip_silent", "full_scan", "interactive")
VALID_SYNC_POLICIES = ("warn", "conflict")


class CollectionsYamlError(Exception):
    """collections.yaml 검증 실패. line number 포함."""

    def __init__(self, message: str, line: Optional[int] = None) -> None:
        self.line = line
        if line is not None:
            super().__init__(f"line {line}: {message}")
        else:
            super().__init__(message)


@dataclass
class Collection:
    """단일 collection 정의."""

    id: str
    paths: List[str]
    vault: Optional[str] = None
    description: str = ""
    auto_detect: bool = True
    first_run_strategy: str = DEFAULT_FIRST_RUN_STRATEGY
    archived: bool = False
    archived_at: Optional[str] = None
    grace_expires_at: Optional[str] = None
    retired_at: Optional[str] = None
    merged_into: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """archived 또는 retired면 비활성."""
        return not (self.archived or self.retired_at)


@dataclass
class CollectionsYaml:
    """collections.yaml 최상단."""

    schema_version: int = SCHEMA_VERSION
    defaults: Dict[str, Any] = field(
        default_factory=lambda: {
            "first_run_strategy": DEFAULT_FIRST_RUN_STRATEGY,
            "sync_policy": DEFAULT_SYNC_POLICY,
        }
    )
    collections: List[Collection] = field(default_factory=list)


# ────────────────────────── path validation ──────────────────────────

# yaml 라인 추적용: 잘못된 path 발견 시 line number 포함하려면 yaml 노드 사용.
# 여기선 path 문자열만 검증하므로 line 추적은 load_and_validate()에서 처리.

def validate_path(path: str) -> None:
    """단일 path 검증. 위반 시 CollectionsYamlError (line 없음).

    규칙:
    - `**` recursion ❌
    - bare `*` glob ❌ (단, `*.md` 같은 단일 레벨 suffix는 ✅)
    - `..` parent traversal ❌
    - 절대경로 ❌ (vault 상대만)
    - path는 반드시 `content/` 또는 `_`로 시작 (vault 정책)
    """
    if not path:
        raise CollectionsYamlError("path is empty")

    if path.startswith("/"):
        raise CollectionsYamlError(f"absolute path not allowed: {path}")

    if ".." in Path(path).parts:
        raise CollectionsYamlError(f"parent traversal not allowed: {path}")

    if "**" in path:
        raise CollectionsYamlError(f"recursion '**' not allowed: {path}")

    # bare glob: `*`이 path의 단일 segment 전체면 ❌
    # 허용: `*.md`, `*.json` (단일 레벨 suffix glob)
    # 거부: `*`, `*/**`, `*/foo` (bare)
    parts = path.split("/")
    for part in parts:
        if part == "*":
            raise CollectionsYamlError(f"bare '*' glob not allowed: {path}")
        # `*.md` 형태는 ✅ (단, segment 안에서 * 1개 + .ext)
        if part.startswith("*.") and part.count("*") == 1:
            continue  # ✅ *.md
        if "*" in part:
            # 예: `foo*bar`, `*foo` — 중간/시작 글롭 ❌
            raise CollectionsYamlError(f"partial glob not allowed: {path} (segment={part!r})")

    # vault 정책: content/ 또는 _ 시작
    if not (path.startswith("content/") or path.startswith("_")):
        raise CollectionsYamlError(
            f"path must start with 'content/' or '_': {path}"
        )


def validate_paths(paths: List[str]) -> None:
    """여러 path 일괄 검증. 첫 위반에서 raise."""
    for p in paths:
        validate_path(p)


# ────────────────────────── yaml load + validate ──────────────────────────

def _parse_first_run_strategy(value: str, line: Optional[int]) -> str:
    if value not in VALID_FIRST_RUN_STRATEGIES:
        raise CollectionsYamlError(
            f"first_run_strategy must be one of {VALID_FIRST_RUN_STRATEGIES}: {value!r}",
            line=line,
        )
    return value


def _parse_sync_policy(value: str, line: Optional[int]) -> str:
    if value not in VALID_SYNC_POLICIES:
        raise CollectionsYamlError(
            f"sync_policy must be one of {VALID_SYNC_POLICIES}: {value!r}",
            line=line,
        )
    return value


def load_and_validate(path: Path) -> CollectionsYaml:
    """collections.yaml 로드 + 검증.

    Raises:
        CollectionsYamlError — line number 포함.
    """
    if not path.exists():
        raise CollectionsYamlError(f"file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        # yaml 라인 추적: Loader 직접 사용 (PyYAML은 노드 line 노출 안 함)
        # → 여기선 대안으로 yaml.safe_load 후 키별 검증에서 path 발견 시 path 라인 추적
        raw_text = f.read()

    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as e:
        raise CollectionsYamlError(f"yaml parse error: {e}") from e

    if not isinstance(data, dict):
        raise CollectionsYamlError("root must be a mapping")

    # schema_version
    sv = data.get("schema_version")
    if sv is None:
        raise CollectionsYamlError("schema_version missing (required)")
    if sv != SCHEMA_VERSION:
        raise CollectionsYamlError(
            f"schema_version mismatch: got {sv}, expected {SCHEMA_VERSION}"
        )

    # defaults
    defaults_raw = data.get("defaults", {}) or {}
    defaults: Dict[str, Any] = {
        "first_run_strategy": _parse_first_run_strategy(
            defaults_raw.get("first_run_strategy", DEFAULT_FIRST_RUN_STRATEGY), None
        ),
        "sync_policy": _parse_sync_policy(
            defaults_raw.get("sync_policy", DEFAULT_SYNC_POLICY), None
        ),
    }

    # collections
    cols_raw = data.get("collections", []) or []
    if not isinstance(cols_raw, list):
        raise CollectionsYamlError("'collections' must be a list")

    collections: List[Collection] = []
    seen_ids: set = set()
    for i, raw in enumerate(cols_raw):
        line_no = i + 2  # yaml 1-based + header 1줄
        if not isinstance(raw, dict):
            raise CollectionsYamlError(f"collection must be a mapping", line=line_no)

        cid = raw.get("id")
        if not cid:
            raise CollectionsYamlError("collection.id missing", line=line_no)
        if cid in seen_ids:
            raise CollectionsYamlError(f"duplicate id: {cid}", line=line_no)
        seen_ids.add(cid)

        paths_raw = raw.get("paths", []) or []
        if not isinstance(paths_raw, list) or not paths_raw:
            raise CollectionsYamlError("collection.paths must be non-empty list", line=line_no)

        # path 검증 (yaml line 추적 위해 직접 호출)
        for p in paths_raw:
            try:
                validate_path(p)
            except CollectionsYamlError as e:
                raise CollectionsYamlError(
                    f"collection {cid!r}: {e}", line=line_no
                ) from e

        coll = Collection(
            id=cid,
            paths=paths_raw,
            vault=raw.get("vault"),
            description=raw.get("description", ""),
            auto_detect=raw.get("auto_detect", True),
            first_run_strategy=_parse_first_run_strategy(
                raw.get("first_run_strategy", defaults["first_run_strategy"]),
                line_no,
            ),
            archived=raw.get("archived", False),
            archived_at=raw.get("archived_at"),
            grace_expires_at=raw.get("grace_expires_at"),
            retired_at=raw.get("retired_at"),
            merged_into=raw.get("merged_into"),
        )
        collections.append(coll)

    return CollectionsYaml(
        schema_version=sv,
        defaults=defaults,
        collections=collections,
    )


def save(yaml_obj: CollectionsYaml, path: Path) -> None:
    """CollectionsYaml → yaml 파일 저장."""
    data: Dict[str, Any] = {
        "schema_version": yaml_obj.schema_version,
        "defaults": yaml_obj.defaults,
        "collections": [
            {k: v for k, v in {
                "id": c.id,
                "vault": c.vault,
                "paths": c.paths,
                "description": c.description,
                "auto_detect": c.auto_detect,
                "first_run_strategy": c.first_run_strategy,
                "archived": c.archived,
                "archived_at": c.archived_at,
                "grace_expires_at": c.grace_expires_at,
                "retired_at": c.retired_at,
                "merged_into": c.merged_into,
            }.items() if v is not None and v != "" and v is not False}
            for c in yaml_obj.collections
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
