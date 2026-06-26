# packages/aoa-langgraph/tests/test_integration.py
"""
Integration tests for LangGraphController.compile() and .ainvoke().

Requires langgraph — skipped automatically if not installed.

Covers:
- compile(box) returns a CompiledStateGraph with ainvoke/astream/get_graph
- ainvoke(data, box) executes the graph and returns output fields
- per-finish out-field mode: __finish_node__ tracking
- RouteKeyError propagated during ainvoke
- UnexpectedResultFieldError raised at build() for undeclared Result fields
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("langgraph", reason="langgraph not installed")

from aoa.langgraph.controller import LangGraphController
from aoa.langgraph.exceptions import MissingInputFieldError, RouteKeyError, UnexpectedResultFieldError

from .support import FullAction, PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _mock_box(result_fields: dict[str, Any]) -> Any:
    """Return a mock ToolsBox whose .run() returns a MagicMock with model_dump()."""
    mock_result = MagicMock()
    mock_result.model_dump.return_value = result_fields
    box = MagicMock()
    box.run = AsyncMock(return_value=mock_result)
    return box


def _ping_ctrl() -> LangGraphController:
    """Minimal built controller that runs PingAction and outputs 'message'."""
    return (
        LangGraphController()
        .mid("message", str, "Ping response message")
        .out("message")
        .node(PingAction)
        .start(PingAction)
        .finish(PingAction)
        .build()
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestCompile
# ─────────────────────────────────────────────────────────────────────────────


class TestCompile:
    def test_returns_compiled_graph_with_ainvoke(self) -> None:
        ctrl = _ping_ctrl()
        compiled = ctrl.compile(MagicMock())
        assert hasattr(compiled, "ainvoke")

    def test_returns_compiled_graph_with_astream(self) -> None:
        ctrl = _ping_ctrl()
        compiled = ctrl.compile(MagicMock())
        assert hasattr(compiled, "astream")

    def test_returns_compiled_graph_with_get_graph(self) -> None:
        ctrl = _ping_ctrl()
        compiled = ctrl.compile(MagicMock())
        assert hasattr(compiled, "get_graph")

    def test_compile_does_not_store_box_on_controller(self) -> None:
        ctrl = _ping_ctrl()
        ctrl.compile(MagicMock())
        assert not hasattr(ctrl, "_box")
        assert not hasattr(ctrl, "_compiled")

    def test_two_compile_calls_return_independent_graphs(self) -> None:
        ctrl = _ping_ctrl()
        box1 = MagicMock()
        box2 = MagicMock()
        g1 = ctrl.compile(box1)
        g2 = ctrl.compile(box2)
        assert g1 is not g2


# ─────────────────────────────────────────────────────────────────────────────
# TestAinvoke
# ─────────────────────────────────────────────────────────────────────────────


class TestAinvoke:
    async def test_basic_ainvoke_returns_output_fields(self) -> None:
        ctrl = _ping_ctrl()
        box = _mock_box({"message": "pong"})
        result = await ctrl.ainvoke({}, box)
        assert result == {"message": "pong"}

    async def test_ainvoke_passes_inp_fields_to_initial_state(self) -> None:
        ctrl = (
            LangGraphController()
            .inp("query", str, "Input query")
            .mid("message", str, "Response")
            .out("message")
            .node(PingAction)
            .start(PingAction)
            .finish(PingAction)
            .build()
        )
        box = _mock_box({"message": "ok"})
        result = await ctrl.ainvoke({"query": "hello"}, box)
        assert result == {"message": "ok"}

    async def test_ainvoke_per_finish_mode(self) -> None:
        ctrl = (
            LangGraphController()
            .mid("message", str, "Ping response message")
            .node(PingAction)
            .start(PingAction)
            .finish(PingAction)
            .out("message")  # per-finish: PingAction.outs = ["message"]
            .build()
        )
        box = _mock_box({"message": "pong"})
        result = await ctrl.ainvoke({}, box)
        assert result == {"message": "pong"}

    async def test_ainvoke_multi_node_chain(self) -> None:
        # FullAction.Params requires user_id and amount — declare as inp-fields
        ctrl = (
            LangGraphController()
            .inp("user_id", str, "User id")
            .inp("amount", float, "Amount")
            .mid("order_id", str, "Order id")
            .mid("txn_id", str, "Txn id")
            .mid("total", float, "Total")
            .mid("status", str, "Status")
            .out("order_id")
            .node(FullAction)
            .start(FullAction)
            .finish(FullAction)
            .build()
        )
        box = _mock_box({
            "order_id": "ORD-u1",
            "txn_id": "TXN-1",
            "total": 100.0,
            "status": "created",
        })
        result = await ctrl.ainvoke({"user_id": "u1", "amount": 100.0}, box)
        assert result["order_id"] == "ORD-u1"

    async def test_ainvoke_missing_inp_field_raises(self) -> None:
        ctrl = (
            LangGraphController()
            .inp("user_id", str, "Required user id")
            .mid("message", str, "Response")
            .out("message")
            .node(PingAction)
            .start(PingAction)
            .finish(PingAction)
            .build()
        )
        box = _mock_box({"message": "pong"})
        with pytest.raises(MissingInputFieldError):
            await ctrl.ainvoke({}, box)  # user_id missing

    async def test_ainvoke_with_response_mapper(self) -> None:
        ctrl = (
            LangGraphController()
            .mid("out_field", str, "output")
            .out("out_field")
            .node(PingAction, response_mapper=lambda r: {"out_field": r.message})
            .start(PingAction)
            .finish(PingAction)
            .build()
        )
        mock_result = MagicMock()
        mock_result.message = "hello"
        box = MagicMock()
        box.run = AsyncMock(return_value=mock_result)
        result = await ctrl.ainvoke({}, box)
        assert result == {"out_field": "hello"}


# ─────────────────────────────────────────────────────────────────────────────
# TestRouteKeyError
# ─────────────────────────────────────────────────────────────────────────────


class _SetUnknownCategory:
    """Async function node that writes an unregistered route key."""


async def _set_unknown_category(state: Any) -> dict:
    return {"category": "NOPE"}


async def _set_known_category(state: Any) -> dict:
    return {"category": "bug"}


async def _handle_bug(state: Any) -> dict:
    return {}


class TestRouteKeyError:
    async def test_unknown_key_raises(self) -> None:
        ctrl = (
            LangGraphController()
            .mid("category", str, "route category")
            .mid("message", str, "response")
            .out("message")
            .node(_set_unknown_category, name="source")
            .node(PingAction)
            .route("source", on=lambda s: s.category, paths={"bug": PingAction})
            .start("source")
            .finish(PingAction)
            .build()
        )
        with pytest.raises(RouteKeyError):
            await ctrl.ainvoke({}, _mock_box({"message": "pong"}))

    async def test_error_message_includes_key_and_paths(self) -> None:
        ctrl = (
            LangGraphController()
            .mid("category", str, "route category")
            .mid("message", str, "response")
            .out("message")
            .node(_set_unknown_category, name="source")
            .node(PingAction)
            .route("source", on=lambda s: s.category, paths={"bug": PingAction})
            .start("source")
            .finish(PingAction)
            .build()
        )
        with pytest.raises(RouteKeyError, match="NOPE") as exc_info:
            await ctrl.ainvoke({}, _mock_box({"message": "pong"}))
        assert "bug" in str(exc_info.value)

    async def test_known_key_does_not_raise(self) -> None:
        # Use PingAction as the route target — it writes "message" (satisfies rule #15)
        ctrl = (
            LangGraphController()
            .mid("category", str, "route category")
            .mid("message", str, "response")
            .out("message")
            .node(_set_known_category, name="source")
            .node(PingAction)
            .route("source", on=lambda s: s.category, paths={"bug": PingAction})
            .start("source")
            .finish(PingAction)
            .build()
        )
        result = await ctrl.ainvoke({}, _mock_box({"message": "pong"}))
        assert result == {"message": "pong"}


# ─────────────────────────────────────────────────────────────────────────────
# TestUnexpectedResultField
# ─────────────────────────────────────────────────────────────────────────────


class TestUnexpectedResultField:
    def test_undeclared_result_field_raises_at_build(self) -> None:
        # Declare "other" in mid (to bypass NoOutputFieldsError), but NOT "message".
        # PingAction.Result.message not in inp/mid → UnexpectedResultFieldError.
        ctrl = (
            LangGraphController()
            .mid("other", str, "unrelated field")
            .out("other")
            .node(PingAction)
            .start(PingAction)
            .finish(PingAction)
        )
        with pytest.raises(UnexpectedResultFieldError) as exc_info:
            ctrl.build()
        assert "message" in exc_info.value.unexpected

    def test_no_error_when_result_fields_declared(self) -> None:
        _ping_ctrl()  # no exception

    def test_no_error_with_response_mapper(self) -> None:
        # response_mapper suppresses rule #13 for that node
        ctrl = (
            LangGraphController()
            .mid("out_field", str, "output")
            .out("out_field")
            .node(PingAction, response_mapper=lambda r: {"out_field": r.message})
            .start(PingAction)
            .finish(PingAction)
            .build()
        )
        assert ctrl._built is True
