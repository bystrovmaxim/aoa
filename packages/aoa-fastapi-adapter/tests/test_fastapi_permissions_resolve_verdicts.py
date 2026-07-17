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
"""

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.check_access_decide_batch_size_exceeded_error import (
    CheckAccessDecideBatchSizeExceededError,
)
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.permissions import build_route_index, resolve_verdicts
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


def _order_item(order_id: int) -> ResolveItem:
    return ResolveItem(operation="POST /actions/cancel-order", params={"order_id": order_id})


def _unknown_item() -> ResolveItem:
    return ResolveItem(operation="POST /nope", params={})


class TestDeduplication:
    """FR-3: identical ``(operation, params)`` items collapse to one real call."""

    async def test_two_identical_items_produce_one_real_call(self) -> None:
        machine = ActionProductMachine(loggers=[])
        outcome = await resolve_verdicts(
            _manager_context(), [_order_item(7), _order_item(7)], _ROUTE_INDEX, machine
        )
        assert len(outcome.verdicts) == 2
        assert outcome.real_call_count == 1
        assert outcome.verdicts[0] == outcome.verdicts[1]

    async def test_five_items_two_duplicates_three_unique(self) -> None:
        """Book example (chapter 2): positions 0 and 4 repeat the same question."""
        items = [_order_item(1), _order_item(2), _order_item(3), _order_item(4), _order_item(1)]
        machine = ActionProductMachine(loggers=[])
        outcome = await resolve_verdicts(_manager_context(), items, _ROUTE_INDEX, machine)
        assert len(outcome.verdicts) == 5
        assert outcome.real_call_count == 4
        assert outcome.verdicts[0] == outcome.verdicts[4]

    async def test_all_different_items_produce_no_savings(self) -> None:
        """No duplicates -> real_call_count equals the item count."""
        items = [_order_item(1), _order_item(2), _order_item(3)]
        machine = ActionProductMachine(loggers=[])
        outcome = await resolve_verdicts(_manager_context(), items, _ROUTE_INDEX, machine)
        assert outcome.real_call_count == 3


class TestPerItemIsolation:
    """FR-4: an unknown operation fails only its own position, not the whole batch."""

    async def test_unknown_action_in_the_middle_is_isolated(self) -> None:
        items = [_order_item(1), _unknown_item(), _order_item(2)]
        machine = ActionProductMachine(loggers=[])
        outcome = await resolve_verdicts(_manager_context(), items, _ROUTE_INDEX, machine)
        assert len(outcome.verdicts) == 3
        assert outcome.verdicts[0].allowed is True
        assert outcome.verdicts[1].allowed is False
        assert outcome.verdicts[1].reason_code == "UNKNOWN_ENDPOINT"
        assert outcome.verdicts[2].allowed is True

    async def test_unknown_action_does_not_count_as_a_real_call(self) -> None:
        items = [_unknown_item(), _unknown_item()]
        machine = ActionProductMachine(loggers=[])
        outcome = await resolve_verdicts(_manager_context(), items, _ROUTE_INDEX, machine)
        assert outcome.real_call_count == 0
        assert all(v.reason_code == "UNKNOWN_ENDPOINT" for v in outcome.verdicts)


class TestBatchSizeAfterDedup:
    """The size cap is enforced against distinct keys, not raw item count."""

    async def test_distinct_keys_over_the_cap_raise(self) -> None:
        machine = ActionProductMachine(loggers=[], max_check_access_decide_batch_size=1)
        with pytest.raises(CheckAccessDecideBatchSizeExceededError):
            await resolve_verdicts(
                _manager_context(), [_order_item(1), _order_item(2)], _ROUTE_INDEX, machine
            )

    async def test_duplicates_collapsing_under_the_cap_do_not_raise(self) -> None:
        """Two raw items, but one distinct key -> does not exceed a cap of 1."""
        machine = ActionProductMachine(loggers=[], max_check_access_decide_batch_size=1)
        outcome = await resolve_verdicts(
            _manager_context(), [_order_item(7), _order_item(7)], _ROUTE_INDEX, machine
        )
        assert outcome.real_call_count == 1
