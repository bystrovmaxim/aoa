# tests/runtime/test_action_product_machine_debug_graph_guard.py
"""Runtime guard for debug graph coordinators with forbidden DAG-cycle diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from action_machine.runtime.action_product_machine import ActionProductMachine
from graph.debug_node_graph_coordinator import DagCycleViolation, DebugNodeGraphCoordinator
from graph.exceptions import InvalidGraphError
from tests.scenarios.domain_model import PingAction


def _params() -> PingAction.Params:
    return PingAction.Params()


@pytest.mark.asyncio
async def test_action_product_machine_rejects_debug_graph_with_dag_cycle_violations() -> None:
    """A debug-built graph with forbidden DAG cycles must not execute any action."""
    debug = DebugNodeGraphCoordinator()
    object.__setattr__(
        debug,
        "_dag_cycle_violations",
        (DagCycleViolation("a", "b", "dag"),),
    )
    machine = ActionProductMachine(graph_coordinator=debug)

    with (
        patch.object(machine, "get_action_node_by_id") as get_action_node_by_id,
        pytest.raises(InvalidGraphError, match="action execution is disabled"),
    ):
        await machine._run_internal(
            context=MagicMock(),
            action=PingAction(),
            params=_params(),
            resources=None,
            connections=None,
            nested_level=0,
            rollup=False,
        )

    get_action_node_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_action_product_machine_allows_debug_graph_without_dag_cycle_violations() -> None:
    """An empty debug-diagnostics set should not block normal runtime flow."""
    machine = ActionProductMachine(graph_coordinator=DebugNodeGraphCoordinator())
    with (
        patch.object(machine, "get_action_node_by_id", side_effect=RuntimeError("past guard")),
        pytest.raises(RuntimeError, match="past guard"),
    ):
        await machine._run_internal(
            context=MagicMock(),
            action=PingAction(),
            params=_params(),
            resources=None,
            connections=None,
            nested_level=0,
            rollup=False,
        )
