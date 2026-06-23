# tests/action_machine/model/test_env_entry.py
"""Unit tests for :class:`~aoa.action_machine.context.env_entry.EnvEntry`."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from aoa.action_machine.context.env_entry import EnvEntry

# ── ttl validation ────────────────────────────────────────────────────────────

def test_negative_ttl_raises_value_error() -> None:
    with pytest.raises(ValueError, match="ttl must be >= 0"):
        EnvEntry(key="k", provider=lambda: 1, ttl=-1)


def test_zero_ttl_is_valid() -> None:
    entry: EnvEntry[int] = EnvEntry(key="k", provider=lambda: 42, ttl=0)
    assert entry.ttl == 0


def test_positive_ttl_is_valid() -> None:
    entry: EnvEntry[int] = EnvEntry(key="k", provider=lambda: 42, ttl=30)
    assert entry.ttl == 30


# ── first access calls provider ───────────────────────────────────────────────

def test_get_calls_provider_on_first_access() -> None:
    calls: list[int] = []

    def provider() -> int:
        calls.append(1)
        return 99

    entry: EnvEntry[int] = EnvEntry(key="k", provider=provider, ttl=0)
    result = entry.get()

    assert result == 99
    assert len(calls) == 1


# ── ttl=0 caches forever ─────────────────────────────────────────────────────

def test_ttl_zero_caches_forever() -> None:
    calls: list[int] = []

    def provider() -> int:
        calls.append(1)
        return 7

    entry: EnvEntry[int] = EnvEntry(key="k", provider=provider, ttl=0)

    with patch("aoa.action_machine.context.env_entry.time.monotonic", side_effect=[0.0, 9999.0]):
        entry.get()   # miss — provider called
        entry.get()   # hit — provider NOT called even after huge time gap

    assert len(calls) == 1


# ── ttl>0 expires after N seconds ────────────────────────────────────────────

def test_ttl_positive_returns_cached_within_window() -> None:
    calls: list[int] = []

    def provider() -> int:
        calls.append(1)
        return 5

    entry: EnvEntry[int] = EnvEntry(key="k", provider=provider, ttl=10)

    with patch(
        "aoa.action_machine.context.env_entry.time.monotonic",
        side_effect=[0.0, 5.0, 5.0],  # set at 0, read at 5 (within ttl)
    ):
        entry.get()   # miss: cached_at=0.0
        result = entry.get()  # hit: 5.0 - 0.0 = 5 < 10

    assert result == 5
    assert len(calls) == 1


def test_ttl_positive_re_calls_provider_after_expiry() -> None:
    calls: list[int] = []

    def provider() -> int:
        calls.append(1)
        return calls[-1]

    entry: EnvEntry[int] = EnvEntry(key="k", provider=provider, ttl=10)

    with patch(
        "aoa.action_machine.context.env_entry.time.monotonic",
        side_effect=[0.0, 20.0, 20.0],  # write@0; read@20 (expired); write@20
    ):
        entry.get()   # miss: cached_at=0.0
        entry.get()   # expired: 20.0 - 0.0 = 20 > 10 → re-call provider

    assert len(calls) == 2


# ── frozen dataclass: _cache mutates but reference is frozen ─────────────────

def test_entry_is_frozen_rebinding_raises() -> None:
    entry: EnvEntry[int] = EnvEntry(key="k", provider=lambda: 1, ttl=0)
    with pytest.raises(AttributeError):  # frozen dataclass raises FrozenInstanceError(AttributeError)
        entry.key = "other"  # type: ignore[misc]


def test_cache_dict_is_mutable_inside_frozen_entry() -> None:
    entry: EnvEntry[int] = EnvEntry(key="k", provider=lambda: 42, ttl=0)
    entry.get()
    assert "v" in entry._cache  # cache was written despite frozen=True on the dataclass
