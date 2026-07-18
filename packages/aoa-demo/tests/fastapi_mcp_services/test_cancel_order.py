# packages/aoa-demo/tests/fastapi_mcp_services/test_cancel_order.py
"""``CancelOrderAction`` — role, guard, and access_decide together (own vs. foreign order)."""

from __future__ import annotations

import pytest

from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.access_control import AccessVerdict, ResolveItemKind
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.demo.fastapi_mcp_services.actions.cancel_order import CancelOrderAction, CustomerRole


@pytest.fixture(scope="module")
def machine() -> ActionProductMachine:
    return ActionProductMachine(cache_coordinator=None)


def _customer_context(user_id: str) -> Context:
    return Context(user=UserInfo(user_id=user_id, roles=(CustomerRole,)))


def _own_order_params() -> CancelOrderAction.Params:
    return CancelOrderAction.Params(order_id="ORD-1", owner_user_id="alice")


async def test_own_order_cancel_succeeds(machine: ActionProductMachine) -> None:
    result = await machine.run(_customer_context("alice"), CancelOrderAction(), _own_order_params())
    assert result == CancelOrderAction.Result(order_id="ORD-1", status="cancelled")


async def test_foreign_order_raises_authorization_error_level_3(machine: ActionProductMachine) -> None:
    with pytest.raises(AuthorizationError) as exc_info:
        await machine.run(_customer_context("bob"), CancelOrderAction(), _own_order_params())
    assert exc_info.value.level == 3
    # access_decide's own clean reason= mechanism is a separate, not-yet-done change —
    # today its rejection still surfaces the raw AuthorizationError message.
    assert "access_decide() returned False" in str(exc_info.value)


async def test_locked_order_denied_by_guard_level_2(machine: ActionProductMachine) -> None:
    params = CancelOrderAction.Params(order_id="LOCKED-1", owner_user_id="alice")
    with pytest.raises(AuthorizationError) as exc_info:
        await machine.run(_customer_context("alice"), CancelOrderAction(), params)
    assert exc_info.value.level == 2
    assert exc_info.value.reason == "order is locked"


async def test_anonymous_caller_denied_level_1(machine: ActionProductMachine) -> None:
    with pytest.raises(AuthorizationError) as exc_info:
        await machine.run(Context(), CancelOrderAction(), _own_order_params())
    assert exc_info.value.level == 1
    assert exc_info.value.reason == "FORBIDDEN_ROLE"


async def test_check_access_decide_matches_run_semantics(machine: ActionProductMachine) -> None:
    own = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, _own_order_params())
    assert own == AccessVerdict(action=CancelOrderAction, kind=ResolveItemKind.SUCCESS, reason="")

    foreign = await machine.check_access_decide(_customer_context("bob"), CancelOrderAction, _own_order_params())
    assert foreign.kind == ResolveItemKind.SECURITY
    assert "access_decide() returned False" in foreign.reason

    locked_params = CancelOrderAction.Params(order_id="LOCKED-1", owner_user_id="alice")
    locked = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, locked_params)
    assert locked.kind == ResolveItemKind.SECURITY
    assert locked.reason == "order is locked"

    anonymous = await machine.check_access_decide(Context(), CancelOrderAction, _own_order_params())
    assert anonymous.kind == ResolveItemKind.SECURITY
    assert anonymous.reason == "FORBIDDEN_ROLE"
