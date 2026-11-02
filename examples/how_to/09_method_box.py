"""
09_method_box.py — Every method of an action gets its own box

Every method that receives `box` receives one of its own, with its own name. Its log
therefore knows which method is writing, and the log's action and method names give
the id of that method's node in the graph: `<action>:<method>`.

    kind               {%scope.aspect}      what {%state.x} reads
    @regular_aspect    the method's name    the current state
    @summary_aspect    the method's name    the current state
    @compensate        the method's name    the snapshot before its step
    @on_error          the handler's name   the state the handler receives
    @access_decide     the method's name    nothing: it has no state

The cases below run one operation and print what each answers:

    1. every kind names itself
    2. a handler's log reads the handler's state
    3. a handler naming a field nobody wrote: OnErrorHandlerError
    4. a check is named the same on a real call and when asked in advance
    5. a check naming a field of state: undecided, because it has no state
    6. several handlers: the line names the one that ran
    7. a nested action's handler: its own action and nesting level
    8. @context_requires: the view and the own box arrive together
    9. an error no handler matches: it goes up unchanged

Reference: ../../docs/reference/intents-and-invariants.md

Run:
    uv run python examples/how_to/09_method_box.py
"""

import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.ctx_constants import Ctx
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.access_undecided import AccessUndecided
from aoa.action_machine.exceptions.on_error_handler_error import OnErrorHandlerError
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import Channel
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox


class WarehouseDomain(BaseDomain):
    name = "warehouse"
    description = "Stock reservations"


class ReserveParams(BaseParams):
    fail_in: str = Field(default="", description="The step that raises: 'first', 'second', 'unhandled' or nothing")
    check_reads_state: bool = Field(default=False, description="Make the check name a field of state")


class ReserveResult(BaseResult):
    outcome: str = Field(description="Who produced the result")


class PrintingLogger(BaseLogger):
    """Prints who wrote each line and what the line says."""

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        print(f"  [nest {scope.nest_level}] {scope.action.rsplit('.', 1)[-1]}:{scope.aspect}  {message}")


@meta(description="Reserve stock", domain=WarehouseDomain)
@check_roles(GuestRole)
class ReserveAction(BaseAction[ReserveParams, ReserveResult]):
    @access_decide("Anyone may reserve")
    async def reserve_access_decide(self, params: ReserveParams, box: ToolsBox, connections: Connections) -> Verdict:
        await box.info(Channel.business, "checking access")
        if params.check_reads_state:
            await box.info(Channel.business, "reserved={%state.reserved}")
        return Allowed()

    @regular_aspect("Reserve the stock")
    @result_string("reserved", required=True)
    async def reserve_aspect(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        if params.fail_in == "first":
            raise ValueError("no stock")
        await box.info(Channel.business, "reserving")
        return {"reserved": "yes"}

    @compensate(reserve_aspect, "Release the stock")
    async def reserve_compensate(
        self,
        params: ReserveParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        await box.info(Channel.business, "releasing")

    @regular_aspect("Charge")
    @result_string("reserved", required=True)
    async def charge_aspect(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        if params.fail_in == "second":
            raise ValueError("card declined")
        if params.fail_in == "unhandled":
            raise KeyError("no handler for this one")
        return {"reserved": state["reserved"]}

    @summary_aspect("Report")
    async def report_summary(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ReserveResult:
        await box.info(Channel.business, "reporting")
        return ReserveResult(outcome="reported")

    @on_error(ValueError, description="A step failed")
    async def reserve_on_error(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections, error: Exception
    ) -> ReserveResult:
        await box.info(Channel.business, "failed with reserved={%state.reserved}")
        return ReserveResult(outcome="handled")


@meta(description="Two handlers, one chosen by the failure", domain=WarehouseDomain)
@check_roles(GuestRole)
class ShipAction(BaseAction[ReserveParams, ReserveResult]):
    @regular_aspect("Ship")
    async def ship_aspect(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        raise KeyError("no address") if params.fail_in == "address" else ValueError("no courier")

    @summary_aspect("Report")
    async def report_summary(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ReserveResult:
        return ReserveResult(outcome="reported")

    @on_error(ValueError, description="No courier")
    async def courier_on_error(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections, error: Exception
    ) -> ReserveResult:
        await box.info(Channel.business, "waiting for a courier")
        return ReserveResult(outcome="courier")

    @on_error(KeyError, description="No address")
    async def address_on_error(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections, error: Exception
    ) -> ReserveResult:
        await box.info(Channel.business, "asking for an address")
        return ReserveResult(outcome="address")


@meta(description="Runs a child whose own handler answers", domain=WarehouseDomain)
@check_roles(GuestRole)
class OrderAction(BaseAction[ReserveParams, ReserveResult]):
    @summary_aspect("Ship the order")
    async def ship_order_summary(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ReserveResult:
        await box.info(Channel.business, "shipping")
        return await box.run(ShipAction, ReserveParams())


@meta(description="A check and a handler that asked for context", domain=WarehouseDomain)
@check_roles(GuestRole)
class AuditAction(BaseAction[ReserveParams, ReserveResult]):
    @access_decide("Only the named user")
    @context_requires(Ctx.User.user_id)
    async def audit_access_decide(
        self, params: ReserveParams, box: ToolsBox, connections: Connections, ctx: ContextView
    ) -> Verdict:
        await box.info(Channel.business, "checking {%var.user}", user=ctx.get(Ctx.User.user_id))
        return Allowed()

    @regular_aspect("Open")
    @result_string("opened", required=True)
    async def open_aspect(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        return {"opened": "yes"}

    @regular_aspect("Fail")
    async def fail_aspect(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        raise ValueError("audit failed")

    @summary_aspect("Report")
    async def report_summary(
        self, params: ReserveParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ReserveResult:
        return ReserveResult(outcome="reported")

    @on_error(ValueError, description="The audit failed")
    @context_requires(Ctx.User.user_id)
    async def audit_on_error(
        self,
        params: ReserveParams,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
        ctx: ContextView,
    ) -> ReserveResult:
        await box.info(Channel.business, "{%var.user}: opened={%state.opened}", user=ctx.get(Ctx.User.user_id))
        return ReserveResult(outcome="handled")


async def main() -> None:
    machine = ActionProductMachine(cache_coordinator=None, log_coordinator=LogCoordinator(loggers=[PrintingLogger()]))
    context = Context()

    print("1. Every kind names itself, on a run that succeeds:")
    print(" ", (await machine.run(context, ReserveAction(), ReserveParams())).outcome)

    print("2. A later step fails: the compensator and the handler name themselves, and the handler's log reads state:")
    print(" ", (await machine.run(context, ReserveAction(), ReserveParams(fail_in="second"))).outcome)

    print("3. The first step fails, nothing was written, and the handler names a field:")
    try:
        await machine.run(context, ReserveAction(), ReserveParams(fail_in="first"))
    except OnErrorHandlerError as error:
        print(f"  {type(error).__name__}: {error}")

    print("4. Asked in advance, the check is named the same:")
    print(" ", (await machine.check_access_decide(context, ReserveAction, ReserveParams())).kind)

    print("5. A check names a field of state, and it has no state:")
    answer = await machine.check_access_decide(context, ReserveAction, ReserveParams(check_reads_state=True))
    print(f"  asked in advance: {answer.kind} at {answer.gate.value}")
    try:
        await machine.run(context, ReserveAction(), ReserveParams(check_reads_state=True))
    except AccessUndecided as error:
        print(f"  on a real call: {type(error).__name__} at {error.verdict.gate.value}")

    print("6. Several handlers: the line names the one that ran:")
    print(" ", (await machine.run(context, ShipAction(), ReserveParams())).outcome)
    print(" ", (await machine.run(context, ShipAction(), ReserveParams(fail_in="address"))).outcome)

    print("7. A nested action's handler keeps its own action and nesting level:")
    print(" ", (await machine.run(context, OrderAction(), ReserveParams())).outcome)

    print("8. @context_requires: the view and the own box arrive together:")
    print(" ", (await machine.run(Context(user=UserInfo(user_id="u1")), AuditAction(), ReserveParams())).outcome)

    print("9. No handler matches: the error goes up unchanged:")
    try:
        await machine.run(context, ReserveAction(), ReserveParams(fail_in="unhandled"))
    except KeyError as error:
        print(f"  {type(error).__name__}: {error}")


if __name__ == "__main__":
    asyncio.run(main())
