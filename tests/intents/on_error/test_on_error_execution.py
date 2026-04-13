# tests/intents/on_error/test_on_error_execution.py
"""
Tests for executing @on_error handlers in ActionProductMachine.
═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════
Verifies the error handling mechanism for aspects in the machine:
- Handler catches the appropriate exception → returns Result.
- Handler does not catch foreign exceptions → propagates outward.
- Multiple handlers — first suitable one (top to bottom).
- Handler throws exception → OnErrorHandlerError.
- Action without @on_error → exception propagates.
- Normal execution (no error) → @on_error not called.
- Regression: Action with @on_error WITHOUT compensators — behavior
  unchanged after introducing compensation mechanism (Saga).

All tests use Actions from tests/domain/error_actions.py.
"""
import pytest

from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.model.exceptions import OnErrorHandlerError
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from action_machine.testing import TestBench
from tests.scenarios.domain_model import (
    ErrorHandledAction,
    ErrorTestParams,
    HandlerRaisesAction,
    MultiErrorAction,
    NoErrorHandlerAction,
)

# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def bench() -> TestBench:
    """TestBench with quiet logger (no console output)."""
    return TestBench(
        coordinator=CoreActionMachine.create_coordinator(),
        log_coordinator=LogCoordinator(loggers=[]),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Handler catches matching exception
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorCatchesMatchingException:
    """@on_error handler catches exception of matching type and returns Result."""

    @pytest.mark.asyncio()
    async def test_value_error_handled(self, bench: TestBench) -> None:
        """ValueError in aspect → handler returns Result with status 'handled'."""
        # Arrange — parameters causing error in aspect
        params = ErrorTestParams(value="test", should_fail=True)
        # Act — machine executes action, aspect throws ValueError,
        # handler catches and returns Result
        result = await bench.run(
            ErrorHandledAction(),
            params,
            rollup=False,
        )
        # Assert — result from handler, not from summary
        assert result.status == "handled"
        assert "Processing error: test" in result.detail

    @pytest.mark.asyncio()
    async def test_normal_execution_no_error(self, bench: TestBench) -> None:
        """No error in aspect → normal Result, handler not called."""
        # Arrange — parameters without error
        params = ErrorTestParams(value="hello", should_fail=False)
        # Act — normal pipeline execution
        result = await bench.run(
            ErrorHandledAction(),
            params,
            rollup=False,
        )
        # Assert — result from summary, not from handler
        assert result.status == "ok"
        assert result.detail == "hello"


# ═════════════════════════════════════════════════════════════════════════════
# Multiple handlers — order top to bottom
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorMultipleHandlers:
    """Multiple @on_error — first suitable handler is called."""

    @pytest.mark.asyncio()
    async def test_insufficient_funds_caught_by_specific_handler(self, bench: TestBench) -> None:
        """InsufficientFundsError → first (specific) handler."""
        # Arrange — value="insufficient" triggers InsufficientFundsError in aspect
        params = ErrorTestParams(value="insufficient")
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — caught by specific handler
        assert result.status == "insufficient_funds"

    @pytest.mark.asyncio()
    async def test_gateway_error_caught_by_specific_handler(self, bench: TestBench) -> None:
        """PaymentGatewayError → second (specific) handler."""
        # Arrange — value="gateway" triggers PaymentGatewayError
        params = ErrorTestParams(value="gateway")
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — caught by second handler
        assert result.status == "gateway_error"

    @pytest.mark.asyncio()
    async def test_runtime_error_caught_by_fallback(self, bench: TestBench) -> None:
        """RuntimeError → third (general fallback) handler Exception."""
        # Arrange — should_fail=True triggers RuntimeError
        params = ErrorTestParams(value="anything", should_fail=True)
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — caught by fallback handler
        assert result.status == "unknown_error"

    @pytest.mark.asyncio()
    async def test_normal_execution(self, bench: TestBench) -> None:
        """No error → normal Result, no handler called."""
        # Arrange — normal parameters
        params = ErrorTestParams(value="ok", should_fail=False)
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — result from summary
        assert result.status == "ok"
        assert result.detail == "ok"


# ═════════════════════════════════════════════════════════════════════════════
# Action without @on_error — error propagates
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorNoHandler:
    """Action without @on_error — aspect exception propagates outward."""

    @pytest.mark.asyncio()
    async def test_error_propagates_without_handler(self, bench: TestBench) -> None:
        """ValueError without handler → propagates to calling code."""
        # Arrange — parameters causing error
        params = ErrorTestParams(value="fail", should_fail=True)
        # Act & Assert — ValueError not caught, propagates outward
        with pytest.raises(ValueError, match="Error: fail"):
            await bench.run(NoErrorHandlerAction(), params, rollup=False)


# ═════════════════════════════════════════════════════════════════════════════
# Handler does not match type — error propagates
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorTypeMismatch:
    """Handler catches only its type — foreign exceptions propagate."""

    @pytest.mark.asyncio()
    async def test_type_error_not_caught_by_value_error_handler(self, bench: TestBench) -> None:
        """TypeError not caught by ValueError handler → propagates."""
        # Arrange — create Action whose aspect throws TypeError,
        # but handler catches only ValueError.
        # ErrorHandledAction catches ValueError. Override aspect via
        # inheritance (edge-case test — class created inside test).
        from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
        from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
        from action_machine.intents.auth import NoneRole, check_roles
        from action_machine.intents.checkers import result_string
        from action_machine.intents.meta.meta_decorator import meta
        from action_machine.intents.on_error import on_error
        from action_machine.model.base_action import BaseAction
        from tests.scenarios.domain_model import OrdersDomain
        from tests.scenarios.domain_model.error_actions import ErrorTestParams, ErrorTestResult

        @meta(description="Throws TypeError, catches ValueError", domain=OrdersDomain)
        @check_roles(NoneRole)
        class TypeMismatchAction(BaseAction[ErrorTestParams, ErrorTestResult]):
            @regular_aspect("Throws TypeError")
            @result_string("processed", required=True)
            async def process_aspect(self, params, state, box, connections):
                raise TypeError("Invalid type")
                return {"processed": "never"}

            @summary_aspect("Result")
            async def result_summary(self, params, state, box, connections):
                return ErrorTestResult(status="ok")

            @on_error(ValueError, description="Catches only ValueError")
            async def handle_value_on_error(self, params, state, box, connections, error):
                return ErrorTestResult(status="handled")

        params = ErrorTestParams(value="test")
        # Act & Assert — TypeError not caught by ValueError handler
        with pytest.raises(TypeError, match="Invalid type"):
            await bench.run(TypeMismatchAction(), params, rollup=False)


# ═════════════════════════════════════════════════════════════════════════════
# Handler itself throws exception → OnErrorHandlerError
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorHandlerRaises:
    """Handler itself throws exception → OnErrorHandlerError."""

    @pytest.mark.asyncio()
    async def test_handler_exception_wrapped(self, bench: TestBench) -> None:
        """Handler throws RuntimeError → OnErrorHandlerError with __cause__."""
        # Arrange — should_fail=True → ValueError → handler → RuntimeError
        params = ErrorTestParams(value="test", should_fail=True)
        # Act & Assert — OnErrorHandlerError wraps RuntimeError
        with pytest.raises(OnErrorHandlerError) as exc_info:
            await bench.run(HandlerRaisesAction(), params, rollup=False)
        # Assert — check OnErrorHandlerError attributes
        error = exc_info.value
        assert error.handler_name == "handle_and_fail_on_error"
        assert isinstance(error.original_error, ValueError)
        assert error.__cause__ is not None
        assert isinstance(error.__cause__, RuntimeError)


# ═════════════════════════════════════════════════════════════════════════════
# Handlers are not inherited
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorNotInherited:
    """@on_error handlers are NOT inherited from parent Action."""

    @pytest.mark.asyncio()
    async def test_child_action_does_not_inherit_handlers(self, bench: TestBench) -> None:
        """Child Action without own @on_error — error propagates."""
        # Arrange — create child class of ErrorHandledAction without its own handlers.
        # Parent ErrorHandledAction has @on_error(ValueError),
        # but child should not inherit it.
        from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
        from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
        from action_machine.intents.auth import NoneRole, check_roles
        from action_machine.intents.checkers import result_string
        from action_machine.intents.meta.meta_decorator import meta
        from action_machine.model.base_action import BaseAction
        from tests.scenarios.domain_model import OrdersDomain
        from tests.scenarios.domain_model.error_actions import ErrorTestParams, ErrorTestResult

        @meta(description="Child without own handlers", domain=OrdersDomain)
        @check_roles(NoneRole)
        class ChildNoHandlerAction(BaseAction[ErrorTestParams, ErrorTestResult]):
            """Child Action — overrides aspects but has no @on_error."""

            @regular_aspect("Processing with error")
            @result_string("processed", required=True)
            async def process_aspect(self, params, state, box, connections):
                if params.should_fail:
                    raise ValueError("Error in child")
                return {"processed": params.value}

            @summary_aspect("Result")
            async def result_summary(self, params, state, box, connections):
                return ErrorTestResult(status="ok", detail=state["processed"])

        params = ErrorTestParams(value="test", should_fail=True)
        # Act & Assert — ValueError propagates, parent handler does NOT work
        with pytest.raises(ValueError, match="Error in child"):
            await bench.run(ChildNoHandlerAction(), params, rollup=False)


# ═════════════════════════════════════════════════════════════════════════════
# Regression: @on_error without compensators — behavior unchanged
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorWithoutCompensatorsRegression:
    """
    Regression test: Action with @on_error WITHOUT compensators works
    the same as before introducing the compensation mechanism (Saga).

    After adding saga_stack to _execute_regular_aspects() and
    _rollback_saga() to _execute_aspects_with_error_handling(), it is important
    to ensure that Actions without @compensate continue to handle errors
    correctly through @on_error — without attempting to unwind an empty stack,
    without extra events, without side effects.
    """

    @pytest.mark.asyncio()
    async def test_on_error_works_without_compensators(self, bench: TestBench) -> None:
        """
        ErrorHandledAction has no @compensate.
        ValueError in aspect → @on_error catches → Result(status="handled").
        Stack unwinding not performed (saga_stack empty, has_compensators=False).
        Behavior identical to before Saga introduction.
        """
        # Arrange — parameters causing error in aspect
        params = ErrorTestParams(value="regression_test", should_fail=True)

        # Act — machine executes action, aspect throws ValueError,
        # @on_error catches without compensation mechanism involvement
        result = await bench.run(
            ErrorHandledAction(),
            params,
            rollup=False,
        )

        # Assert — result from @on_error handler
        assert result.status == "handled"
        assert "Processing error: regression_test" in result.detail

    @pytest.mark.asyncio()
    async def test_no_handler_propagates_without_compensators(self, bench: TestBench) -> None:
        """
        NoErrorHandlerAction has neither @compensate nor @on_error.
        ValueError propagates outward — behavior identical
        to before Saga introduction.
        """
        # Arrange — parameters causing error
        params = ErrorTestParams(value="no_handler", should_fail=True)

        # Act & Assert — ValueError propagates unchanged
        with pytest.raises(ValueError, match="Error: no_handler"):
            await bench.run(NoErrorHandlerAction(), params, rollup=False)
