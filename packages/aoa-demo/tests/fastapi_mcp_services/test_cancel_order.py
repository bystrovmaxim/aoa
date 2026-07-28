# packages/aoa-demo/tests/fastapi_mcp_services/test_cancel_order.py
"""``CancelOrderAction`` — role, guard, and access_decide together (own vs. foreign order)."""

from __future__ import annotations

import pytest

from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDeniedError, AccessGate
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, AllowedVerdict, FailSecurityVerdict
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.demo.fastapi_mcp_services.actions.cancel_order import CancelOrderAction, CustomerRole


@pytest.fixture(scope="module")
def machine() -> ActionProductMachine:
    return ActionProductMachine(cache_coordinator=None)


def _customer_context(user_id: str) -> Context:
    return Context(user=UserInfo(user_id=user_id, roles=(CustomerRole,)))


def _own_order_params() -> CancelOrderAction.Params:
    """``ORD-1`` belongs to alice in the module's ``_ORDERS`` table."""
    return CancelOrderAction.Params(order_id="ORD-1")


async def test_own_order_cancel_succeeds(machine: ActionProductMachine) -> None:
    result = await machine.run(_customer_context("alice"), CancelOrderAction(), _own_order_params())
    assert result == CancelOrderAction.Result(order_id="ORD-1", status="cancelled")


async def test_foreign_order_raises_access_denied_error_level_3(machine: ActionProductMachine) -> None:
    with pytest.raises(AccessDeniedError) as exc_info:
        await machine.run(_customer_context("bob"), CancelOrderAction(), _own_order_params())
    assert exc_info.value.refused_by is AccessGate.ACCESS_DECIDE
    # Generic deny (oracle safety): a foreign order answers with the same
    # FORBIDDEN_OBJECT reason as a missing one -- see the test below.
    assert exc_info.value.reason == "FORBIDDEN_OBJECT"


async def test_locked_order_denied_by_guard_level_2(machine: ActionProductMachine) -> None:
    params = CancelOrderAction.Params(order_id="LOCKED-1")
    with pytest.raises(AccessDeniedError) as exc_info:
        await machine.run(_customer_context("alice"), CancelOrderAction(), params)
    assert exc_info.value.refused_by is AccessGate.WHEN_OR_GUARD
    assert exc_info.value.reason == "order is locked"


async def test_anonymous_caller_denied_level_1(machine: ActionProductMachine) -> None:
    with pytest.raises(AccessDeniedError) as exc_info:
        await machine.run(Context(), CancelOrderAction(), _own_order_params())
    assert exc_info.value.refused_by is AccessGate.CHECK_ROLES
    assert exc_info.value.reason == "FORBIDDEN_ROLE"


async def test_missing_order_gives_identical_verdict_to_foreign_order(machine: ActionProductMachine) -> None:
    """Oracle safety: "doesn't exist" and "exists but isn't yours" must be indistinguishable."""
    missing_params = CancelOrderAction.Params(order_id="NO-SUCH-ORDER")
    missing = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, missing_params)

    # ORD-2 exists and belongs to bob, so for alice it is a real foreign object.
    foreign_params = CancelOrderAction.Params(order_id="ORD-2")
    foreign = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, foreign_params)

    # Not just equal reason text -- the exact same shared verdict object, so the
    # two cases can never accidentally drift apart.
    assert missing is FORBIDDEN_OBJECT
    assert foreign is FORBIDDEN_OBJECT
    # And the serialized shape itself, pinned to a literal. Comparing the two
    # dumps to each other would compare one object with itself and pass no matter
    # what the constant says (audit-11 finding 5) -- this is what the client sees.
    assert missing.model_dump() == {"kind": "FailSecurityVerdict", "reason": "FORBIDDEN_OBJECT"}


async def test_specific_reason_visible_only_to_confirmed_owner(machine: ActionProductMachine) -> None:
    """A more specific denial reason is safe only once ownership is already confirmed."""
    own_cancelled = CancelOrderAction.Params(order_id="CANCELLED-1")  # alice's, already cancelled
    own = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, own_cancelled)
    assert isinstance(own, FailSecurityVerdict)
    assert own.reason == "order is already cancelled"

    # A non-owner probing the same order_id learns nothing beyond FORBIDDEN_OBJECT --
    # the specific "already cancelled" reason never reaches someone who hasn't
    # already proven ownership.
    foreign_cancelled = await machine.check_access_decide(_customer_context("bob"), CancelOrderAction, own_cancelled)
    assert foreign_cancelled is FORBIDDEN_OBJECT


async def test_ownership_cannot_be_claimed_by_the_request(machine: ActionProductMachine) -> None:
    """audit-11 finding 2: the caller must not be able to state who owns an order.

    ``owner_user_id`` used to be a ``Params`` field, so sending one's own id was enough
    to pass level 3 on somebody else's order. The owner now comes from ``_ORDERS``, and
    ``Params`` has no such field at all -- pydantic's ``extra="forbid"`` makes the old
    forged request a hard validation error rather than a silently accepted bypass."""
    assert "owner_user_id" not in CancelOrderAction.Params.model_fields

    with pytest.raises(ValueError):
        CancelOrderAction.Params(order_id="ORD-1", owner_user_id="bob")  # type: ignore[call-arg]

    # And the bypass it enabled is gone end to end: bob cannot reach alice's order.
    verdict = await machine.check_access_decide(_customer_context("bob"), CancelOrderAction, _own_order_params())
    assert verdict is FORBIDDEN_OBJECT
    with pytest.raises(AccessDeniedError):
        await machine.run(_customer_context("bob"), CancelOrderAction(), _own_order_params())


def test_the_orders_table_is_read_only_at_runtime() -> None:
    """narrow-audit finding 9: ``Final`` is an annotation, not a runtime lock.

    As a plain dict this table accepted
    ``cancel_order._ORDERS["ORD-1"] = _OrderRow("mallory", ...)``, reassigning an
    order's owner for the whole process. Unreachable from a request either way -- the
    point of finding 2 holds regardless -- but the annotation should not claim more
    than it delivers, and the rows themselves are already NamedTuples."""
    from aoa.demo.fastapi_mcp_services.actions import cancel_order

    with pytest.raises(TypeError):
        cancel_order._ORDERS["ORD-1"] = cancel_order._OrderRow(owner_user_id="mallory", status="pending")

    with pytest.raises(AttributeError):
        cancel_order._ORDERS["ORD-1"].owner_user_id = "mallory"  # type: ignore[misc]

    assert cancel_order._ORDERS["ORD-1"].owner_user_id == "alice"


async def test_check_access_decide_matches_run_semantics(machine: ActionProductMachine) -> None:
    own = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, _own_order_params())
    assert own == AllowedVerdict()

    foreign = await machine.check_access_decide(_customer_context("bob"), CancelOrderAction, _own_order_params())
    assert isinstance(foreign, FailSecurityVerdict)
    assert foreign.reason == "FORBIDDEN_OBJECT"

    locked_params = CancelOrderAction.Params(order_id="LOCKED-1")
    locked = await machine.check_access_decide(_customer_context("alice"), CancelOrderAction, locked_params)
    assert isinstance(locked, FailSecurityVerdict)
    assert locked.reason == "order is locked"

    anonymous = await machine.check_access_decide(Context(), CancelOrderAction, _own_order_params())
    assert isinstance(anonymous, FailSecurityVerdict)
    assert anonymous.reason == "FORBIDDEN_ROLE"
