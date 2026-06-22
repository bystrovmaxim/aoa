# tests/action_machine/model/test_cache_key_mixin.py
"""Tests for CacheKeyMixin — hash-based cache key and always-write policy."""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.cache_key_mixin import CacheKeyMixin


class ScalarParams(BaseParams):
    sku: str = Field(description="sku")
    quantity: int = Field(description="qty")
    price: float = Field(description="price")
    active: bool = Field(description="active")


class EmptyParams(BaseParams):
    pass


class ComplexParams(BaseParams):
    products: list[str] = Field(description="products")
    meta: dict[str, str] = Field(description="meta")


class MixedParams(BaseParams):
    name: str = Field(description="name")
    tags: list[str] = Field(description="tags")


_mixin = CacheKeyMixin()


def test_same_params_produce_same_key() -> None:
    p1 = ScalarParams(sku="A", quantity=2, price=9.99, active=True)
    p2 = ScalarParams(sku="A", quantity=2, price=9.99, active=True)
    assert _mixin.cache_key(p1) == _mixin.cache_key(p2)


def test_different_params_produce_different_key() -> None:
    p1 = ScalarParams(sku="A", quantity=1, price=9.99, active=True)
    p2 = ScalarParams(sku="B", quantity=1, price=9.99, active=True)
    assert _mixin.cache_key(p1) != _mixin.cache_key(p2)


def test_key_is_hex_string() -> None:
    p = ScalarParams(sku="X", quantity=1, price=1.0, active=False)
    key = _mixin.cache_key(p)
    assert isinstance(key, str)
    assert len(key) == 64
    int(key, 16)  # must be valid hex


def test_empty_params_returns_stable_key() -> None:
    key1 = _mixin.cache_key(EmptyParams())
    key2 = _mixin.cache_key(EmptyParams())
    assert key1 == key2
    assert len(key1) == 64


def test_complex_fields_excluded_from_key() -> None:
    p1 = ComplexParams(products=["a", "b"], meta={"x": "1"})
    p2 = ComplexParams(products=["c", "d"], meta={"y": "2"})
    assert _mixin.cache_key(p1) == _mixin.cache_key(p2)


def test_mixed_params_uses_only_scalar_fields() -> None:
    p1 = MixedParams(name="alice", tags=["x"])
    p2 = MixedParams(name="alice", tags=["y", "z"])
    assert _mixin.cache_key(p1) == _mixin.cache_key(p2)


def test_non_base_schema_params_returns_stable_key() -> None:
    key = _mixin.cache_key(object())
    assert len(key) == 64


@pytest.mark.asyncio
async def test_on_cache_write_returns_true() -> None:
    result = await _mixin.on_cache_write(object(), object(), 42.0)
    assert result is True
