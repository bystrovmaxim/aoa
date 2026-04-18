# tests/graph_contract/test_reliability.py

"""
Extra contract checks: vertex-id parsing helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Catch regressions on interchange vertex-id string conventions.
"""

from __future__ import annotations

import pytest

from action_machine.graph import split_checker_vertex_id, split_host_element_vertex_id


def test_split_checker_nested_qualname_before_colon() -> None:
    host, method, field = split_checker_vertex_id(
        "myapp.pkg.actions.CreateOrderAction.validate_aspect:amount_cents",
    )
    assert host == "myapp.pkg.actions.CreateOrderAction"
    assert method == "validate_aspect"
    assert field == "amount_cents"


def test_split_host_element_nested_qualname() -> None:
    host, element = split_host_element_vertex_id("myapp.pkg.actions.CreateOrderAction.summary_aspect")
    assert host == "myapp.pkg.actions.CreateOrderAction"
    assert element == "summary_aspect"


@pytest.mark.parametrize("bad", ["nodots", "", "only.dots."])
def test_split_host_element_rejects_missing_or_empty_parts(bad: str) -> None:
    with pytest.raises(ValueError):
        split_host_element_vertex_id(bad)
