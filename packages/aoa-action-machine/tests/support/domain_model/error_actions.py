# tests/scenarios/domain_model/error_actions.py
"""
Actions with @on_error handlers for error-handling tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides Actions that exercise @on_error scenarios:

- ErrorHandledAction — single handler catching ValueError.
- HandlerRaisesAction — handler raises → OnErrorHandlerError.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

    from ...support.domain_model.error_actions import (
        ErrorHandledAction,
        HandlerRaisesAction,
    )
"""

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from .domains import OrdersDomain

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
@check_roles(GuestRole)
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
        connections: dict[str, BaseResource],
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
        connections: dict[str, BaseResource],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(ValueError, description="Handle validation error")
    async def handle_validation_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="handled", detail=str(error))


# ═════════════════════════════════════════════════════════════════════════════
# HandlerRaisesAction — handler itself raises
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action whose error handler raises", domain=OrdersDomain)
@check_roles(GuestRole)
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
        connections: dict[str, BaseResource],
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
        connections: dict[str, BaseResource],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(ValueError, description="Handler that fails")
    async def handle_and_fail_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        error: Exception,
    ) -> ErrorTestResult:
        raise RuntimeError(f"Error in handler: {error}")
