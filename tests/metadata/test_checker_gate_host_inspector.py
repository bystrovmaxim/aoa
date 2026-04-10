# tests/metadata/test_checker_gate_host_inspector.py
"""Unit tests for CheckerGateHostInspector."""

from __future__ import annotations

from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.checkers.checker_gate_host_inspector import CheckerGateHostInspector
from action_machine.checkers.result_string_checker import result_string


class _NoCheckerAction(CheckerGateHost):
    pass


class _CheckerAction(CheckerGateHost):
    @result_string("name", required=True, min_length=2)
    async def validate_name_aspect(self, params, state, box, connections):
        return {"name": "ok"}


def test_checker_inspector_returns_none_without_checkers() -> None:
    assert CheckerGateHostInspector.inspect(_NoCheckerAction) is None


def test_checker_inspector_builds_payload_with_checker_entries() -> None:
    payload = CheckerGateHostInspector.inspect(_CheckerAction)
    assert payload is not None
    assert payload.node_type == "checker"

    data = dict(payload.node_meta)
    checkers = data["checkers"]
    assert len(checkers) == 1

    method_name, checker_class, field_name, required, extra = checkers[0]
    assert method_name == "validate_name_aspect"
    assert checker_class is not None
    assert field_name == "name"
    assert required is True
    assert ("min_length", 2) in extra
