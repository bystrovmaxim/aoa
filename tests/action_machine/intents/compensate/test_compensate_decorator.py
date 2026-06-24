# tests/intents/compensate/test_compensate_decorator.py
"""
Tests for @compensate — validation at class definition time.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Verifies that @compensate validates arguments, method signature, and name suffix
when the class is defined (import time). All tests are synchronous and do not
require running the machine.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestCompensateDecoratorSuccess      — valid cases
TestCompensateTargetErrors          — target_aspect errors
TestCompensateDescriptionErrors     — description errors
TestCompensateMethodErrors          — method errors (sync, signature)
TestCompensateNamingSuffix          — method name suffix errors
"""

from __future__ import annotations

import pytest

from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.context_requires import context_requires

# ─────────────────────────────────────────────────────────────────────────────
# Stub callable used as target_aspect across tests
# ─────────────────────────────────────────────────────────────────────────────


async def _stub_aspect(self, params, state, box, connections):
    pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateDecoratorSuccess — valid cases
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateDecoratorSuccess:
    """@compensate works correctly with valid data."""

    def test_correct_decorator_with_7_params(self) -> None:
        """
        Valid decorator with 7 parameters (without @context_requires).
        """

        class Action:
            async def charge_aspect(self, params, state, box, connections):
                pass

            @compensate(charge_aspect, "Compensator description")
            async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
                pass

        method = Action.rollback_compensate
        assert hasattr(method, "_compensate_meta")
        meta = method._compensate_meta
        assert meta["target_aspect"] is Action.charge_aspect
        assert meta["description"] == "Compensator description"

    def test_correct_decorator_with_8_params_and_context_requires(self) -> None:
        """
        Valid decorator with 8 parameters (with @context_requires).
        """

        class Action:
            async def charge_aspect(self, params, state, box, connections):
                pass

            @compensate(charge_aspect, "Description with context")
            @context_requires("user.user_id")
            async def rollback_with_context_compensate(
                self, params, state_before, state_after, box, connections, error, ctx
            ):
                pass

        method = Action.rollback_with_context_compensate
        assert hasattr(method, "_compensate_meta")
        meta = method._compensate_meta
        assert meta["target_aspect"] is Action.charge_aspect
        assert meta["description"] == "Description with context"
        assert hasattr(method, "_required_context_keys")
        assert method._required_context_keys == {"user.user_id"}

    def test_decorator_returns_same_function(self) -> None:
        """
        Decorator returns the same function object (not a wrapper).
        """

        async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
            pass

        decorated = compensate(_stub_aspect, "Description")(rollback_compensate)
        assert decorated is rollback_compensate


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateTargetErrors — target_aspect errors
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateTargetErrors:
    """Validates target_aspect parameter."""

    def test_target_aspect_not_callable(self) -> None:
        """Non-callable target_aspect → TypeError."""
        with pytest.raises(TypeError, match="target_aspect must be a callable"):

            @compensate(123, "Description")
            async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
                pass

    def test_target_aspect_callable_without_name(self) -> None:
        """Callable without __name__ → TypeError."""

        class _NoName:
            def __call__(self):
                pass

        with pytest.raises(TypeError, match="target_aspect must have __name__"):

            @compensate(_NoName(), "Description")
            async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateDescriptionErrors — description errors
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateDescriptionErrors:
    """Validates description parameter."""

    def test_description_not_string(self) -> None:
        """Non-string description → TypeError."""
        with pytest.raises(TypeError, match="description must be a string"):

            @compensate(_stub_aspect, 123)
            async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
                pass

    def test_description_empty_string(self) -> None:
        """Empty description → ValueError."""
        with pytest.raises(ValueError, match="description cannot be empty"):

            @compensate(_stub_aspect, "")
            async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
                pass

    def test_description_whitespace_only(self) -> None:
        """Whitespace-only description → ValueError."""
        with pytest.raises(ValueError, match="description cannot be empty"):

            @compensate(_stub_aspect, "   ")
            async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateMethodErrors — method errors
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateMethodErrors:
    """Validates the decorated method."""

    def test_sync_method(self) -> None:
        """Sync method → TypeError requiring async def."""
        with pytest.raises(TypeError, match="must be async"):

            @compensate(_stub_aspect, "Description")
            def sync_compensate(self, params, state_before, state_after, box, connections, error):
                pass

    def test_too_few_parameters_without_context(self) -> None:
        """Fewer than 7 parameters without @context_requires → TypeError."""
        with pytest.raises(TypeError, match="must accept 7 parameters"):

            @compensate(_stub_aspect, "Description")
            async def too_few_params_compensate(self, params, state_before, state_after, box, connections):
                pass

    def test_too_many_parameters_without_context(self) -> None:
        """More than 7 parameters without @context_requires → TypeError."""
        with pytest.raises(TypeError, match="must accept 7 parameters"):

            @compensate(_stub_aspect, "Description")
            async def too_many_params_compensate(
                self, params, state_before, state_after, box, connections, error, extra
            ):
                pass

    def test_too_few_parameters_with_context(self) -> None:
        """Fewer than 8 parameters with @context_requires → TypeError."""
        with pytest.raises(TypeError, match="must accept 8 parameters"):

            @compensate(_stub_aspect, "Description")
            @context_requires("user.user_id")
            async def too_few_with_ctx_compensate(self, params, state_before, state_after, box, connections, error):
                pass

    def test_too_many_parameters_with_context(self) -> None:
        """More than 8 parameters with @context_requires → TypeError."""
        with pytest.raises(TypeError, match="must accept 8 parameters"):

            @compensate(_stub_aspect, "Description")
            @context_requires("user.user_id")
            async def too_many_with_ctx_compensate(
                self, params, state_before, state_after, box, connections, error, ctx, extra
            ):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateNamingSuffix — method name suffix errors
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateNamingSuffix:
    """Compensator method name must end with '_compensate'."""

    def test_method_without_compensate_suffix(self) -> None:
        """Method name not ending with '_compensate' → ValueError."""
        with pytest.raises(ValueError, match="must end with '_compensate'"):

            @compensate(_stub_aspect, "Description")
            async def rollback_wrong(self, params, state_before, state_after, box, connections, error):
                pass

    def test_method_with_wrong_suffix(self) -> None:
        """Method name with wrong suffix → ValueError."""
        with pytest.raises(ValueError, match="must end with '_compensate'"):

            @compensate(_stub_aspect, "Description")
            async def rollback_rollback(self, params, state_before, state_after, box, connections, error):
                pass

    def test_method_with_correct_suffix(self) -> None:
        """Method name with '_compensate' suffix — success."""

        class Action:
            @compensate(_stub_aspect, "Description")
            async def rollback_compensate(self, params, state_before, state_after, box, connections, error):
                pass

        assert hasattr(Action.rollback_compensate, "_compensate_meta")
