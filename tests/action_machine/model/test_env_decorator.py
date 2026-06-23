# tests/action_machine/model/test_env_decorator.py
"""Tests for the ``@env`` class decorator and ``Context.resolve("env.*")``."""

from __future__ import annotations

import pytest

from aoa.action_machine.context import Context, env
from aoa.action_machine.context.env_entry import EnvEntry

# ── @env registers entry on the class ────────────────────────────────────────

def test_env_registers_entry_on_class() -> None:
    @env("region", "eu-west-1")
    class AppContext(Context):
        pass

    assert "region" in AppContext.__env_entries__
    assert isinstance(AppContext.__env_entries__["region"], EnvEntry)


def test_env_callable_stored_as_is() -> None:
    def provider() -> str:
        return "us-east-1"

    @env("region", provider)
    class AppContext(Context):
        pass

    assert AppContext.__env_entries__["region"].provider is provider


def test_env_constant_wrapped_in_lambda() -> None:
    @env("max_retries", 3)
    class AppContext(Context):
        pass

    assert AppContext.__env_entries__["max_retries"].get() == 3


def test_env_ttl_stored_on_entry() -> None:
    @env("flag", lambda: True, ttl=60)
    class AppContext(Context):
        pass

    assert AppContext.__env_entries__["flag"].ttl == 60


# ── multiple stacked decorators ───────────────────────────────────────────────

def test_multiple_env_decorators_all_registered() -> None:
    @env("flag", lambda: True, ttl=30)
    @env("region", "eu-west-1")
    @env("max_retries", 3)
    class AppContext(Context):
        pass

    entries = AppContext.__env_entries__
    assert set(entries.keys()) == {"flag", "region", "max_retries"}


# ── inheritance ───────────────────────────────────────────────────────────────

def test_child_inherits_parent_env_entries() -> None:
    @env("region", "eu-west-1")
    class ParentContext(Context):
        pass

    @env("flag", lambda: True)
    class ChildContext(ParentContext):
        pass

    assert "region" in ChildContext.__env_entries__
    assert "flag" in ChildContext.__env_entries__


def test_child_does_not_mutate_parent_entries() -> None:
    @env("region", "eu-west-1")
    class ParentContext(Context):
        pass

    @env("flag", lambda: True)
    class ChildContext(ParentContext):
        pass

    assert "flag" not in ParentContext.__env_entries__


def test_child_can_override_parent_entry() -> None:
    @env("region", "eu-west-1")
    class ParentContext(Context):
        pass

    @env("region", "ap-southeast-1")
    class ChildContext(ParentContext):
        pass

    assert ChildContext.__env_entries__["region"].get() == "ap-southeast-1"
    assert ParentContext.__env_entries__["region"].get() == "eu-west-1"


# ── Context.resolve("env.*") ──────────────────────────────────────────────────

def test_resolve_env_prefix_returns_provider_value() -> None:
    @env("region", "eu-west-1")
    class AppContext(Context):
        pass

    ctx = AppContext()
    assert ctx.resolve("env.region") == "eu-west-1"


def test_resolve_env_missing_key_returns_default() -> None:
    @env("region", "eu-west-1")
    class AppContext(Context):
        pass

    ctx = AppContext()
    assert ctx.resolve("env.missing") is None
    assert ctx.resolve("env.missing", "fallback") == "fallback"


def test_resolve_env_callable_invoked_lazily() -> None:
    calls: list[int] = []

    def provider() -> str:
        calls.append(1)
        return "value"

    @env("k", provider)
    class AppContext(Context):
        pass

    ctx = AppContext()
    assert len(calls) == 0       # provider NOT called at class/instance creation
    ctx.resolve("env.k")
    assert len(calls) == 1       # called only on access


def test_resolve_non_env_path_uses_base_resolve() -> None:
    class AppContext(Context):
        pass

    ctx = AppContext()
    assert ctx.resolve("user.user_id") is None   # normal dot-path still works


def test_base_context_has_no_env_entries() -> None:
    ctx = Context()
    assert ctx.resolve("env.anything") is None


def test_env_negative_ttl_raises_at_decoration_time() -> None:
    with pytest.raises(ValueError, match="ttl must be >= 0"):
        @env("k", lambda: 1, ttl=-1)
        class AppContext(Context):
            pass
