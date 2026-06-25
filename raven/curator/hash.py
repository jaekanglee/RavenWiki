"""raven.curator.hash — payload_hash canonical form (멱등성 게이트).

v3 합의안 (Claude #10):
- 정확한 form: `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",",":")).encode("utf-8")`
- → `hashlib.sha256`. hex digest.
- 입력은 **내용 결정에 필요한 필드만** (timestamp 같은 변동 필드 제외).
- 양쪽 end가 동일 구현임을 테스트로 lock.

사용 패턴:
- Curator가 LLM 위임 결과(suggestion payload dict)를 받으면
- 즉시 `payload_hash(suggestion)` 계산 → idempotency_key에 포함
- DB upsert (idempotency_key UNIQUE) → 동일 suggestion 중복 차단
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def payload_hash(obj: Any) -> str:
    """객체의 canonical form → sha256 hex digest (16자).

    Args:
        obj: dict/list/str/int 등 JSON 직렬화 가능한 객체.

    Returns:
        16자 hex string (64-bit). 충돌 확률 매우 낮음 (LLM 결과 변동성 대비).
    """
    canonical = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()[:16]


def idempotency_key(collection_id: str, suggestion_type: str, target_slug: str, hash16: str) -> str:
    """suggestion 멱등성 키.

    구성: collection_id | suggestion_type | target_slug | payload_hash

    같은 vault + 같은 type + 같은 slug + 같은 payload면
    같은 키 → DB UNIQUE 충돌 → 중복 차단.
    """
    return f"{collection_id}|{suggestion_type}|{target_slug}|{hash16}"


def full_hash(obj: Any) -> str:
    """64자 hex (전체 sha256). 디버깅/audit용. 일반 payload_hash와 구분."""
    canonical = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
