# tests/decorators/test_on_decorator.py
"""
Tests for the @on decorator — plugin method subscription to machine events.

The @on decorator attaches SubscriptionInfo records to a plugin method's
_on_subscriptions list. It validates that the decorated target is an async
callable with exactly 4 parameters (self, state, event, log), that event_type
is a non-empty string, that action_filter is a string, and that the method
name starts with "on_".

Scenarios covered:
    - Valid async method with 4 params and "on_" prefix is decorated without error.
    - SubscriptionInfo is appended to method._on_subscriptions.
    - Multiple @on decorators on the same method produce multiple subscriptions.
    - event_type stored correctly in SubscriptionInfo.
    - action_filter defaults to ".*".
    - Custom action_filter stored correctly.
    - ignore_exceptions defaults to True.
    - ignore_exceptions=False stored correctly.
    - Non-string event_type raises TypeError.
    - Empty event_type raises ValueError.
    - Whitespace-only event_type raises ValueError.
    - Non-string action_filter raises TypeError.
    - Non-callable target raises TypeError.
    - Synchronous method raises TypeError.
    - Wrong parameter count (not 4) raises TypeError.
    - Method without "on_" prefix raises NamingPrefixError.
    - SubscriptionInfo is frozen (immutable).
"""

import pytest

from action_machine.plugins.decorators import SubscriptionInfo, on

# ═════════════════════════════════════════════════════════════════════════════
# Valid usage
# ═════════════════════════════════════════════════════════════════════════════


class TestValidUsage:
    """Verify @on decorator on correctly defined async methods."""

    def test_decorates_valid_method(self) -> None:
        """A valid async method with 4 params and on_ prefix is decorated without error."""

        @on("global_finish")
        async def on_handler(self, state, event, log):
            return state

        assert hasattr(on_handler, "_on_subscriptions")
        assert len(on_handler._on_subscriptions) == 1

    def test_subscription_info_event_type(self) -> None:
        """SubscriptionInfo stores the correct event_type."""

        @on("before:validate")
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.event_type == "before:validate"

    def test_default_action_filter(self) -> None:
        """Default action_filter is '.*' (match all actions)."""

        @on("global_start")
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.action_filter == ".*"

    def test_custom_action_filter(self) -> None:
        """Custom action_filter is stored correctly."""

        @on("global_finish", "CreateOrder.*")
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.action_filter == "CreateOrder.*"

    def test_default_ignore_exceptions(self) -> None:
        """Default ignore_exceptions is True."""

        @on("global_finish")
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.ignore_exceptions is True

    def test_ignore_exceptions_false(self) -> None:
        """ignore_exceptions=False is stored correctly."""

        @on("global_finish", ignore_exceptions=False)
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.ignore_exceptions is False

    def test_multiple_subscriptions(self) -> None:
        """Multiple @on decorators on one method create multiple subscriptions."""

        @on("global_start")
        @on("global_finish")
        async def on_handler(self, state, event, log):
            return state

        assert len(on_handler._on_subscriptions) == 2
        event_types = {s.event_type for s in on_handler._on_subscriptions}
        assert "global_start" in event_types
        assert "global_finish" in event_types

    def test_returns_original_function(self) -> None:
        """The decorator returns the original function unchanged."""

        async def on_handler(self, state, event, log):
            return state

        decorated = on("global_finish")(on_handler)
        assert decorated is on_handler


# ═════════════════════════════════════════════════════════════════════════════
# event_type validation
# ═════════════════════════════════════════════════════════════════════════════


class TestEventTypeValidation:
    """Verify event_type argument validation."""

    def test_non_string_raises_type_error(self) -> None:
        """Non-string event_type raises TypeError."""
        with pytest.raises(TypeError, match="event_type"):
            @on(123)  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_none_raises_type_error(self) -> None:
        """None event_type raises TypeError."""
        with pytest.raises(TypeError, match="event_type"):
            @on(None)  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_empty_string_raises_value_error(self) -> None:
        """Empty string event_type raises ValueError."""
        with pytest.raises(ValueError, match="event_type"):
            @on("")
            async def on_handler(self, state, event, log):
                return state

    def test_whitespace_only_raises_value_error(self) -> None:
        """Whitespace-only event_type raises ValueError."""
        with pytest.raises(ValueError, match="event_type"):
            @on("   ")
            async def on_handler(self, state, event, log):
                return state


# ═════════════════════════════════════════════════════════════════════════════
# action_filter validation
# ═════════════════════════════════════════════════════════════════════════════


class TestActionFilterValidation:
    """Verify action_filter argument validation."""

    def test_non_string_raises_type_error(self) -> None:
        """Non-string action_filter raises TypeError."""
        with pytest.raises(TypeError, match="action_filter"):
            @on("global_finish", 123)  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state


# ═════════════════════════════════════════════════════════════════════════════
# Target validation
# ═════════════════════════════════════════════════════════════════════════════


class TestTargetValidation:
    """Verify that @on rejects invalid targets."""

    def test_non_callable_raises_type_error(self) -> None:
        """Applying @on to a non-callable raises TypeError."""
        with pytest.raises(TypeError, match="методам"):
            on("global_finish")("not_a_function")

    def test_sync_method_raises_type_error(self) -> None:
        """Applying @on to a synchronous method raises TypeError."""
        with pytest.raises(TypeError, match="async"):
            @on("global_finish")
            def on_handler(self, state, event, log):
                return state

    def test_wrong_param_count_raises_type_error(self) -> None:
        """A method with != 4 parameters raises TypeError."""
        with pytest.raises(TypeError, match="4"):
            @on("global_finish")
            async def on_handler(self, state, event):
                return state

    def test_too_many_params_raises_type_error(self) -> None:
        """A method with 5 parameters raises TypeError."""
        with pytest.raises(TypeError, match="4"):
            @on("global_finish")
            async def on_handler(self, state, event, log, extra):
                return state

    def test_no_params_raises_type_error(self) -> None:
        """A method with 0 parameters raises TypeError."""
        with pytest.raises(TypeError, match="4"):
            @on("global_finish")
            async def on_handler():
                pass


# ═════════════════════════════════════════════════════════════════════════════
# Naming prefix validation
# ═════════════════════════════════════════════════════════════════════════════


class TestNamingPrefixValidation:
    """Verify that @on rejects methods without on_ prefix."""

    def test_missing_prefix_raises(self) -> None:
        """Method without on_ prefix raises NamingPrefixError."""
        from action_machine.core.exceptions import NamingPrefixError

        with pytest.raises(NamingPrefixError, match="on_"):
            @on("global_finish")
            async def handler(self, state, event, log):
                return state

    def test_wrong_prefix_raises(self) -> None:
        """Method with wrong prefix raises NamingPrefixError."""
        from action_machine.core.exceptions import NamingPrefixError

        with pytest.raises(NamingPrefixError, match="on_"):
            @on("global_finish")
            async def handle_finish(self, state, event, log):
                return state


# ═════════════════════════════════════════════════════════════════════════════
# SubscriptionInfo immutability
# ═════════════════════════════════════════════════════════════════════════════


class TestSubscriptionInfoFrozen:
    """Verify that SubscriptionInfo is a frozen dataclass."""

    def test_cannot_modify_event_type(self) -> None:
        """Attempting to change event_type raises an error."""
        info = SubscriptionInfo(event_type="global_finish")

        with pytest.raises(AttributeError):
            info.event_type = "other"  # type: ignore[misc]

    def test_cannot_modify_action_filter(self) -> None:
        """Attempting to change action_filter raises an error."""
        info = SubscriptionInfo(event_type="global_finish", action_filter="Test.*")

        with pytest.raises(AttributeError):
            info.action_filter = ".*"  # type: ignore[misc]

    def test_cannot_modify_ignore_exceptions(self) -> None:
        """Attempting to change ignore_exceptions raises an error."""
        info = SubscriptionInfo(event_type="global_finish", ignore_exceptions=False)

        with pytest.raises(AttributeError):
            info.ignore_exceptions = True  # type: ignore[misc]
