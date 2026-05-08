# tests/runtime/test_action_product_machine_pipeline.py
"""Focused ``ActionProductMachine`` pipeline error-path tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.model.base_state import BaseState
from action_machine.runtime.action_product_machine import ActionProductMachine


def _aspect(label: str) -> SimpleNamespace:
    return SimpleNamespace(label=label)


def _compensator(label: str) -> SimpleNamespace:
    return SimpleNamespace(label=label)


def _machine_with_mocks() -> ActionProductMachine:
    machine = ActionProductMachine(
        graph_coordinator=MagicMock(),
        role_checker=MagicMock(),
        connection_validator=MagicMock(),
        aspect_executor=MagicMock(),
        error_handler_executor=MagicMock(),
        saga_coordinator=MagicMock(),
    )
    machine._plugin_coordinator = AsyncMock()  # type: ignore[method-assign]
    machine._plugin_coordinator.emit_before_regular_aspect = AsyncMock()
    machine._plugin_coordinator.emit_after_regular_aspect = AsyncMock()
    machine._plugin_coordinator.emit_before_summary_aspect = AsyncMock()
    machine._plugin_coordinator.emit_after_summary_aspect = AsyncMock()
    machine._saga_coordinator.execute = AsyncMock()
    machine._error_handler_executor.handle = AsyncMock(return_value="handled")
    return machine


async def _run_pipeline(
    machine: ActionProductMachine,
    action_graph_node: MagicMock,
) -> object:
    return await machine._execute_pipeline_aspects(  # pylint: disable=protected-access
        action=MagicMock(),
        params=MagicMock(),
        box=SimpleNamespace(nested_level=1),
        connections={},
        context=MagicMock(),
        plugin_ctx=AsyncMock(),
        action_graph_node=action_graph_node,
    )


@pytest.mark.asyncio
async def test_failed_first_aspect_rolls_back_frame_with_no_state_after() -> None:
    machine = _machine_with_mocks()
    first = _aspect("first")
    first_comp = _compensator("undo_first")
    action_graph_node = MagicMock()
    action_graph_node.get_regular_aspect_graph_nodes.return_value = [first]
    action_graph_node.compensator_graph_node_for_aspect.return_value = first_comp
    machine._aspect_executor.execute_regular = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

    result = await _run_pipeline(machine, action_graph_node)

    assert result == "handled"
    saga_stack = machine._saga_coordinator.execute.call_args.kwargs["saga_stack"]
    assert len(saga_stack) == 1
    assert saga_stack[0].compensator is first_comp
    assert saga_stack[0].state_after is None


@pytest.mark.asyncio
async def test_failed_aspect_without_compensator_runs_empty_rollback_stack() -> None:
    machine = _machine_with_mocks()
    aspect = _aspect("no_compensator")
    action_graph_node = MagicMock()
    action_graph_node.get_regular_aspect_graph_nodes.return_value = [aspect]
    action_graph_node.compensator_graph_node_for_aspect.return_value = None
    machine._aspect_executor.execute_regular = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

    await _run_pipeline(machine, action_graph_node)

    saga_stack = machine._saga_coordinator.execute.call_args.kwargs["saga_stack"]
    assert saga_stack == []


@pytest.mark.asyncio
async def test_failed_second_aspect_keeps_successful_and_pending_saga_frames() -> None:
    machine = _machine_with_mocks()
    first = _aspect("first")
    second = _aspect("second")
    first_comp = _compensator("undo_first")
    second_comp = _compensator("undo_second")
    action_graph_node = MagicMock()
    action_graph_node.get_regular_aspect_graph_nodes.return_value = [first, second]
    action_graph_node.compensator_graph_node_for_aspect.side_effect = [first_comp, second_comp]
    state_after_first = BaseState(done=True)
    machine._aspect_executor.execute_regular = AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            (state_after_first, {"done": True}, 0.01),
            RuntimeError("second failed"),
        ]
    )

    await _run_pipeline(machine, action_graph_node)

    saga_stack = machine._saga_coordinator.execute.call_args.kwargs["saga_stack"]
    assert [(frame.aspect_name, frame.compensator) for frame in saga_stack] == [
        ("first", first_comp),
        ("second", second_comp),
    ]
    assert saga_stack[0].state_after is state_after_first
    assert saga_stack[1].state_after is None


@pytest.mark.asyncio
async def test_summary_failure_rolls_back_completed_regular_aspects() -> None:
    machine = _machine_with_mocks()
    aspect = _aspect("regular")
    comp = _compensator("undo_regular")
    summary = _aspect("summary")
    action_graph_node = MagicMock()
    action_graph_node.get_regular_aspect_graph_nodes.return_value = [aspect]
    action_graph_node.compensator_graph_node_for_aspect.return_value = comp
    action_graph_node.get_summary_aspect_graph_node.return_value = summary
    state_after = BaseState(processed=True)
    machine._aspect_executor.execute_regular = AsyncMock(  # type: ignore[method-assign]
        return_value=(state_after, {"processed": True}, 0.01)
    )
    machine._aspect_executor.execute_summary = AsyncMock(side_effect=RuntimeError("summary failed"))  # type: ignore[method-assign]

    await _run_pipeline(machine, action_graph_node)

    saga_stack = machine._saga_coordinator.execute.call_args.kwargs["saga_stack"]
    assert len(saga_stack) == 1
    assert saga_stack[0].state_after is state_after
    assert machine._error_handler_executor.handle.call_args.kwargs["failed_aspect_name"] == "summary"
