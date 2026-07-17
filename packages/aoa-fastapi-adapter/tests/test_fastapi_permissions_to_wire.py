# tests/test_fastapi_permissions_to_wire.py
"""
Tests for ``aoa.fastapi.permissions.to_wire`` — ``AccessVerdict`` -> wire ``Verdict`` (issue #130, PR 1).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Confirm the PR-1 projection is deliberately conservative: ``scope`` only ever
reports ``"role"``/``None`` — never ``"object"``, even for a real level-3
rejection — and ``entities``/``reason_code``/``expires_at`` stay at their
reserved defaults regardless of the internal verdict. Full reporting is PR 8.
"""

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.access_control import AccessVerdict
from aoa.action_machine.model.base_action import BaseAction
from aoa.fastapi.permissions import to_wire


@exclude_graph_model  # bare test stand-in, not graph-buildable — keep it out of any global subclass scan
class _ToWireTestAction(BaseAction):  # type: ignore[type-arg]
    """Stand-in action class — only its identity matters for ``AccessVerdict.action``, not real behavior."""


class TestToWire:
    """``to_wire`` — internal ``AccessVerdict`` -> wire ``Verdict`` projection."""

    def test_allowed_verdict_has_no_scope_or_level(self) -> None:
        """``allowed=True`` implies ``level=None`` on ``AccessVerdict`` -> ``scope=None`` on the wire."""
        verdict = to_wire(AccessVerdict(allowed=True, action=_ToWireTestAction))
        assert verdict.allowed is True
        assert verdict.scope is None
        assert verdict.level is None

    def test_role_level_rejection_reports_scope_role(self) -> None:
        """Level 1 (role) rejection reports ``scope: "role"``."""
        verdict = to_wire(AccessVerdict(allowed=False, action=_ToWireTestAction, level=1))
        assert verdict.allowed is False
        assert verdict.scope == "role"
        assert verdict.level == 1

    def test_guard_level_rejection_reports_scope_role(self) -> None:
        """Level 2 (guard) rejection also reports ``scope: "role"``."""
        verdict = to_wire(AccessVerdict(allowed=False, action=_ToWireTestAction, level=2))
        assert verdict.scope == "role"
        assert verdict.level == 2

    def test_object_level_rejection_still_reports_scope_role_in_this_pr(self) -> None:
        """A real level-3 (access_decide) rejection is deliberately reported as "role", not "object", until PR 8."""
        verdict = to_wire(AccessVerdict(allowed=False, action=_ToWireTestAction, level=3))
        assert verdict.scope == "role"
        assert verdict.level == 3

    def test_reason_passes_through(self) -> None:
        """Developer-facing ``reason`` text passes through unchanged."""
        verdict = to_wire(AccessVerdict(allowed=False, action=_ToWireTestAction, level=1, reason="not a manager"))
        assert verdict.reason == "not a manager"

    def test_reserved_fields_stay_unpopulated_regardless_of_input(self) -> None:
        """``reason_code``/``entities``/``expires_at`` are always at their PR-1 defaults, even on a real rejection."""
        verdict = to_wire(AccessVerdict(allowed=False, action=_ToWireTestAction, level=3, reason="not your order"))
        assert verdict.reason_code is None
        assert verdict.entities == []
        assert verdict.expires_at is None
