# packages/aoa-demo/tests/fastapi_mcp_services/test_cancel_order.py
"""``CancelOrderAction`` — role, guard, and access_decide together (own vs. foreign order)."""

from __future__ import annotations

import pytest

from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Allowed, Gate, Refused
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


async def test_a_foreign_order_is_refused_by_the_object_step(machine: ActionProductMachine) -> None:
    with pytest.raises(AccessDenied) as exc_info:
        await machine.run(_customer_context("bob"), CancelOrderAction(), _own_order_params())
    assert exc_info.value.verdict.gate is Gate.ACCESS_DECIDE


async def test_a_locked_order_is_refused_by_the_guard(machine: ActionProductMachine) -> None:
    params = CancelOrderAction.Params(order_id="LOCKED-1", owner_user_id="alice")
    with pytest.raises(AccessDenied) as exc_info:
        await machine.run(_customer_context("alice"), CancelOrderAction(), params)
    assert exc_info.value.verdict.gate is Gate.GUARD
    assert exc_info.value.verdict.reason == "ORDER_LOCKED"


async def test_an_anonymous_caller_is_refused_by_the_roles_step(machine: ActionProductMachine) -> None:
    with pytest.raises(AccessDenied) as exc_info:
        await machine.run(Context(), CancelOrderAction(), _own_order_params())
    assert exc_info.value.verdict.gate is Gate.CHECK_ROLES


async def test_check_access_decide_matches_run_semantics(machine: ActionProductMachine) -> None:
    """The advance answer names the same step the executed call would be stopped by."""
    own = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, _own_order_params())
    assert isinstance(own, Allowed)

    foreign = await machine.check_access_decide(_customer_context("bob"), CancelOrderAction, _own_order_params())
    assert isinstance(foreign, Refused)
    assert foreign.gate is Gate.ACCESS_DECIDE

    locked_params = CancelOrderAction.Params(order_id="LOCKED-1", owner_user_id="alice")
    locked = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, locked_params)
    assert isinstance(locked, Refused)
    assert locked.gate is Gate.GUARD  # the shared guard=, not a grant's own condition

    anonymous = await machine.check_access_decide(Context(), CancelOrderAction, _own_order_params())
    assert isinstance(anonymous, Refused)
    assert anonymous.gate is Gate.CHECK_ROLES
