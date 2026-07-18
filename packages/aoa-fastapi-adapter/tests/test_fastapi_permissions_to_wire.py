# tests/test_fastapi_permissions_to_wire.py
"""
Tests for ``aoa.fastapi.permissions.to_wire`` — ``AccessVerdict`` -> wire ``ResolveItemResult`` (issue #130).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Confirm the projection is a straight copy: both ``AccessVerdict`` and
``ResolveItemResult`` are the same flat ``{kind, reason}`` pair now, one layer
apart, so ``to_wire`` has nothing left to recompute — every ``ResolveItemKind``
that can actually appear on an ``AccessVerdict`` round-trips unchanged, ``reason``
included verbatim.
"""

import pytest

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.access_control import AccessVerdict, ResolveItemKind
from aoa.action_machine.model.base_action import BaseAction
from aoa.fastapi.permissions import to_wire


@exclude_graph_model  # bare test stand-in, not graph-buildable — keep it out of any global subclass scan
class _ToWireTestAction(BaseAction):  # type: ignore[type-arg]
    """Stand-in action class — only its identity matters for ``AccessVerdict.action``, not real behavior."""


class TestToWire:
    """``to_wire`` — internal ``AccessVerdict`` -> wire ``ResolveItemResult``, a straight copy."""

    def test_success_round_trips_with_empty_reason(self) -> None:
        result = to_wire(AccessVerdict(action=_ToWireTestAction, kind=ResolveItemKind.SUCCESS, reason=""))
        assert result.kind == ResolveItemKind.SUCCESS
        assert result.reason == ""

    @pytest.mark.parametrize("kind", [ResolveItemKind.SECURITY, ResolveItemKind.FLAG, ResolveItemKind.MACHINE_RULE])
    def test_denial_channels_round_trip_kind_and_reason(self, kind: ResolveItemKind) -> None:
        """``to_wire()`` itself is a generic straight copy over the whole enum — this is a
        unit test of that copy, not a claim that FLAG/MACHINE_RULE are reachable today: no
        production code constructs an AccessVerdict with either (grep confirms this); both
        are reserved for future business-rule work (feature flags, budgets, a circuit
        breaker) that chapter 3.5 defers."""
        result = to_wire(AccessVerdict(action=_ToWireTestAction, kind=kind, reason="not a manager"))
        assert result.kind == kind
        assert result.reason == "not a manager"

    def test_reason_passes_through_verbatim(self) -> None:
        """No recomputation: whatever ``AccessVerdict.reason`` holds is exactly what the wire gets."""
        result = to_wire(
            AccessVerdict(action=_ToWireTestAction, kind=ResolveItemKind.SECURITY, reason="RuntimeError")
        )
        assert result.reason == "RuntimeError"
