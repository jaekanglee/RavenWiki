"""raven.api.workspace_tree — workspace directory tree listing (read-only).

v0.7.61+ 용도: WorkspacePage에 OS 파일 트리를 read-only로 노출.
워크스페이스는 사용자 vault에 연동된 OS 디렉토리 (예: ~/code/myproject) — 그 안의
파일/폴더를 dashboard에서 직접 보고 .md 파일은 인라인 미리보기.

설계 원칙:
    - READ-ONLY: 절대 쓰기/수정/삭제 안 함. 파일 시스템 안전망.
    - TRAVERSAL GUARD: `path` 쿼리는 workspace_path의 서브 경로만 허용.
      resolve 후 `is_relative_to(workspace_root)` 검증, 아니면 403.
    - DEPTH LIMIT: 기본 3단계 (큰 monorepo 가드). max 5.
    - HIDDEN OPTION: `?hidden=true` 시 dotfile (.git, .venv 등) 포함. 기본 false.
    - NO CACHE: 매 호출마다 stat. workspace가 사용자 OS 디렉토리라 stale 위험 > 캐시.
    - TYPE: `dir` | `file`. symlink는 따라가지 않음 (os.walk followlinks=False 기본).

응답:
    {
      "ok": true,
      "workspace_path": "/abs/path",
      "path": "src",                       # 요청한 상대 경로 (없으면 "")
      "nodes": [
        {"name": "raven", "path": "src/raven", "type": "dir",
         "size": null, "mtime": 1720000000.0, "is_hidden": false},
        {"name": "main.py", "path": "src/main.py", "type": "file",
         "size": 4096, "mtime": 1720000000.0, "is_hidden": false},
      ],
      "total": 2,
    }

실패 케이스:
    - workspace_path 미연동 → 400 "No workspace associated"
    - 경로가 workspace 외부 → 403 "Access denied"
    - 디렉토리 부재 → 404 "Directory does not exist"
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional


MAX_DEPTH = 5
DEFAULT_DEPTH = 3


def _is_hidden(name: str) -> bool:
    """Unix dotfile 규칙. .git, .venv, .DS_Store 등."""
    return name.startswith(".")


def list_workspace_dir(
    workspace_root: Path,
    relative: str = "",
    depth: int = DEFAULT_DEPTH,
    include_hidden: bool = False,
) -> dict:
    """워크스페이스 디렉토리 1단계 트리 반환.

    Args:
        workspace_root: vault에 연동된 절대 경로 (resolve 후).
        relative: workspace_root 기준 상대 경로 ("" = 루트). `..` 등 외부 경로 ❌.
        depth: 재귀 깊이 (1=루트만, MAX_DEPTH=5).
        include_hidden: dotfile 표시 여부.

    Returns:
        dict with keys: workspace_path, path, nodes, total, depth.

    Raises:
        ValueError: relative가 workspace_root 외부.
        FileNotFoundError: 디렉토리 부재.
        NotADirectoryError: 디렉토리가 아님.
    """
    workspace_root = workspace_root.resolve()
    if not relative:
        target = workspace_root
    else:
        # relative에 ../ 같은 거 거부
        candidate = (workspace_root / relative).resolve()
        # Path.resolve()는 /private/tmp 같은 macOS quirks 때문에
        # is_relative_to로 단순 prefix 체크 (resolve 후엔 둘 다 absolute)
        try:
            candidate.relative_to(workspace_root)
        except ValueError as e:
            raise ValueError(f"Path escapes workspace root: {relative}") from e
        target = candidate

    if not target.exists():
        raise FileNotFoundError(f"Directory does not exist: {relative or '.'}")
    if not target.is_dir():
        raise NotADirectoryError(f"Not a directory: {relative or '.'}")

    depth = max(1, min(depth, MAX_DEPTH))
    nodes = _walk(target, workspace_root, current_depth=1, max_depth=depth, include_hidden=include_hidden)

    return {
        "workspace_path": str(workspace_root),
        "path": relative,
        "nodes": nodes,
        "total": len(nodes),
        "depth": depth,
    }


def _walk(
    target: Path,
    workspace_root: Path,
    current_depth: int,
    max_depth: int,
    include_hidden: bool,
) -> list[dict]:
    """현재 depth의 1단계 entry만 list. 자식은 안 들어감 (lazy load)."""
    out: list[dict] = []
    try:
        entries = sorted(
            target.iterdir(),
            key=lambda p: (p.is_file(), p.name.lower()),  # dir 먼저, 알파벳순
        )
    except PermissionError:
        return out

    for entry in entries:
        name = entry.name
        hidden = _is_hidden(name)
        if hidden and not include_hidden:
            continue

        try:
            stat = entry.stat()
            size = stat.st_size if entry.is_file() else None
            mtime = stat.st_mtime
        except OSError:
            # broken symlink 등 — stat 실패 시 스킵
            continue

        try:
            rel = entry.resolve().relative_to(workspace_root).as_posix()
        except ValueError:
            # workspace_root 외부 (symlink 등) — 스킵
            continue

        out.append({
            "name": name,
            "path": rel,
            "type": "dir" if entry.is_dir() else "file",
            "size": size,
            "mtime": mtime,
            "is_hidden": hidden,
            "depth": current_depth,
            "has_children": entry.is_dir() and current_depth < max_depth,
        })

    return out


def _looks_binary(content: str, sample_bytes: int = 8192) -> bool:
    """content의 첫 sample_bytes 문자를 보고 binary 판별.

    휴리스틱:
    - NUL byte (\x00) 하나라도 있으면 binary (텍스트엔 NUL 없음)
    - printable + 일반 whitespace 비율 < 80%면 binary

    `errors="replace"`로 디코드된 텍스트라 NUL이 살아남으면 binary.
    """
    sample = content[:sample_bytes]
    if "\x00" in sample:
        return True
    if not sample:
        return False
    # printable: ASCII 가시문자 + 일반 공백류 (tab, newline, cr)
    printable = sum(
        1 for ch in sample
        if ch.isprintable() or ch in "\t\n\r"
    )
    return (printable / len(sample)) < 0.8


def read_workspace_file(
    workspace_root: Path,
    relative: str,
    max_bytes: int = 256 * 1024,
) -> dict:
    """워크스페이스 안 파일을 read-only로 읽음 (인라인 미리보기 용).

    Args:
        workspace_root: vault 연동 절대 경로.
        relative: workspace_root 기준 상대 경로.
        max_bytes: 최대 바이트 (256KB 기본). 큰 파일은 truncated.

    Returns:
        dict with keys: workspace_path, path, size, content, truncated, is_binary.

        - is_binary=True 면 content는 utf-8 디코드 결과를 그대로 담지만 UI는
          안내 메시지만 보여줘야 함 (binary 미리보기 미지원).

    Raises:
        ValueError: path가 workspace_root 외부.
        FileNotFoundError: 파일 부재.
        IsADirectoryError: 디렉토리.
    """
    workspace_root = workspace_root.resolve()
    if not relative:
        raise ValueError("relative path required")

    target = (workspace_root / relative).resolve()
    try:
        target.relative_to(workspace_root)
    except ValueError as e:
        raise ValueError(f"Path escapes workspace root: {relative}") from e

    if not target.exists():
        raise FileNotFoundError(f"File does not exist: {relative}")
    if target.is_dir():
        raise IsADirectoryError(f"Is a directory: {relative}")

    size = target.stat().st_size
    truncated = size > max_bytes

    try:
        # 텍스트로 가정. binary는 utf-8 디코드 실패 시 fallback.
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise ValueError(f"Failed to read file: {e}") from e

    is_binary = _looks_binary(content)

    if truncated:
        content = content[:max_bytes] + f"\n\n... (truncated, total {size} bytes)"

    return {
        "workspace_path": str(workspace_root),
        "path": relative,
        "size": size,
        "truncated": truncated,
        "is_binary": is_binary,
        "content": content,
    }