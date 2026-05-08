# tests/intents/context_requires/test_context_requires_decorator.py
"""
Tests for @context_requires — recording context dependencies
on the method attribute _required_context_keys.
"""

import pytest

from action_machine.context.ctx_constants import Ctx
from action_machine.intents.context_requires.context_requires_decorator import context_requires


class TestSingleKey:
    """A single key is stored as a one-element frozenset."""

    def test_single_constant_key(self) -> None:
        # Arrange — decorator with one Ctx constant
        @context_requires(Ctx.User.user_id)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act — read stored attribute
        keys = my_method._required_context_keys

        # Assert — frozenset with one element
        assert keys == frozenset({"user.user_id"})

    def test_single_string_key(self) -> None:
        # Arrange — decorator with a string path (custom field)
        @context_requires("user.extra.billing_plan")
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert
        assert keys == frozenset({"user.extra.billing_plan"})


class TestMultipleKeys:
    """Multiple keys are stored as a multi-element frozenset."""

    def test_two_constants(self) -> None:
        # Arrange — decorator with two constants
        @context_requires(Ctx.User.user_id, Ctx.User.roles)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — frozenset with two elements
        assert keys == frozenset({"user.user_id", "user.roles"})

    def test_keys_from_different_components(self) -> None:
        # Arrange — keys from different context components
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id, Ctx.Runtime.hostname)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — all three keys in the set
        assert keys == frozenset({"user.user_id", "request.trace_id", "runtime.hostname"})

    def test_mixed_constants_and_strings(self) -> None:
        # Arrange — mix of Ctx constants and string paths
        @context_requires(Ctx.User.user_id, "user.extra.billing_plan")
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — both keys in the set
        assert keys == frozenset({"user.user_id", "user.extra.billing_plan"})


class TestDuplicateKeys:
    """Duplicate keys collapse in the frozenset."""

    def test_duplicate_keys_deduplicated(self) -> None:
        # Arrange — same key twice
        @context_requires(Ctx.User.user_id, Ctx.User.user_id)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — frozenset removes duplicates
        assert keys == frozenset({"user.user_id"})
        assert len(keys) == 1


class TestReturnsFunctionUnchanged:
    """The decorator returns the original function unchanged."""

    def test_function_identity(self) -> None:
        # Arrange — original function
        async def original(self, params, state, box, connections, ctx):
            return "result"

        # Act — apply decorator
        decorated = context_requires(Ctx.User.user_id)(original)

        # Assert — same function, not a wrapper
        assert decorated is original

    def test_function_name_preserved(self) -> None:
        # Arrange / Act
        @context_requires(Ctx.User.user_id)
        async def my_named_method(self, params, state, box, connections, ctx):
            pass

        # Assert — method name unchanged
        assert my_named_method.__name__ == "my_named_method"


class TestKeysType:
    """Stored attribute _required_context_keys is a frozenset."""

    def test_type_is_frozenset(self) -> None:
        # Arrange / Act
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Assert — type is frozenset, not set or list
        assert isinstance(my_method._required_context_keys, frozenset)


class TestInvalidNoKeys:
    """Empty @context_requires() call — ValueError."""

    def test_no_keys_raises_value_error(self) -> None:
        # Arrange / Act / Assert — empty call with no arguments
        with pytest.raises(ValueError, match="at least one key"):
            @context_requires()
            async def my_method(self, params, state, box, connections, ctx):
                pass


class TestInvalidKeyType:
    """Non-string key — TypeError."""

    def test_int_key_raises_type_error(self) -> None:
        # Arrange / Act / Assert — int instead of string
        with pytest.raises(TypeError, match="must be a string"):
            @context_requires(42)  # type: ignore[arg-type]
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_none_key_raises_type_error(self) -> None:
        # Arrange / Act / Assert — None instead of string
        with pytest.raises(TypeError, match="must be a string"):
            @context_requires(None)  # type: ignore[arg-type]
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_list_key_raises_type_error(self) -> None:
        # Arrange / Act / Assert — list instead of string
        with pytest.raises(TypeError, match="must be a string"):
            @context_requires(["user.user_id"])  # type: ignore[arg-type]
            async def my_method(self, params, state, box, connections, ctx):
                pass


class TestInvalidEmptyKey:
    """Empty string as key — ValueError."""

    def test_empty_string_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="cannot be empty"):
            @context_requires("")
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_whitespace_only_raises_value_error(self) -> None:
        # Arrange / Act / Assert — whitespace-only string
        with pytest.raises(ValueError, match="cannot be empty"):
            @context_requires("   ")
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_mixed_valid_and_empty_raises(self) -> None:
        # Arrange / Act / Assert — one valid key, one empty
        with pytest.raises(ValueError, match="cannot be empty"):
            @context_requires(Ctx.User.user_id, "")
            async def my_method(self, params, state, box, connections, ctx):
                pass


class TestInvalidTarget:
    """Decorator applies only to callables."""

    def test_non_callable_raises_type_error(self) -> None:
        # Arrange — string instead of function
        decorator = context_requires(Ctx.User.user_id)

        # Act / Assert
        with pytest.raises(TypeError, match="only be applied to methods/callables"):
            decorator("not a function")

    def test_int_target_raises_type_error(self) -> None:
        # Arrange — number instead of function
        decorator = context_requires(Ctx.User.user_id)

        # Act / Assert
        with pytest.raises(TypeError, match="only be applied to methods/callables"):
            decorator(42)
