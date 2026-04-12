# tests/decorators/test_on_decorator.py
"""
Tests for the @on decorator — plugin method subscription to machine events.

The @on decorator attaches SubscriptionInfo records to a plugin method's
_on_subscriptions list. It validates that the decorated target is an async
callable with exactly 4 parameters (self, state, event, log), that event_class
is a subclass of BasePluginEvent, and that the method name starts with "on_".

The decorator accepts event_class as the first positional argument (a class
from the BasePluginEvent hierarchy) and optional keyword-only filters:
action_class, action_name_pattern, aspect_name_pattern, nest_level,
domain, predicate, ignore_exceptions [1].

Scenarios covered:
    - Valid async method with 4 params and "on_" prefix is decorated without error.
    - SubscriptionInfo is appended to method._on_subscriptions.
    - Multiple @on decorators on the same method produce multiple subscriptions.
    - event_class stored correctly in SubscriptionInfo.
    - action_name_pattern defaults to None.
    - Custom action_name_pattern stored correctly.
    - ignore_exceptions defaults to True.
    - ignore_exceptions=False stored correctly.
    - Non-BasePluginEvent event_class raises TypeError (int, str, None).
    - Non-callable target raises TypeError.
    - Synchronous method raises TypeError.
    - Wrong parameter count (not 4) raises TypeError.
    - Method without "on_" prefix raises NamingPrefixError.
    - SubscriptionInfo is frozen (immutable).
"""
import pytest

from action_machine.plugins.events import (
    BeforeRegularAspectEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.plugins.on_decorator import on
from action_machine.plugins.subscription_info import SubscriptionInfo

# ═════════════════════════════════════════════════════════════════════════════
# Valid usage
# ═════════════════════════════════════════════════════════════════════════════

class TestValidUsage:
    """Verify @on decorator on correctly defined async methods."""

    def test_decorates_valid_method(self) -> None:
        """A valid async method with 4 params and on_ prefix is decorated without error."""

        @on(GlobalFinishEvent)
        async def on_handler(self, state, event, log):
            return state

        assert hasattr(on_handler, "_on_subscriptions")
        assert len(on_handler._on_subscriptions) == 1

    def test_subscription_info_event_class(self) -> None:
        """SubscriptionInfo stores the correct event_class."""

        @on(BeforeRegularAspectEvent)
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.event_class is BeforeRegularAspectEvent

    def test_default_action_name_pattern(self) -> None:
        """Default action_name_pattern is None (match all actions)."""

        @on(GlobalStartEvent)
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.action_name_pattern is None

    def test_custom_action_name_pattern(self) -> None:
        """Custom action_name_pattern is stored correctly."""

        @on(GlobalFinishEvent, action_name_pattern="CreateOrder.*")
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.action_name_pattern == "CreateOrder.*"

    def test_default_ignore_exceptions(self) -> None:
        """Default ignore_exceptions is True."""

        @on(GlobalFinishEvent)
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.ignore_exceptions is True

    def test_ignore_exceptions_false(self) -> None:
        """ignore_exceptions=False is stored correctly."""

        @on(GlobalFinishEvent, ignore_exceptions=False)
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.ignore_exceptions is False

    def test_multiple_subscriptions(self) -> None:
        """Multiple @on decorators on one method create multiple subscriptions."""

        @on(GlobalStartEvent)
        @on(GlobalFinishEvent)
        async def on_handler(self, state, event, log):
            return state

        assert len(on_handler._on_subscriptions) == 2
        event_classes = {s.event_class for s in on_handler._on_subscriptions}
        assert GlobalStartEvent in event_classes
        assert GlobalFinishEvent in event_classes

    def test_returns_original_function(self) -> None:
        """The decorator returns the original function unchanged."""

        async def on_handler(self, state, event, log):
            return state

        decorated = on(GlobalFinishEvent)(on_handler)
        assert decorated is on_handler

    def test_method_name_stored(self) -> None:
        """SubscriptionInfo stores the method name."""

        @on(GlobalFinishEvent)
        async def on_my_handler(self, state, event, log):
            return state

        info = on_my_handler._on_subscriptions[0]
        assert info.method_name == "on_my_handler"

    def test_default_filters_are_none(self) -> None:
        """All optional filters default to None."""

        @on(GlobalFinishEvent)
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.action_class is None
        assert info.action_name_pattern is None
        assert info.aspect_name_pattern is None
        assert info.nest_level is None
        assert info.domain is None
        assert info.predicate is None


# ═════════════════════════════════════════════════════════════════════════════
# event_class validation
# ═════════════════════════════════════════════════════════════════════════════

class TestEventClassValidation:
    """Verify event_class argument validation."""

    def test_non_class_int_raises_type_error(self) -> None:
        """Non-class event_class (int) raises TypeError."""
        with pytest.raises(TypeError, match="BasePluginEvent"):
            @on(123)  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_none_raises_type_error(self) -> None:
        """None event_class raises TypeError."""
        with pytest.raises(TypeError, match="BasePluginEvent"):
            @on(None)  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_string_raises_type_error(self) -> None:
        """String event_class raises TypeError (old API rejected)."""
        with pytest.raises(TypeError, match="BasePluginEvent"):
            @on("global_finish")  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_non_base_plugin_event_class_raises(self) -> None:
        """A regular class (not BasePluginEvent subclass) raises TypeError."""
        with pytest.raises(TypeError, match="BasePluginEvent"):
            @on(dict)  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_list_raises_type_error(self) -> None:
        """List event_class raises TypeError."""
        with pytest.raises(TypeError, match="BasePluginEvent"):
            @on([GlobalFinishEvent])  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state


# ═════════════════════════════════════════════════════════════════════════════
# Filter argument validation
# ═════════════════════════════════════════════════════════════════════════════

class TestFilterValidation:
    """Verify filter argument validation in @on."""

    def test_non_string_action_name_pattern_raises(self) -> None:
        """Non-string action_name_pattern raises TypeError."""
        with pytest.raises(TypeError, match="action_name_pattern"):
            @on(GlobalFinishEvent, action_name_pattern=123)  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_negative_nest_level_raises(self) -> None:
        """Negative nest_level raises ValueError."""
        with pytest.raises(ValueError, match="отрицательн"):
            @on(GlobalFinishEvent, nest_level=-1)
            async def on_handler(self, state, event, log):
                return state

    def test_non_callable_predicate_raises(self) -> None:
        """Non-callable predicate raises TypeError."""
        with pytest.raises(TypeError, match="predicate"):
            @on(GlobalFinishEvent, predicate="not_callable")  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_non_type_domain_raises(self) -> None:
        """Non-type domain raises TypeError."""
        with pytest.raises(TypeError, match="domain"):
            @on(GlobalFinishEvent, domain="not_a_type")  # type: ignore[arg-type]
            async def on_handler(self, state, event, log):
                return state

    def test_aspect_name_pattern_on_non_aspect_event_raises(self) -> None:
        """aspect_name_pattern on non-AspectEvent raises ValueError."""
        with pytest.raises(ValueError, match="AspectEvent"):
            @on(GlobalFinishEvent, aspect_name_pattern="validate_.*")
            async def on_handler(self, state, event, log):
                return state

    def test_aspect_name_pattern_on_aspect_event_ok(self) -> None:
        """aspect_name_pattern on AspectEvent subclass is accepted."""

        @on(BeforeRegularAspectEvent, aspect_name_pattern="validate_.*")
        async def on_handler(self, state, event, log):
            return state

        info = on_handler._on_subscriptions[0]
        assert info.aspect_name_pattern == "validate_.*"


# ═════════════════════════════════════════════════════════════════════════════
# Target validation
# ═════════════════════════════════════════════════════════════════════════════

class TestTargetValidation:
    """Verify that @on rejects invalid targets."""

    def test_non_callable_raises_type_error(self) -> None:
        """Applying @on to a non-callable raises TypeError."""
        with pytest.raises(TypeError, match="методам"):
            on(GlobalFinishEvent)("not_a_function")

    def test_sync_method_raises_type_error(self) -> None:
        """Applying @on to a synchronous method raises TypeError."""
        with pytest.raises(TypeError, match="async"):
            @on(GlobalFinishEvent)
            def on_handler(self, state, event, log):
                return state

    def test_wrong_param_count_raises_type_error(self) -> None:
        """A method with != 4 parameters raises TypeError."""
        with pytest.raises(TypeError, match="4"):
            @on(GlobalFinishEvent)
            async def on_handler(self, state, event):
                return state

    def test_too_many_params_raises_type_error(self) -> None:
        """A method with 5 parameters raises TypeError."""
        with pytest.raises(TypeError, match="4"):
            @on(GlobalFinishEvent)
            async def on_handler(self, state, event, log, extra):
                return state

    def test_no_params_raises_type_error(self) -> None:
        """A method with 0 parameters raises TypeError."""
        with pytest.raises(TypeError, match="4"):
            @on(GlobalFinishEvent)
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
            @on(GlobalFinishEvent)
            async def handler(self, state, event, log):
                return state

    def test_wrong_prefix_raises(self) -> None:
        """Method with wrong prefix raises NamingPrefixError."""
        from action_machine.core.exceptions import NamingPrefixError

        with pytest.raises(NamingPrefixError, match="on_"):
            @on(GlobalFinishEvent)
            async def handle_finish(self, state, event, log):
                return state


# ═════════════════════════════════════════════════════════════════════════════
# SubscriptionInfo immutability
# ═════════════════════════════════════════════════════════════════════════════

class TestSubscriptionInfoFrozen:
    """Verify that SubscriptionInfo is a frozen dataclass."""

    def test_cannot_modify_event_class(self) -> None:
        """Attempting to change event_class raises an error."""
        info = SubscriptionInfo(
            event_class=GlobalFinishEvent,
            method_name="on_handler",
        )
        with pytest.raises(AttributeError):
            info.event_class = GlobalStartEvent  # type: ignore[misc]

    def test_cannot_modify_action_name_pattern(self) -> None:
        """Attempting to change action_name_pattern raises an error."""
        info = SubscriptionInfo(
            event_class=GlobalFinishEvent,
            method_name="on_handler",
            action_name_pattern="Test.*",
        )
        with pytest.raises(AttributeError):
            info.action_name_pattern = ".*"  # type: ignore[misc]

    def test_cannot_modify_ignore_exceptions(self) -> None:
        """Attempting to change ignore_exceptions raises an error."""
        info = SubscriptionInfo(
            event_class=GlobalFinishEvent,
            method_name="on_handler",
            ignore_exceptions=False,
        )
        with pytest.raises(AttributeError):
            info.ignore_exceptions = True  # type: ignore[misc]

    def test_cannot_modify_method_name(self) -> None:
        """Attempting to change method_name raises an error."""
        info = SubscriptionInfo(
            event_class=GlobalFinishEvent,
            method_name="on_handler",
        )
        with pytest.raises(AttributeError):
            info.method_name = "on_other"  # type: ignore[misc]
