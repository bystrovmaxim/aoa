# tests/action_machine/runtime/test_cache_tag.py
"""Unit tests for :class:`~aoa.action_machine.runtime.cache_tag.CacheTag`."""

from __future__ import annotations

import pytest

from aoa.action_machine.runtime.cache_tag import CacheTag


class _Order:
    pass


class _Payment:
    pass


def test_cache_tag_type_only() -> None:
    tag = CacheTag(type=_Order)
    assert tag.type is _Order
    assert tag.key is None


def test_cache_tag_key_str() -> None:
    tag = CacheTag(key="order:42")
    assert tag.type is None
    assert tag.key == "order:42"


def test_cache_tag_key_int() -> None:
    tag = CacheTag(key=42)
    assert tag.type is None
    assert tag.key == 42


def test_cache_tag_type_and_key() -> None:
    tag = CacheTag(type=_Order, key=99)
    assert tag.type is _Order
    assert tag.key == 99


def test_cache_tag_both_none_raises() -> None:
    with pytest.raises(ValueError, match="CacheTag"):
        CacheTag()


def test_cache_tag_is_frozen() -> None:
    tag = CacheTag(type=_Order)
    with pytest.raises(AttributeError):
        tag.type = _Payment  # type: ignore[misc]


def test_cache_tag_equality_same_values() -> None:
    assert CacheTag(type=_Order, key=1) == CacheTag(type=_Order, key=1)


def test_cache_tag_inequality_different_key() -> None:
    assert CacheTag(type=_Order, key=1) != CacheTag(type=_Order, key=2)


def test_cache_tag_inequality_different_type() -> None:
    assert CacheTag(type=_Order, key=1) != CacheTag(type=_Payment, key=1)


def test_cache_tag_hashable_dedup_in_set() -> None:
    tags = {CacheTag(type=_Order, key=1), CacheTag(type=_Order, key=1)}
    assert len(tags) == 1


def test_cache_tag_different_tags_in_set() -> None:
    tags = {CacheTag(type=_Order, key=1), CacheTag(type=_Order, key=2)}
    assert len(tags) == 2


def test_cache_tag_usable_in_frozenset() -> None:
    fs = frozenset({CacheTag(type=_Order, key=1), CacheTag(type=_Payment)})
    assert len(fs) == 2


def test_cache_tag_wildcard_type_not_equal_to_typed() -> None:
    assert CacheTag(type=_Order) != CacheTag(type=_Order, key=1)


def test_cache_tag_key_none_field_means_wildcard_only_in_matching_not_equality() -> None:
    # Equality is field-level; wildcard semantics are a CacheCoordinator concern.
    assert CacheTag(type=_Order) != CacheTag(type=_Order, key=None)
