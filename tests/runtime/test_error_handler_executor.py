# tests/runtime/test_error_handler_executor.py
"""Focused tests for ``ErrorHandlerExecutor`` (handler resolution + plugin emits)."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.context.context import Context
from action_machine.context.ctx_constants import Ctx
from action_machine.context.user_info import UserInfo
from action_machine.exceptions import OnErrorHandlerError
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.context_requires.context_requires_decorator import context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error import on_error
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.model.base_action import BaseAction
from action_machine.model.base_state import BaseState
from action_machine.plugin.events import (
    AfterOnErrorAspectEvent,
    BeforeOnErrorAspectEvent,
    UnhandledErrorEvent,
)
from action_machine.plugin.plugin_emit_support import PluginEmitSupport
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.error_handler_executor import ErrorHandlerExecutor
from action_machine.runtime.tools_box import ToolsBox
from action_machine.system_core import TypeIntrospection
from graph.create_node_graph_coordinator import create_node_graph_coordinator
from tests.scenarios.domain_model.domains import OrdersDomain
from tests.scenarios.domain_model.error_actions import (
    ErrorHandledAction,
    ErrorTestParams,
    ErrorTestResult,
    HandlerRaisesAction,
)


def _wired_action(cls: type) -> ActionGraphNode:
    coordinator = create_node_graph_coordinator()
    node_id = TypeIntrospection.full_qualname(cls)
    raw = coordinator.get_node_by_id(node_id, ActionGraphNode.NODE_TYPE)
    return raw  # type: ignore[return-value]


@meta(description="Probe @context_requires wiring in ErrorHandlerExecutor", domain=OrdersDomain)
@check_roles(NoneRole)
class _CtxOnErrorProbeAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """Minimal Action whose ``@on_error`` handler pulls ``Ctx.User.user_id`` via ``ContextView``."""

    @regular_aspect("noop probe aspect")
    @result_string("processed", required=True)
    async def noop_probe_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict[str, str]:
        return {"processed": "ok"}

    @summary_aspect("stub summary")
    async def noop_probe_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail="")

    @on_error(RuntimeError, description="handler with ContextView")
    @context_requires(Ctx.User.user_id)
    async def runtime_probe_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        error: Exception,
        ctx,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="handled", detail=str(ctx.get(Ctx.User.user_id)))


@pytest.fixture
def plugin_emit() -> PluginEmitSupport:
    return PluginEmitSupport(LogCoordinator(loggers=[]))


def _minimal_box() -> MagicMock:
    box = MagicMock()
    box.nested_level = 0
    return box


@pytest.mark.asyncio
async def test_handle_unhandled_emits_and_reraises(plugin_emit: PluginEmitSupport) -> None:
    importlib.import_module("tests.scenarios.domain_model.error_actions")
    exe = ErrorHandlerExecutor(plugin_emit)
    plugin_ctx = AsyncMock()
    err = KeyError("missing")

    with pytest.raises(KeyError, match="missing"):
        await exe.handle(
            error=err,
            action=ErrorHandledAction(),
            params=ErrorTestParams(value="v", should_fail=True),
            state=BaseState(),
            box=_minimal_box(),
            connections={},
            context=Context(),
            error_handler_nodes=[],
            plugin_ctx=plugin_ctx,
            failed_aspect_name="aspect_x",
        )

    emitted = plugin_ctx.emit_event.call_args.args[0]
    assert isinstance(emitted, UnhandledErrorEvent)


@pytest.mark.asyncio
async def test_handle_invokes_matching_handler(plugin_emit: PluginEmitSupport) -> None:
    importlib.import_module("tests.scenarios.domain_model.error_actions")
    action_node = _wired_action(ErrorHandledAction)
    exe = ErrorHandlerExecutor(plugin_emit)
    plugin_ctx = AsyncMock()

    bound = await exe.handle(
        error=ValueError("boom"),
        action=ErrorHandledAction(),
        params=ErrorTestParams(value="v", should_fail=True),
        state=BaseState(),
        box=_minimal_box(),
        connections={},
        context=Context(),
        error_handler_nodes=action_node.get_error_handler_graph_nodes(),
        plugin_ctx=plugin_ctx,
        failed_aspect_name="process_aspect",
    )

    assert bound.status == "handled"
    events = [c.args[0] for c in plugin_ctx.emit_event.call_args_list]
    assert any(isinstance(e, BeforeOnErrorAspectEvent) for e in events)
    assert any(isinstance(e, AfterOnErrorAspectEvent) for e in events)


@pytest.mark.asyncio
async def test_handle_wraps_handler_exception(plugin_emit: PluginEmitSupport) -> None:
    importlib.import_module("tests.scenarios.domain_model.error_actions")
    action_node = _wired_action(HandlerRaisesAction)
    exe = ErrorHandlerExecutor(plugin_emit)
    plugin_ctx = AsyncMock()

    orig = ValueError("aspect failed")
    with pytest.raises(OnErrorHandlerError, match="handler") as ei:
        await exe.handle(
            error=orig,
            action=HandlerRaisesAction(),
            params=ErrorTestParams(value="v", should_fail=True),
            state=BaseState(),
            box=_minimal_box(),
            connections={},
            context=Context(),
            error_handler_nodes=action_node.get_error_handler_graph_nodes(),
            plugin_ctx=plugin_ctx,
            failed_aspect_name="process_aspect",
        )

    assert ei.value.original_error is orig


@pytest.mark.asyncio
async def test_handle_passes_context_view_when_required(plugin_emit: PluginEmitSupport) -> None:
    action_node = _wired_action(_CtxOnErrorProbeAction)
    handler = next(h for h in action_node.get_error_handler_graph_nodes() if h.label == "runtime_probe_on_error")
    exe = ErrorHandlerExecutor(plugin_emit)
    plugin_ctx = AsyncMock()
    ctx = Context(user=UserInfo(user_id="uid-42", roles=()))

    bound = await exe.handle(
        error=RuntimeError("r"),
        action=_CtxOnErrorProbeAction(),
        params=ErrorTestParams(value="x", should_fail=False),
        state=BaseState(),
        box=_minimal_box(),
        connections={},
        context=ctx,
        error_handler_nodes=[handler],
        plugin_ctx=plugin_ctx,
        failed_aspect_name=None,
    )

    assert bound.detail == "uid-42"
    assert bound.status == "handled"
