# tests/test_fastapi_permissions_resolve_verdicts.py
"""
Direct (non-HTTP) tests for ``resolve_verdicts`` — dedup + per-item isolation (issue #130, PR 2).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``resolve_verdicts`` is called directly here, against a real ``ActionProductMachine``
and real ``@check_roles``-gated actions — no ``TestClient``, no HTTP, no mocking of
``machine.check_access_decide`` itself. Deduplication is asserted on
``ResolveOutcome.real_call_count`` (see the module docstring in ``permissions.py``
for why this is a return value, not a wire field, a log line, or a metrics counter).

``resolve_verdicts`` takes a ``plan_index`` (route + auth coordinator per operation)
and a ``prepared_by_operation`` (this call's context/connections per operation,
issue #130's ``EndpointExecutionPlan`` — see ``execution_plan.py``) instead of one
shared ``Context``. Tests build ``prepared_by_operation`` directly with a fixed
``PreparedEndpointContext`` — no ``Request``, no real auth coordinator round-trip —
since ``resolve_verdicts`` itself never calls ``prepare()``, only looks its result up.
"""

from aoa.action_machine.auth.auth_coordinator import NoAuthCoordinator
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.access_control import AllowedVerdict, FailErrorVerdict, FailSecurityVerdict
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.execution_plan import PreparedEndpointContext, build_execution_plan_index
from aoa.fastapi.permissions import ResolveOutcome, build_route_index, resolve_verdicts
from aoa.fastapi.permissions_schema import ResolveItem
from aoa.fastapi.route_record import FastApiRouteRecord

from .support import CancelOrderAction, ManagerRole, PingAction

_ROUTE_INDEX = build_route_index(
    [
        FastApiRouteRecord(action_class=CancelOrderAction, method="post", path="/actions/cancel-order"),
        FastApiRouteRecord(action_class=PingAction, method="get", path="/actions/ping"),
    ]
)


def _manager_context() -> Context:
    return Context(user=UserInfo(user_id="alice", roles=(ManagerRole,)))


#: None of these tests exercise auth coordinator selection itself — every route uses
#: the same fixed manager context, matching the single ``context`` these tests passed
#: before ``EndpointExecutionPlan`` existed.
_PLAN_INDEX = build_execution_plan_index(_ROUTE_INDEX, lambda record: NoAuthCoordinator(context=_manager_context()))
_PREPARED_BY_OPERATION = {operation: PreparedEndpointContext(context=_manager_context(), connections=None) for operation in _ROUTE_INDEX}


async def _resolve(
    items: list[ResolveItem],
    machine: ActionProductMachine,
    *,
    unauthorized_operations: frozenset[str] = frozenset(),
) -> ResolveOutcome:
    return await resolve_verdicts(
        items, _PLAN_INDEX, _PREPARED_BY_OPERATION, machine, unauthorized_operations=unauthorized_operations
    )


def _order_item(order_id: int) -> ResolveItem:
    return ResolveItem(operation="POST /actions/cancel-order", params={"order_id": order_id})


def _unknown_item() -> ResolveItem:
    return ResolveItem(operation="POST /nope", params={})


class TestDeduplication:
    """FR-3: identical ``(operation, params)`` items collapse to one real call."""

    async def test_two_identical_items_produce_one_real_call(self) -> None:
        machine = ActionProductMachine(loggers=[])
        outcome = await _resolve([_order_item(7), _order_item(7)], machine)
        assert len(outcome.results) == 2
        assert outcome.real_call_count == 1
        assert outcome.results[0] == outcome.results[1]

    async def test_five_items_two_duplicates_three_unique(self) -> None:
        """Book example (chapter 2): positions 0 and 4 repeat the same question."""
        items = [_order_item(1), _order_item(2), _order_item(3), _order_item(4), _order_item(1)]
        machine = ActionProductMachine(loggers=[])
        outcome = await _resolve(items, machine)
        assert len(outcome.results) == 5
        assert outcome.real_call_count == 4
        assert outcome.results[0] == outcome.results[4]

    async def test_all_different_items_produce_no_savings(self) -> None:
        """No duplicates -> real_call_count equals the item count."""
        items = [_order_item(1), _order_item(2), _order_item(3)]
        machine = ActionProductMachine(loggers=[])
        outcome = await _resolve(items, machine)
        assert outcome.real_call_count == 3


class TestPerItemIsolation:
    """FR-4: an unknown operation fails only its own position, not the whole batch."""

    async def test_unknown_action_in_the_middle_is_isolated(self) -> None:
        items = [_order_item(1), _unknown_item(), _order_item(2)]
        machine = ActionProductMachine(loggers=[])
        outcome = await _resolve(items, machine)
        assert len(outcome.results) == 3
        assert outcome.results[0] == AllowedVerdict()
        assert outcome.results[1] == FailErrorVerdict("UNKNOWN_ENDPOINT")
        assert outcome.results[2] == AllowedVerdict()

    async def test_unknown_action_does_not_count_as_a_real_call(self) -> None:
        items = [_unknown_item(), _unknown_item()]
        machine = ActionProductMachine(loggers=[])
        outcome = await _resolve(items, machine)
        assert outcome.real_call_count == 0
        assert all(r == FailErrorVerdict("UNKNOWN_ENDPOINT") for r in outcome.results)

    async def test_route_level_auth_rejection_is_isolated_not_fatal(self) -> None:
        """A route whose own auth_coordinator rejected the caller (reported via
        unauthorized_operations, mirroring adapter.py catching AuthorizationError from
        EndpointExecutionPlan.prepare) fails only its own position -- FailSecurityVerdict,
        reason="UNAUTHORIZED" -- never the whole batch."""
        items = [_order_item(1), ResolveItem(operation="GET /actions/ping", params={})]
        machine = ActionProductMachine(loggers=[])
        outcome = await _resolve(items, machine, unauthorized_operations=frozenset({"GET /actions/ping"}))
        assert len(outcome.results) == 2
        assert outcome.results[0] == AllowedVerdict()
        assert outcome.results[1] == FailSecurityVerdict("UNAUTHORIZED")

    async def test_route_level_auth_rejection_does_not_count_as_a_real_call(self) -> None:
        items = [ResolveItem(operation="GET /actions/ping", params={})]
        machine = ActionProductMachine(loggers=[])
        outcome = await _resolve(items, machine, unauthorized_operations=frozenset({"GET /actions/ping"}))
        assert outcome.real_call_count == 0
