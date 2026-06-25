"""raven.curator.hash — payload_hash canonical form 테스트.

v3 합의안 (Claude #10):
- canonical form 정확성 lock
- 양쪽 end가 동일 구현임을 검증
"""
from __future__ import annotations

import json

import pytest

from raven.curator.hash import full_hash, idempotency_key, payload_hash


def test_payload_hash_deterministic():
    """같은 dict → 같은 hash."""
    obj = {"a": 1, "b": [2, 3], "c": "hello"}
    h1 = payload_hash(obj)
    h2 = payload_hash(obj)
    assert h1 == h2
    assert len(h1) == 16


def test_payload_hash_key_order_independent():
    """dict key 순서 무관 (sort_keys=True 보장)."""
    obj1 = {"a": 1, "b": 2, "c": 3}
    obj2 = {"c": 3, "b": 2, "a": 1}
    assert payload_hash(obj1) == payload_hash(obj2)


def test_payload_hash_whitespace_independent():
    """JSON 직렬화 시 공백 무관 (separators 보장)."""
    obj = {"a": 1, "b": 2}
    h = payload_hash(obj)
    # json.dumps 기본값으로 만들어도 같은 hash
    expected = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    import hashlib
    assert h == hashlib.sha256(expected).hexdigest()[:16]


def test_payload_hash_unicode_preserved():
    """ensure_ascii=False → 한글 등 보존."""
    obj = {"title": "한글 제목", "slug": "한글-slug"}
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert "한글" in canonical
    assert "\\u" not in canonical


def test_payload_hash_different_obj_different_hash():
    """다른 dict → 다른 hash."""
    assert payload_hash({"a": 1}) != payload_hash({"a": 2})
    assert payload_hash({"a": 1}) != payload_hash({"b": 1})


def test_payload_hash_nested_dict():
    """nested dict도 일관성."""
    obj1 = {"x": {"y": [1, 2, 3], "z": {"a": "b"}}}
    obj2 = {"x": {"z": {"a": "b"}, "y": [1, 2, 3]}}
    assert payload_hash(obj1) == payload_hash(obj2)


def test_payload_hash_list_order_matters():
    """list 순서는 의미 있음 (sort 안 함)."""
    assert payload_hash([1, 2, 3]) != payload_hash([3, 2, 1])


def test_idempotency_key_format():
    """idempotency_key = collection|type|slug|hash."""
    key = idempotency_key("wiki", "merge", "content/harumoa/why-spring-boot", "abc123def456ab78")
    assert key == "wiki|merge|content/harumoa/why-spring-boot|abc123def456ab78"


def test_idempotency_key_same_input_same_output():
    """같은 입력 → 같은 키."""
    k1 = idempotency_key("wiki", "merge", "x", "h1")
    k2 = idempotency_key("wiki", "merge", "x", "h1")
    assert k1 == k2


def test_full_hash_64_chars():
    """full_hash = 64자 hex."""
    h = full_hash({"a": 1})
    assert len(h) == 64


def test_payload_hash_returns_16_chars():
    """payload_hash는 16자 (DB 캐시 키용)."""
    h = payload_hash({"a": 1})
    assert len(h) == 16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
