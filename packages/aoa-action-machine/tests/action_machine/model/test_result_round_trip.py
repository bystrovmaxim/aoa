# packages/aoa-action-machine/tests/action_machine/model/test_result_round_trip.py
"""
What goes out comes back in: a Result read back from its JSON has the same observable state.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Case 8.2 of issue #409, on AOA's own value types: relations loaded, not loaded and
loaded with zero rows; a partial target; a dictionary value as a relation and as a
bare field; a lifecycle; a projection; a list of entities.
"""

from __future__ import annotations

import pytest

from aoa.action_machine.domain import observable_difference
from tests.support.round_trip_model import RtLineCoreEntity, RtOrderResult, result


def _read_back(value: RtOrderResult) -> RtOrderResult:
    return RtOrderResult.model_validate_json(value.model_dump_json())


@pytest.mark.parametrize(
    "value",
    [
        result(),
        result(lines=(RtLineCoreEntity(id="l1", quantity=2), RtLineCoreEntity(id="l2", quantity=1))),
        result(customer_loaded=False, lines=None),
        result(status="draft"),
    ],
    ids=["zero-lines-loaded", "two-lines-loaded", "nothing-loaded", "draft"],
)
def test_a_result_reads_back_with_the_same_observable_state(value: RtOrderResult) -> None:
    """Every value type keeps its observable state through its own JSON."""
    assert observable_difference(value, _read_back(value)) is None


def test_the_read_back_keeps_what_equality_cannot_see() -> None:
    """Zero loaded lines stay loaded, the never-loaded stay not loaded, declared objects stay the declared ones."""
    back = _read_back(result())
    assert back.order.lines.is_loaded is True
    assert back.history[0].lines.is_loaded is False
    assert back.order.lifecycle.current_status is result().order.lifecycle.current_status
    assert back.settlement is result().settlement
