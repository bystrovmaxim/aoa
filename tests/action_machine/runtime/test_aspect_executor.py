# tests/runtime/test_aspect_executor.py
"""Focused tests for ``AspectExecutor`` checker-validation branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from aoa.action_machine.exceptions.missing_summary_aspect_error import MissingSummaryAspectError
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.runtime.aspect_executor import AspectExecutor
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.graph.exclude_graph_model import exclude_graph_model


class _RejectingChecker:
    def __init__(self, field_name: str, *, required: bool = True) -> None:
        self.field_name = field_name
        self.required = required

    def check(self, result: dict[str, object]) -> None:
        raise ValidationFieldError(f"Rejected {self.field_name}", self.field_name)


def _checker_node(field_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        label=field_name,
        node_obj=SimpleNamespace(
            checker_class=_RejectingChecker,
            field_name=field_name,
            required=True,
            properties={},
        ),
    )


class _Params(BaseParams):
    pass


class _Result(BaseResult):
    value: str = "ok"


@exclude_graph_model
class _ExecutorProbeAction(BaseAction[_Params, _Result]):
    pass


def _box() -> SimpleNamespace:
    return SimpleNamespace(
        run_child=AsyncMock(),
        factory=MagicMock(),
        resources={},
        nested_level=0,
        rollup=False,
    )


@pytest.mark.asyncio
async def test_call_aspect_wraps_tools_box_and_context_view() -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))
    aspect_node = MagicMock()
    aspect_node.label = "context_aspect"
    aspect_node.get_required_context_keys.return_value = frozenset({"user.id"})
    aspect_node.node_obj = AsyncMock(return_value={"ok": True})

    result = await executor.call_aspect(
        action=_ExecutorProbeAction(),
        aspect_node=aspect_node,
        params=_Params(),
        state=BaseState(),
        box=_box(),
        connections={},
        context=SimpleNamespace(resolve=lambda key: f"value:{key}"),
    )

    assert result == {"ok": True}
    called_args = aspect_node.node_obj.await_args.args
    assert isinstance(called_args[3], ToolsBox)
    assert called_args[5].allowed_keys == frozenset({"user.id"})


@pytest.mark.asyncio
async def test_execute_regular_raises_when_checker_rejects_result() -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))
    executor.call_aspect = AsyncMock(return_value={"processed": "bad"})  # type: ignore[method-assign]
    aspect_node = MagicMock()
    aspect_node.label = "validate_aspect"
    aspect_node.get_checker_graph_nodes.return_value = [_checker_node("processed")]

    with pytest.raises(ValidationFieldError, match="Rejected processed"):
        await executor.execute_regular(
            action=MagicMock(),
            aspect_node=aspect_node,
            params=MagicMock(),
            state=BaseState(),
            box=MagicMock(),
            connections={},
            context=MagicMock(),
        )


@pytest.mark.asyncio
async def test_execute_regular_raises_when_state_patch_has_no_checkers() -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))
    executor.call_aspect = AsyncMock(return_value={"processed": "unchecked"})  # type: ignore[method-assign]
    aspect_node = MagicMock()
    aspect_node.label = "unchecked_aspect"
    aspect_node.get_checker_graph_nodes.return_value = []

    with pytest.raises(ValidationFieldError, match="has no checkers"):
        await executor.execute_regular(
            action=MagicMock(),
            aspect_node=aspect_node,
            params=MagicMock(),
            state=BaseState(),
            box=MagicMock(),
            connections={},
            context=MagicMock(),
        )


@pytest.mark.asyncio
async def test_execute_regular_rejects_non_dict_aspect_result() -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))
    executor.call_aspect = AsyncMock(return_value=["not", "a", "dict"])  # type: ignore[method-assign]
    aspect_node = MagicMock()
    aspect_node.label = "bad_result_aspect"

    with pytest.raises(TypeError, match="must return a dict"):
        await executor.execute_regular(
            action=MagicMock(),
            aspect_node=aspect_node,
            params=MagicMock(),
            state=BaseState(),
            box=MagicMock(),
            connections={},
            context=MagicMock(),
        )


@pytest.mark.asyncio
async def test_execute_regular_rejects_extra_fields_not_backed_by_checkers() -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))
    executor.call_aspect = AsyncMock(return_value={"allowed": "ok", "extra": "no"})  # type: ignore[method-assign]
    aspect_node = MagicMock()
    aspect_node.label = "extra_field_aspect"
    allowed_checker = _checker_node("allowed")
    allowed_checker.node_obj.checker_class = lambda field_name, required=True: SimpleNamespace(check=lambda result: None)
    aspect_node.get_checker_graph_nodes.return_value = [allowed_checker]

    with pytest.raises(ValidationFieldError, match="returned extra fields"):
        await executor.execute_regular(
            action=MagicMock(),
            aspect_node=aspect_node,
            params=MagicMock(),
            state=BaseState(),
            box=MagicMock(),
            connections={},
            context=MagicMock(),
        )


@pytest.mark.asyncio
async def test_execute_regular_merges_state_when_checkers_accept() -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))
    executor.call_aspect = AsyncMock(return_value={"allowed": "ok"})  # type: ignore[method-assign]
    aspect_node = MagicMock()
    aspect_node.label = "valid_aspect"
    checker = _checker_node("allowed")
    checker.node_obj.checker_class = lambda field_name, required=True: SimpleNamespace(check=lambda result: None)
    aspect_node.get_checker_graph_nodes.return_value = [checker]

    merged, patch, duration = await executor.execute_regular(
        action=MagicMock(),
        aspect_node=aspect_node,
        params=MagicMock(),
        state=BaseState(existing="yes"),
        box=MagicMock(),
        connections={},
        context=MagicMock(),
    )

    assert merged.to_dict() == {"existing": "yes", "allowed": "ok"}
    assert patch == {"allowed": "ok"}
    assert duration >= 0


@pytest.mark.asyncio
async def test_execute_summary_requires_summary_node() -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))

    with pytest.raises(MissingSummaryAspectError):
        await executor.execute_summary(
            summary_node=None,
            action=_ExecutorProbeAction(),
            params=_Params(),
            state=BaseState(),
            box=MagicMock(),
            connections={},
            context=MagicMock(),
        )


@pytest.mark.asyncio
async def test_execute_summary_returns_result_and_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = AspectExecutor(LogCoordinator(loggers=[]))
    expected = _Result(value="done")
    executor.call_aspect = AsyncMock(return_value=expected)  # type: ignore[method-assign]
    monkeypatch.setattr(
        "aoa.action_machine.runtime.aspect_executor.ActionSchemaIntentResolver.resolve_result_type",
        lambda action_cls: _Result,
    )

    result, duration = await executor.execute_summary(
        summary_node=MagicMock(),
        action=_ExecutorProbeAction(),
        params=_Params(),
        state=BaseState(),
        box=MagicMock(),
        connections={},
        context=MagicMock(),
    )

    assert result is expected
    assert duration >= 0
