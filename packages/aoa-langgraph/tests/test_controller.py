# packages/aoa-langgraph/tests/test_controller.py
"""
Integration tests for LangGraphController in the AOA resource system.

Covers:
- LangGraphController is a BaseController (accepted by @connection / @depends)
- get_wrapper_class() returns LangGraphControllerWrapper
- @connection(LangGraphController, key=...) does not raise at class-definition time
- LangGraphControllerWrapper delegates ainvoke() to the inner controller
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from aoa.action_machine.intents.connection import connection
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.langgraph.controller import LangGraphController
from aoa.langgraph.langgraph_controller_wrapper import LangGraphControllerWrapper

# ─────────────────────────────────────────────────────────────────────────────
# TestBaseController
# ─────────────────────────────────────────────────────────────────────────────


class TestBaseController:
    def test_is_base_controller_subclass(self) -> None:
        assert issubclass(LangGraphController, BaseController)

    def test_is_base_resource_subclass(self) -> None:
        assert issubclass(LangGraphController, BaseResource)

    def test_get_wrapper_class_returns_wrapper(self) -> None:
        ctrl = LangGraphController()
        assert ctrl.get_wrapper_class() is LangGraphControllerWrapper

    async def test_check_rollup_support_returns_false(self) -> None:
        ctrl = LangGraphController()
        assert await ctrl.check_rollup_support() is False


# ─────────────────────────────────────────────────────────────────────────────
# TestConnectionDecorator
# ─────────────────────────────────────────────────────────────────────────────


class TestConnectionDecorator:
    def test_connection_decorator_accepts_controller_type(self) -> None:
        # @connection(LangGraphController, key='graph') must not raise at class-definition time
        @connection(LangGraphController, key="graph", description="LangGraph runner")
        class _StubConsumer:
            pass

        assert _StubConsumer is not None

    def test_wrapper_is_base_controller_subclass(self) -> None:
        assert issubclass(LangGraphControllerWrapper, BaseController)

    def test_wrapper_get_wrapper_class_returns_self(self) -> None:
        inner = MagicMock(spec=LangGraphController)
        wrapper = LangGraphControllerWrapper(inner)
        assert wrapper.get_wrapper_class() is LangGraphControllerWrapper


# ─────────────────────────────────────────────────────────────────────────────
# TestWrapperDelegation
# ─────────────────────────────────────────────────────────────────────────────


class TestWrapperDelegation:
    async def test_ainvoke_delegates_to_inner(self) -> None:
        inner = MagicMock(spec=LangGraphController)
        inner.ainvoke = AsyncMock(return_value={"message": "pong"})
        wrapper = LangGraphControllerWrapper(inner)
        box = MagicMock()

        result = await wrapper.ainvoke({"x": 1}, box)

        inner.ainvoke.assert_awaited_once_with({"x": 1}, box)
        assert result == {"message": "pong"}

    async def test_check_rollup_support_delegates_to_inner(self) -> None:
        inner = MagicMock(spec=LangGraphController)
        inner.check_rollup_support = AsyncMock(return_value=False)
        wrapper = LangGraphControllerWrapper(inner)

        result = await wrapper.check_rollup_support()
        assert result is False
