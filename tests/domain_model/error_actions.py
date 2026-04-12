# tests/domain_model/error_actions.py
"""
Actions with @on_error handlers for error-handling tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides Actions that exercise @on_error scenarios:

- ErrorHandledAction — single handler catching ValueError.
- MultiErrorAction — multiple handlers (specific → general).
- NoErrorHandlerAction — no @on_error (errors propagate).
- HandlerRaisesAction — handler raises → OnErrorHandlerError.

═══════════════════════════════════════════════════════════════════════════════
CUSTOM EXCEPTIONS
═══════════════════════════════════════════════════════════════════════════════

- InsufficientFundsError — not enough balance.
- PaymentGatewayError — payment gateway failure.

Both inherit Exception directly. Used to test handler ordering and type matching.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

    from tests.domain_model.error_actions import (
        ErrorHandledAction,
        MultiErrorAction,
        NoErrorHandlerAction,
        HandlerRaisesAction,
        InsufficientFundsError,
        PaymentGatewayError,
    )
"""

from typing import Any

from pydantic import Field

from action_machine.aspects.regular_aspect_decorator import regular_aspect
from action_machine.aspects.summary_aspect_decorator import summary_aspect
from action_machine.auth import NoneRole, check_roles
from action_machine.checkers import result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.on_error import on_error
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .domains import OrdersDomain

# ═════════════════════════════════════════════════════════════════════════════
# Custom exceptions
# ═════════════════════════════════════════════════════════════════════════════


class InsufficientFundsError(Exception):
    """Not enough funds on the account."""
    pass


class PaymentGatewayError(Exception):
    """Payment gateway failure."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Shared Params / Result for error Actions
# ═════════════════════════════════════════════════════════════════════════════


class ErrorTestParams(BaseParams):
    """Parameters for error-handling test Actions."""
    value: str = Field(description="Value to process")
    should_fail: bool = Field(
        default=False,
        description="If True, the regular aspect raises an exception",
    )


class ErrorTestResult(BaseResult):
    """Result type for error-handling test Actions."""
    status: str = Field(description="Execution status")
    detail: str = Field(default="", description="Result details")


# ═════════════════════════════════════════════════════════════════════════════
# ErrorHandledAction — single ValueError handler
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action with a single ValueError handler", domain=OrdersDomain)
@check_roles(NoneRole)
class ErrorHandledAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Action with one @on_error handler for ValueError.

    When should_fail=True, the regular aspect raises ValueError.
    handle_validation_on_error catches it and returns Result(status="handled").

    Test scenarios:
    - should_fail=False → normal Result(status="ok").
    - should_fail=True → handler → Result(status="handled").
    """

    @regular_aspect("Process value")
    @result_string("processed", required=True)
    async def process_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_fail:
            raise ValueError(f"Processing error: {params.value}")
        return {"processed": params.value}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(ValueError, description="Handle validation error")
    async def handle_validation_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="handled", detail=str(error))


# ═════════════════════════════════════════════════════════════════════════════
# MultiErrorAction — multiple handlers (specific → general)
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action with multiple error handlers", domain=OrdersDomain)
@check_roles(NoneRole)
class MultiErrorAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Action with three @on_error handlers from specific to general.

    Handler order:
    1. InsufficientFundsError — specific.
    2. PaymentGatewayError — specific.
    3. Exception — general fallback.

    Test scenarios:
    - InsufficientFundsError → handler 1 → status="insufficient_funds".
    - PaymentGatewayError → handler 2 → status="gateway_error".
    - RuntimeError (or any Exception) → handler 3 → status="unknown_error".
    - No error → normal Result(status="ok").
    """

    @regular_aspect("Execute operation")
    @result_string("processed", required=True)
    async def execute_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.value == "insufficient":
            raise InsufficientFundsError("Insufficient funds")
        if params.value == "gateway":
            raise PaymentGatewayError("Gateway unavailable")
        if params.should_fail:
            raise RuntimeError("Unexpected error")
        return {"processed": params.value}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(InsufficientFundsError, description="Insufficient funds")
    async def insufficient_funds_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="insufficient_funds", detail=str(error))

    @on_error(PaymentGatewayError, description="Payment gateway error")
    async def gateway_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="gateway_error", detail=str(error))

    @on_error(Exception, description="Unexpected error")
    async def fallback_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="unknown_error", detail=str(error))


# ═════════════════════════════════════════════════════════════════════════════
# NoErrorHandlerAction — no @on_error (errors propagate)
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action without error handlers", domain=OrdersDomain)
@check_roles(NoneRole)
class NoErrorHandlerAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Action without @on_error — aspect errors propagate to the caller.

    Test scenarios:
    - should_fail=True → ValueError propagates.
    - should_fail=False → normal Result(status="ok").
    """

    @regular_aspect("Process value")
    @result_string("processed", required=True)
    async def process_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_fail:
            raise ValueError(f"Error: {params.value}")
        return {"processed": params.value}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])


# ═════════════════════════════════════════════════════════════════════════════
# HandlerRaisesAction — handler itself raises
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action whose error handler raises", domain=OrdersDomain)
@check_roles(NoneRole)
class HandlerRaisesAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Action whose @on_error handler raises.

    The aspect raises ValueError. handle_and_fail_on_error catches it
    but raises RuntimeError. The machine wraps that in OnErrorHandlerError.

    Test scenarios:
    - should_fail=True → ValueError → handler → RuntimeError →
      OnErrorHandlerError with __cause__=RuntimeError
      and original_error=ValueError.
    """

    @regular_aspect("Process value")
    @result_string("processed", required=True)
    async def process_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_fail:
            raise ValueError(f"Error: {params.value}")
        return {"processed": params.value}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(ValueError, description="Handler that fails")
    async def handle_and_fail_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        raise RuntimeError(f"Error in handler: {error}")
