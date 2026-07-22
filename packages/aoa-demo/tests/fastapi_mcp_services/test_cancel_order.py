# packages/aoa-demo/tests/fastapi_mcp_services/test_cancel_order.py
"""``CancelOrderAction`` — role, guard, and access_decide together (own vs. foreign order)."""

from __future__ import annotations

import pytest

from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.access_control import AllowedVerdict, FailSecurityVerdict
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
    # access_decide's own clean reason= mechanism: it returns FailSecurityVerdict
    # directly, with a developer-chosen reason -- no more raw exception text.
    assert exc_info.value.reason == "order does not belong to the caller"


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
    assert own == AllowedVerdict()

    foreign = await machine.check_access_decide(_customer_context("bob"), CancelOrderAction, _own_order_params())
    assert isinstance(foreign, FailSecurityVerdict)
    assert foreign.reason == "order does not belong to the caller"

    locked_params = CancelOrderAction.Params(order_id="LOCKED-1", owner_user_id="alice")
    locked = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, locked_params)
    assert isinstance(locked, FailSecurityVerdict)
    assert locked.reason == "order is locked"

    anonymous = await machine.check_access_decide(Context(), CancelOrderAction, _own_order_params())
    assert isinstance(anonymous, FailSecurityVerdict)
    assert anonymous.reason == "FORBIDDEN_ROLE"
