# packages/aoa-langgraph/tests/test_adapter.py
"""
Unit tests for LangGraphController data contract, topology, and node_binding helpers.

Tests do not import langgraph and do not call .compile() or .ainvoke(),
so they pass without a running ToolsBox.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from aoa.action_machine.model.base_params import BaseParams
from aoa.langgraph.agent_state import AgentState
from aoa.langgraph.controller import LangGraphController
from aoa.langgraph.exceptions import (
    CompileBeforeBuildError,
    ControllerAlreadyBuiltError,
    DeadEndNodeError,
    DuplicateFieldError,
    FieldHasNoProducerError,
    FieldNotReadyError,
    FinishUnreachableError,
    InconsistentFinishOutputError,
    MissingFieldDescriptionError,
    NoEntryPointError,
    NoFinishPointError,
    NoNodesError,
    OutputHasNoProducerError,
    StateFieldMismatchError,
    UndeclaredOutputFieldError,
    UnexpectedResultFieldError,
    UnreachableNodeError,
    UnregisteredNodeError,
)
from aoa.langgraph.node_binding import _extract_params
from aoa.langgraph.sentinel import UNSET, UnsetType

from .support import FullAction, PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _minimal_built() -> LangGraphController:
    """Return a minimal built controller (PingAction node, no inp fields)."""
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
# TestDataContract
# ─────────────────────────────────────────────────────────────────────────────


class TestDataContract:
    def test_inp_field_stored(self) -> None:
        ctrl = LangGraphController()
        ctrl.inp("query", str, "Search query")
        assert "query" in ctrl._inp_fields

    def test_mid_field_stored(self) -> None:
        ctrl = LangGraphController()
        ctrl.mid("result", str, "Intermediate result")
        assert "result" in ctrl._mid_fields

    def test_out_field_global_when_no_pending_finish(self) -> None:
        ctrl = LangGraphController()
        ctrl.mid("result", str, "desc")
        ctrl.out("result")
        assert "result" in ctrl._out_fields

    def test_out_after_finish_is_per_finish(self) -> None:
        ctrl = LangGraphController()
        ctrl.mid("result", str, "desc")
        ctrl.node(PingAction)
        ctrl.finish(PingAction)
        ctrl.out("result")
        assert "result" in ctrl._finish_nodes["PingAction"]
        assert "result" not in ctrl._out_fields

    def test_duplicate_inp_raises(self) -> None:
        ctrl = LangGraphController()
        ctrl.inp("query", str, "desc")
        with pytest.raises(DuplicateFieldError, match="query"):
            ctrl.inp("query", str, "desc2")

    def test_duplicate_mid_raises(self) -> None:
        ctrl = LangGraphController()
        ctrl.mid("result", str, "desc")
        with pytest.raises(DuplicateFieldError, match="result"):
            ctrl.mid("result", str, "desc2")

    def test_inp_empty_description_raises(self) -> None:
        ctrl = LangGraphController()
        with pytest.raises(MissingFieldDescriptionError):
            ctrl.inp("query", str, "")

    def test_mid_empty_description_raises(self) -> None:
        ctrl = LangGraphController()
        with pytest.raises(MissingFieldDescriptionError):
            ctrl.mid("result", str, "")

    def test_fluent_chain_returns_self(self) -> None:
        ctrl = LangGraphController()
        result = ctrl.inp("q", str, "desc").mid("r", str, "desc")
        assert result is ctrl

    def test_methods_raise_after_build(self) -> None:
        ctrl = _minimal_built()
        with pytest.raises(ControllerAlreadyBuiltError):
            ctrl.inp("extra", str, "desc")


# ─────────────────────────────────────────────────────────────────────────────
# TestNodeRegistration
# ─────────────────────────────────────────────────────────────────────────────


class TestNodeRegistration:
    def test_action_class_registered_by_qualname(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction)
        assert "PingAction" in ctrl._nodes

    def test_action_class_custom_name_overrides_qualname(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction, name="ping_check")
        assert "ping_check" in ctrl._nodes
        assert "PingAction" not in ctrl._nodes

    def test_async_fn_with_name_registered(self) -> None:
        async def my_fn(state: Any) -> dict:
            return {}

        ctrl = LangGraphController()
        ctrl.node(my_fn, name="entry")
        assert "entry" in ctrl._nodes

    def test_fn_without_name_raises(self) -> None:
        async def fn(state: Any) -> dict:
            return {}

        with pytest.raises(ValueError, match="name="):
            LangGraphController().node(fn)

    def test_sync_fn_raises(self) -> None:
        def sync_fn(state: Any) -> dict:
            return {}

        with pytest.raises(TypeError, match="async"):
            LangGraphController().node(sync_fn, name="sync")

    def test_node_returns_self_for_chaining(self) -> None:
        ctrl = LangGraphController()
        assert ctrl.node(PingAction) is ctrl

    def test_two_action_classes_registered_independently(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction).node(FullAction)
        assert "PingAction" in ctrl._nodes
        assert "FullAction" in ctrl._nodes


# ─────────────────────────────────────────────────────────────────────────────
# TestTopology
# ─────────────────────────────────────────────────────────────────────────────


class TestTopology:
    def test_edge_between_registered_nodes_stored(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction).node(FullAction)
        ctrl.edge(PingAction, FullAction)
        assert ("PingAction", "FullAction") in ctrl._edges

    def test_edge_unregistered_src_raises_immediately(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(FullAction)
        with pytest.raises(UnregisteredNodeError, match="PingAction"):
            ctrl.edge(PingAction, FullAction)

    def test_edge_unregistered_dst_raises_immediately(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction)
        with pytest.raises(UnregisteredNodeError, match="FullAction"):
            ctrl.edge(PingAction, FullAction)

    def test_start_sets_name(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction).start(PingAction)
        assert "PingAction" in ctrl._start_names

    def test_start_unregistered_raises_immediately(self) -> None:
        with pytest.raises(UnregisteredNodeError):
            LangGraphController().start(PingAction)

    def test_finish_creates_entry_in_finish_nodes(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction).finish(PingAction)
        assert "PingAction" in ctrl._finish_nodes

    def test_conditional_edge_registered(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction).node(FullAction)
        ctrl.conditional_edge(PingAction, when=lambda s: True, if_true=FullAction, if_false=PingAction)
        assert len(ctrl._conditional_edges) == 1

    def test_route_registered(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction).node(FullAction)
        ctrl.route(PingAction, on=lambda s: "full", paths={"full": FullAction})
        assert len(ctrl._routes) == 1

    def test_edge_returns_self(self) -> None:
        ctrl = LangGraphController()
        ctrl.node(PingAction).node(FullAction)
        assert ctrl.edge(PingAction, FullAction) is ctrl


# ─────────────────────────────────────────────────────────────────────────────
# TestBuild
# ─────────────────────────────────────────────────────────────────────────────


class TestBuild:
    def test_no_nodes_raises(self) -> None:
        with pytest.raises(NoNodesError):
            LangGraphController().mid("x", str, "d").out("x").build()

    def test_no_start_raises(self) -> None:
        ctrl = (
            LangGraphController()
            .mid("message", str, "d")
            .out("message")
            .node(PingAction)
            .finish(PingAction)
        )
        with pytest.raises(NoEntryPointError):
            ctrl.build()

    def test_no_finish_raises(self) -> None:
        ctrl = (
            LangGraphController()
            .mid("message", str, "d")
            .out("message")
            .node(PingAction)
            .start(PingAction)
        )
        with pytest.raises(NoFinishPointError):
            ctrl.build()

    def test_dead_end_node_raises(self) -> None:
        async def dead_end(state: Any) -> dict:
            return {}

        ctrl = (
            LangGraphController()
            .mid("message", str, "d")
            .out("message")
            .node(dead_end, name="dead_end")  # no outgoing edge
            .node(PingAction)
            .start("dead_end")
            .finish(PingAction)
            # "dead_end" has no edge to PingAction → DeadEndNodeError
        )
        with pytest.raises(DeadEndNodeError):
            ctrl.build()

    def test_undeclared_out_field_raises(self) -> None:
        ctrl = (
            LangGraphController()
            .out("ghost")  # "ghost" not in inp or mid
            .node(PingAction)
            .start(PingAction)
            .finish(PingAction)
        )
        with pytest.raises(UndeclaredOutputFieldError):
            ctrl.build()

    def test_result_field_not_in_inp_mid_raises(self) -> None:
        # PingAction.Result.message not in inp or mid; "other" is, so NoOutputFieldsError is bypassed
        ctrl = (
            LangGraphController()
            .mid("other", str, "some other field")
            .out("other")
            .node(PingAction)
            .start(PingAction)
            .finish(PingAction)
        )
        with pytest.raises(UnexpectedResultFieldError):
            ctrl.build()

    def test_silent_returns_none_on_failure(self) -> None:
        ctrl = (
            LangGraphController()
            .node(PingAction)
            .start(PingAction)
            .finish(PingAction)
        )
        assert ctrl.build(silent=True) is None

    def test_successful_build_returns_self(self) -> None:
        ctrl = _minimal_built()
        assert ctrl._built is True

    def test_compile_before_build_raises(self) -> None:
        ctrl = LangGraphController()
        with pytest.raises(CompileBeforeBuildError):
            ctrl.compile(MagicMock())

    def test_finish_unreachable_raises(self) -> None:
        async def looping(s: Any) -> dict:
            return {}

        ctrl = (
            LangGraphController()
            .mid("message", str, "d")
            .out("message")
            .node(looping, name="looping")
            .node(PingAction)
            .edge("looping", "looping")  # self-loop: not a dead end
            .start("looping")
            .finish(PingAction)  # unreachable from "looping"
        )
        with pytest.raises(FinishUnreachableError):
            ctrl.build()

    def test_unreachable_node_raises(self) -> None:
        async def orphan(s: Any) -> dict:
            return {}

        ctrl = (
            LangGraphController()
            .mid("message", str, "d")
            .out("message")
            .node(PingAction)
            .node(orphan, name="orphan")
            .edge("orphan", PingAction)  # orphan→PingAction, but nothing points to orphan
            .start(PingAction)
            .finish(PingAction)
        )
        with pytest.raises(UnreachableNodeError):
            ctrl.build()

    def test_inconsistent_finish_output_raises(self) -> None:
        ctrl = (
            LangGraphController()
            .mid("message", str, "d")
            .node(PingAction)
            .node(FullAction)
            .start(PingAction)
            .finish(PingAction)
            .out("message")   # PingAction gets per-finish out
            .finish(FullAction)  # FullAction gets no per-finish out → inconsistent
        )
        with pytest.raises(InconsistentFinishOutputError):
            ctrl.build()

    def test_field_has_no_producer_raises(self) -> None:
        # FullAction.Params.user_id is required but neither inp nor written by any action
        ctrl = (
            LangGraphController()
            .mid("user_id", str, "u")
            .mid("amount", float, "a")
            .mid("order_id", str, "o")
            .mid("txn_id", str, "t")
            .mid("total", float, "tot")
            .mid("status", str, "s")
            .out("order_id")
            .node(FullAction)
            .start(FullAction)
            .finish(FullAction)
        )
        with pytest.raises(FieldHasNoProducerError):
            ctrl.build()

    def test_output_has_no_producer_raises(self) -> None:
        async def fn(s: Any) -> dict:
            return {}

        ctrl = (
            LangGraphController()
            .mid("message", str, "m")
            .out("message")  # no action writes it
            .node(fn, name="fn")
            .start("fn")
            .finish("fn")
        )
        with pytest.raises(OutputHasNoProducerError):
            ctrl.build()

    def test_diamond_topology_builds_successfully(self) -> None:
        # A→(B|C)→PingAction: covers conditional_edge in _build_adjacency
        # and BFS revisit (PingAction enqueued from both B and C)
        async def node_a(s: Any) -> dict:
            return {}

        async def node_b(s: Any) -> dict:
            return {}

        async def node_c(s: Any) -> dict:
            return {}

        ctrl = (
            LangGraphController()
            .mid("message", str, "d")
            .out("message")
            .node(node_a, name="A")
            .node(node_b, name="B")
            .node(node_c, name="C")
            .node(PingAction)
            .conditional_edge("A", when=lambda s: True, if_true="B", if_false="C")
            .edge("B", PingAction)
            .edge("C", PingAction)
            .start("A")
            .finish(PingAction)
            .build()
        )
        assert ctrl._built is True


# ─────────────────────────────────────────────────────────────────────────────
# TestSentinel
# ─────────────────────────────────────────────────────────────────────────────


class TestSentinel:
    def test_unset_is_falsy(self) -> None:
        assert not UNSET  # exercises __bool__ → return False

    def test_unset_singleton(self) -> None:
        assert UnsetType() is UNSET  # second __new__ call hits the 54→56 branch


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────


class TestExceptions:
    def test_state_field_mismatch_stores_attrs(self) -> None:
        exc = StateFieldMismatchError("MyAction", ["f1", "f2"], "MyState")
        assert exc.action_name == "MyAction"
        assert exc.missing_fields == ["f1", "f2"]
        assert exc.state_class == "MyState"


# ─────────────────────────────────────────────────────────────────────────────
# TestAgentState
# ─────────────────────────────────────────────────────────────────────────────


class TestAgentState:
    def test_set_field_returned(self) -> None:
        from aoa.langgraph.agent_state import AgentState
        from aoa.langgraph.sentinel import UNSET

        class _S(AgentState):
            name: str | UnsetType = UNSET

        state = _S(name="alice")
        assert state["name"] == "alice"

    def test_unset_field_raises_field_not_ready(self) -> None:
        from aoa.langgraph.agent_state import AgentState
        from aoa.langgraph.sentinel import UNSET

        class _S(AgentState):
            name: str | UnsetType = UNSET

        state = _S()  # name stays UNSET
        with pytest.raises(FieldNotReadyError):
            _ = state["name"]


# ─────────────────────────────────────────────────────────────────────────────
# Stubs for _extract_params tests
# ─────────────────────────────────────────────────────────────────────────────


class _RequiredNameAction:
    """Stub: one required str field."""

    class Params(BaseParams):
        name: str


class _OptionalCountAction:
    """Stub: one optional int field with default 42."""

    class Params(BaseParams):
        count: int = 42


class _MixedAction:
    """Stub: one required + one optional field."""

    class Params(BaseParams):
        name: str
        count: int = 0


class _NameState(AgentState):
    name: str | UnsetType = UNSET


class _CountState(AgentState):
    count: int | UnsetType = UNSET


class _MixedState(AgentState):
    name: str | UnsetType = UNSET
    count: int | UnsetType = UNSET


# ─────────────────────────────────────────────────────────────────────────────
# TestExtractParams
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractParams:
    def test_required_field_set_in_state(self) -> None:
        state = _NameState(name="alice")
        params = _extract_params(_RequiredNameAction, state)  # type: ignore[arg-type]
        assert params.name == "alice"

    def test_required_field_unset_raises_field_not_ready(self) -> None:
        state = _NameState()  # name=UNSET
        with pytest.raises(FieldNotReadyError, match="name"):
            _extract_params(_RequiredNameAction, state)  # type: ignore[arg-type]

    def test_optional_field_unset_uses_default(self) -> None:
        state = _CountState()  # count=UNSET
        params = _extract_params(_OptionalCountAction, state)  # type: ignore[arg-type]
        assert params.count == 42

    def test_optional_field_set_overrides_default(self) -> None:
        state = _CountState(count=99)
        params = _extract_params(_OptionalCountAction, state)  # type: ignore[arg-type]
        assert params.count == 99

    def test_mixed_required_set_optional_unset(self) -> None:
        state = _MixedState(name="bob")  # count=UNSET
        params = _extract_params(_MixedAction, state)  # type: ignore[arg-type]
        assert params.name == "bob"
        assert params.count == 0

    def test_empty_params_needs_no_state_fields(self) -> None:
        state = _NameState()
        params = _extract_params(PingAction, state)
        assert params is not None
