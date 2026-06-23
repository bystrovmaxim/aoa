# tests/langgraph/test_integration.py
"""
Integration tests for LangGraphAdapter.build_graph() and .compile().

Requires langgraph — skipped automatically if not installed.

Covers:
- build_graph() returns a StateGraph
- compile() returns a compiled graph with ainvoke/astream/get_graph
- MissingConnectionError is raised at build_graph() time (before StateGraph is returned)
- build_graph() result can be extended and compiled with native LangGraph API
- conditional_edge routing is wired correctly
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

pytest.importorskip("langgraph", reason="langgraph not installed")

from langgraph.graph import END, StateGraph

from aoa.langgraph.adapter import LangGraphAdapter
from aoa.langgraph.agent_state import AgentState
from aoa.langgraph.exceptions import MissingConnectionError, RouteKeyError, StateFieldMismatchError
from tests.action_machine.scenarios.domain_model import OrdersDbManager, PingAction
from tests.action_machine.scenarios.domain_model.full_action import FullAction

# ─────────────────────────────────────────────────────────────────────────────
# State schemas
# ─────────────────────────────────────────────────────────────────────────────


class _PingState(AgentState):
    """State for single-node ping tests."""

    message: str


class _FlowState(AgentState):
    """State for multi-node flow tests."""

    message: str
    routed: bool = False


class _FullState(AgentState):
    """State covering FullAction.Result fields (order_id, txn_id, total, status)."""

    order_id: str = ""
    txn_id: str = ""
    total: float = 0.0
    status: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────


def _adapter(agentstate: type = _PingState, **kwargs: Any) -> LangGraphAdapter:
    return LangGraphAdapter(
        machine=MagicMock(),
        context=MagicMock(),
        agentstate=agentstate,
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestBuildGraph
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildGraph:
    def test_returns_state_graph_instance(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).start(PingAction)
        assert isinstance(adapter.build_graph(), StateGraph)

    def test_raises_missing_connection_before_building_graph(self) -> None:
        # _validate() runs inside build_graph() — MissingConnectionError is raised
        # before StateGraph is ever constructed or returned.
        adapter = _adapter()
        adapter.node(FullAction())  # FullAction requires @connection key="db"
        with pytest.raises(MissingConnectionError, match="db"):
            adapter.build_graph()

    def test_passes_when_connection_provided(self) -> None:
        mock_db = MagicMock(spec=OrdersDbManager)
        adapter = _adapter(agentstate=_FullState, connections={"db": mock_db})
        adapter.node(FullAction()).start(FullAction)
        graph = adapter.build_graph()
        assert isinstance(graph, StateGraph)

    def test_with_plain_fn_node(self) -> None:
        async def done(state: _PingState) -> dict:
            return {}

        adapter = _adapter()
        adapter.node(PingAction()).node(done, name="done")
        adapter.edge(PingAction, "done").start(PingAction)
        graph = adapter.build_graph()
        assert isinstance(graph, StateGraph)

    def test_with_edge_to_end(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).start(PingAction)
        adapter.edge(PingAction, END)
        graph = adapter.build_graph()
        assert isinstance(graph, StateGraph)

    def test_with_conditional_edge(self) -> None:
        async def branch_a(state: _FlowState) -> dict:
            return {"routed": True}

        async def branch_b(state: _FlowState) -> dict:
            return {"routed": False}

        adapter = _adapter(agentstate=_FlowState)
        adapter.node(PingAction())
        adapter.node(branch_a, name="branch_a")
        adapter.node(branch_b, name="branch_b")
        adapter.start(PingAction)
        adapter.conditional_edge(
            PingAction,
            when=lambda s: s.get("routed"),
            if_true="branch_a",
            if_false="branch_b",
        )
        adapter.edge("branch_a", END)
        adapter.edge("branch_b", END)
        graph = adapter.build_graph()
        assert isinstance(graph, StateGraph)

    def test_build_graph_enables_native_continuation(self) -> None:
        """build_graph() → StateGraph can be extended with native LangGraph API."""
        adapter = _adapter()
        adapter.node(PingAction()).start(PingAction)
        graph = adapter.build_graph()
        graph.add_edge("ping", END)
        compiled = graph.compile()
        assert hasattr(compiled, "ainvoke")


# ─────────────────────────────────────────────────────────────────────────────
# TestCompile
# ─────────────────────────────────────────────────────────────────────────────


class TestCompile:
    def test_returns_compiled_graph_with_ainvoke(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).start(PingAction).edge(PingAction, END)
        compiled = adapter.compile()
        assert hasattr(compiled, "ainvoke")

    def test_returns_compiled_graph_with_astream(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).start(PingAction).edge(PingAction, END)
        compiled = adapter.compile()
        assert hasattr(compiled, "astream")

    def test_returns_compiled_graph_with_get_graph(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).start(PingAction).edge(PingAction, END)
        compiled = adapter.compile()
        assert hasattr(compiled, "get_graph")

    def test_missing_connection_raised_at_compile(self) -> None:
        adapter = _adapter()
        adapter.node(FullAction())
        with pytest.raises(MissingConnectionError, match="db"):
            adapter.compile()


# ─────────────────────────────────────────────────────────────────────────────
# TestRouteKeyError
# ─────────────────────────────────────────────────────────────────────────────


class _RouteState(AgentState):
    category: str = ""
    message: str = ""  # covers PingAction.Result.message


async def _set_unknown_category(state: _RouteState) -> dict:
    return {"category": "NOPE"}


def _route_adapter() -> LangGraphAdapter:
    return LangGraphAdapter(
        machine=MagicMock(),
        context=MagicMock(),
        agentstate=_RouteState,
    )


class TestRouteKeyError:
    async def test_unknown_key_raises_route_key_error(self) -> None:
        compiled = (
            _route_adapter()
            .node(_set_unknown_category, name="source")
            .node(PingAction())
            .start("source")
            .route("source", on=lambda s: s.get("category"), paths={"bug": PingAction})
            .edge(PingAction, END)
            .compile()
        )
        with pytest.raises(RouteKeyError):
            await compiled.ainvoke(_RouteState())

    async def test_error_message_includes_key_and_available_paths(self) -> None:
        compiled = (
            _route_adapter()
            .node(_set_unknown_category, name="source")
            .node(PingAction())
            .start("source")
            .route("source", on=lambda s: s.get("category"), paths={"bug": PingAction})
            .edge(PingAction, END)
            .compile()
        )
        with pytest.raises(RouteKeyError, match="NOPE") as exc_info:
            await compiled.ainvoke(_RouteState())
        assert "bug" in str(exc_info.value)
        assert "source" in str(exc_info.value)

    async def test_known_key_does_not_raise(self) -> None:
        async def set_known_category(state: _RouteState) -> dict:
            return {"category": "bug"}

        async def handle_bug(state: _RouteState) -> dict:
            return {}

        compiled = (
            _route_adapter()
            .node(set_known_category, name="source")
            .node(handle_bug, name="handle_bug")
            .start("source")
            .route("source", on=lambda s: s.get("category"), paths={"bug": "handle_bug"})
            .edge("handle_bug", END)
            .compile()
        )
        # No RouteKeyError — "bug" is in paths
        await compiled.ainvoke(_RouteState())


# ─────────────────────────────────────────────────────────────────────────────
# TestStateFieldMismatch
# ─────────────────────────────────────────────────────────────────────────────


class _EmptyState(AgentState):
    """AgentState with no fields — anything an Action returns will be missing."""


class TestStateFieldMismatch:
    def test_mismatch_raises_at_compile(self) -> None:
        # PingAction.Result has "message: str"; _EmptyState has no fields → mismatch
        with pytest.raises(StateFieldMismatchError) as exc_info:
            _adapter(agentstate=_EmptyState).node(PingAction()).compile()
        err = exc_info.value
        assert err.action_name == "PingAction"
        assert "message" in err.missing_fields
        assert err.state_class == "_EmptyState"

    def test_mismatch_error_message_is_readable(self) -> None:
        with pytest.raises(StateFieldMismatchError, match="message"):
            _adapter(agentstate=_EmptyState).node(PingAction()).compile()

    def test_no_error_when_state_covers_result_fields(self) -> None:
        # _PingState has "message: str" — matches PingAction.Result
        _adapter(agentstate=_PingState).node(PingAction()).start(PingAction)
        # no exception

    def test_no_error_when_response_mapper_provided(self) -> None:
        # response_mapper handles the output — field check is skipped
        _adapter(agentstate=_EmptyState).node(
            PingAction(),
            response_mapper=lambda r: {},
        ).start(PingAction)
        # no exception at registration; build_graph/compile skips field check

    def test_no_error_when_agentstate_is_not_agent_state_subclass(self) -> None:
        # test_adapter.py uses agentstate=dict — no model_fields, check is skipped
        _adapter(agentstate=dict).node(PingAction()).start(PingAction)
        # no exception
