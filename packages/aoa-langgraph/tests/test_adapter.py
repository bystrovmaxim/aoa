# tests/langgraph/test_adapter.py
"""
Unit tests for LangGraphAdapter.

Tests cover:
- Node registration (Action instances and plain async functions)
- Fail-fast edge validation: UnregisteredNodeError raised at .edge() / .conditional_edge() / .route() / .start()
- Connection validation: MissingConnectionError raised at _validate() / build_graph()
- _node_name() naming convention (strip 'Action' suffix, snake_case)
- _declared_connections() reads @connection metadata from action class

These tests do not import langgraph and do not call build_graph() / compile(),
so they pass without langgraph installed.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aoa.action_machine.model.base_params import BaseParams
from aoa.langgraph.adapter import LangGraphAdapter
from aoa.langgraph.exceptions import MissingConnectionError, UnregisteredNodeError
from aoa.langgraph.node_wrapper import _extract_params, _node_name, wrap_action

from .support import FullAction, OrdersDbManager, PingAction

# ─────────────────────────────────────────────────────────────────────────────
# Factory helper
# ─────────────────────────────────────────────────────────────────────────────


def _adapter(**kwargs: Any) -> LangGraphAdapter:
    """Build a LangGraphAdapter with mock machine and context."""
    return LangGraphAdapter(
        machine=MagicMock(),
        context=MagicMock(),
        agentstate=dict,
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TestNodeRegistration
# ─────────────────────────────────────────────────────────────────────────────


class TestNodeRegistration:
    def test_action_instance_registered_by_snake_name(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        assert "ping" in adapter._nodes

    def test_node_entry_marks_is_action_true(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        _, is_action, *_ = adapter._nodes["ping"]
        assert is_action is True

    def test_plain_async_fn_registered_with_explicit_name(self) -> None:
        async def my_fn(state: dict) -> dict:
            return {}

        adapter = _adapter()
        adapter.node(my_fn, name="entry")
        assert "entry" in adapter._nodes
        _, is_action, *_ = adapter._nodes["entry"]
        assert is_action is False

    def test_plain_fn_without_name_raises_value_error(self) -> None:
        async def fn(state: dict) -> dict:
            return {}

        with pytest.raises(ValueError, match="name="):
            _adapter().node(fn)

    def test_sync_fn_raises_type_error(self) -> None:
        def sync_fn(state: dict) -> dict:
            return {}

        with pytest.raises(TypeError, match="async"):
            _adapter().node(sync_fn, name="sync")

    def test_node_returns_self_for_chaining(self) -> None:
        adapter = _adapter()
        assert adapter.node(PingAction()) is adapter

    def test_two_actions_registered_independently(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).node(FullAction())
        assert "ping" in adapter._nodes
        assert "full" in adapter._nodes


# ─────────────────────────────────────────────────────────────────────────────
# TestEdgeValidation
# ─────────────────────────────────────────────────────────────────────────────


class TestEdgeValidation:
    def test_edge_between_registered_nodes_ok(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).node(FullAction())
        adapter.edge(PingAction, FullAction)
        assert ("ping", "full") in adapter._edges

    def test_edge_accepts_string_names(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).node(FullAction())
        adapter.edge("ping", "full")
        assert ("ping", "full") in adapter._edges

    def test_edge_unregistered_source_raises_immediately(self) -> None:
        adapter = _adapter()
        adapter.node(FullAction())
        with pytest.raises(UnregisteredNodeError, match="ping"):
            adapter.edge(PingAction, FullAction)

    def test_edge_unregistered_target_raises_immediately(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        with pytest.raises(UnregisteredNodeError, match="full"):
            adapter.edge(PingAction, FullAction)

    def test_edge_returns_self_for_chaining(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).node(FullAction())
        assert adapter.edge(PingAction, FullAction) is adapter

    def test_conditional_edge_registered_ok(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).node(FullAction())
        adapter.conditional_edge(
            PingAction,
            when=lambda s: True,
            if_true=FullAction,
            if_false=PingAction,
        )
        assert len(adapter._conditional_edges) == 1

    def test_conditional_edge_unregistered_source_raises(self) -> None:
        adapter = _adapter()
        adapter.node(FullAction())
        with pytest.raises(UnregisteredNodeError):
            adapter.conditional_edge(
                PingAction,
                when=lambda s: True,
                if_true=FullAction,
                if_false=FullAction,
            )

    def test_conditional_edge_unregistered_branch_raises(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        with pytest.raises(UnregisteredNodeError, match="full"):
            adapter.conditional_edge(
                PingAction,
                when=lambda s: True,
                if_true=FullAction,  # not registered
                if_false=PingAction,
            )

    def test_route_registered_ok(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction()).node(FullAction())
        adapter.route(PingAction, on=lambda s: "full", paths={"full": FullAction})
        assert len(adapter._routes) == 1

    def test_route_unregistered_path_target_raises(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        with pytest.raises(UnregisteredNodeError, match="full"):
            adapter.route(PingAction, on=lambda s: "full", paths={"full": FullAction})

    def test_edge_to_end_sentinel_passes_without_registration(self) -> None:
        # LangGraph END = "__end__" — dunder names are allowed without .node()
        adapter = _adapter()
        adapter.node(PingAction())
        adapter.edge(PingAction, "__end__")
        assert ("ping", "__end__") in adapter._edges

    def test_edge_to_start_sentinel_passes_without_registration(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        adapter.edge(PingAction, "__start__")
        assert ("ping", "__start__") in adapter._edges


# ─────────────────────────────────────────────────────────────────────────────
# TestStart
# ─────────────────────────────────────────────────────────────────────────────


class TestStart:
    def test_start_sets_name_from_action_class(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        adapter.start(PingAction)
        assert adapter._start_name == "ping"

    def test_start_sets_name_from_string(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        adapter.start("ping")
        assert adapter._start_name == "ping"

    def test_start_unregistered_raises_immediately(self) -> None:
        with pytest.raises(UnregisteredNodeError):
            _adapter().start(PingAction)

    def test_start_returns_self_for_chaining(self) -> None:
        adapter = _adapter()
        adapter.node(PingAction())
        assert adapter.start(PingAction) is adapter


# ─────────────────────────────────────────────────────────────────────────────
# TestNodeName
# ─────────────────────────────────────────────────────────────────────────────


class TestNodeName:
    def test_strips_action_suffix(self) -> None:
        assert _node_name(PingAction) == "ping"

    def test_strips_action_suffix_full(self) -> None:
        assert _node_name(FullAction) == "full"

    def test_snake_case_multi_word(self) -> None:
        class CheckInventoryAction:
            pass

        assert _node_name(CheckInventoryAction) == "check_inventory"  # type: ignore[arg-type]

    def test_no_action_suffix_lowercased(self) -> None:
        class Monitor:
            pass

        assert _node_name(Monitor) == "monitor"  # type: ignore[arg-type]

    def test_single_word_uppercase(self) -> None:
        class RouteAction:
            pass

        assert _node_name(RouteAction) == "route"  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# TestDeclaredConnections
# ─────────────────────────────────────────────────────────────────────────────


class TestDeclaredConnections:
    def test_action_without_connections_returns_empty_set(self) -> None:
        adapter = _adapter()
        assert adapter._declared_connections(PingAction()) == set()

    def test_action_with_connection_returns_key(self) -> None:
        adapter = _adapter()
        assert adapter._declared_connections(FullAction()) == {"db"}


# ─────────────────────────────────────────────────────────────────────────────
# TestValidate
# ─────────────────────────────────────────────────────────────────────────────


class TestValidate:
    def test_passes_when_all_connections_provided(self) -> None:
        mock_db = MagicMock(spec=OrdersDbManager)
        adapter = _adapter(connections={"db": mock_db})
        adapter.node(FullAction())
        adapter._validate()  # no exception

    def test_passes_with_extra_connections_in_pool(self) -> None:
        mock_db = MagicMock(spec=OrdersDbManager)
        adapter = _adapter(connections={"db": mock_db, "cache": MagicMock()})
        adapter.node(PingAction()).node(FullAction())
        adapter._validate()  # extra "cache" is filtered per action — no error

    def test_raises_missing_connection(self) -> None:
        adapter = _adapter()  # empty connections pool
        adapter.node(FullAction())
        with pytest.raises(MissingConnectionError, match="db"):
            adapter._validate()

    def test_plain_fn_node_skipped_in_validate(self) -> None:
        async def fn(state: dict) -> dict:
            return {}

        adapter = _adapter()  # no connections pool
        adapter.node(fn, name="fn")
        adapter._validate()  # plain fns have no @connection — no error

    def test_no_action_nodes_validate_passes(self) -> None:
        adapter = _adapter()
        adapter._validate()  # empty node list — no error


# ─────────────────────────────────────────────────────────────────────────────
# Minimal fake action stubs for _extract_params / wrap_action tests.
# These do not need @meta / @check_roles — only .Params matters.
# ─────────────────────────────────────────────────────────────────────────────


class _RequiredField:
    """Stub with one required str field."""

    class Params(BaseParams):
        name: str


class _OptionalNone:
    """Stub with one Optional field whose default is None."""

    class Params(BaseParams):
        name: str | None = None


class _OptionalDefault:
    """Stub with one int field whose default is 42."""

    class Params(BaseParams):
        count: int = 42


class _Mixed:
    """Stub with one required and one optional field."""

    class Params(BaseParams):
        name: str
        count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# TestExtractParams
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractParams:
    def test_required_field_present_in_agentstate(self) -> None:
        action = _RequiredField()
        params = _extract_params(action, {"name": "alice"})  # type: ignore[arg-type]
        assert params.name == "alice"

    def test_required_field_absent_raises_key_error(self) -> None:
        action = _RequiredField()
        with pytest.raises(KeyError, match="name"):
            _extract_params(action, {})  # type: ignore[arg-type]

    def test_optional_none_default_absent_uses_none(self) -> None:
        action = _OptionalNone()
        params = _extract_params(action, {})  # type: ignore[arg-type]
        assert params.name is None

    def test_optional_int_default_absent_uses_default(self) -> None:
        action = _OptionalDefault()
        params = _extract_params(action, {})  # type: ignore[arg-type]
        assert params.count == 42

    def test_optional_int_default_overridden_by_agentstate(self) -> None:
        action = _OptionalDefault()
        params = _extract_params(action, {"count": 99})  # type: ignore[arg-type]
        assert params.count == 99

    def test_mixed_required_present_optional_absent(self) -> None:
        action = _Mixed()
        params = _extract_params(action, {"name": "bob"})  # type: ignore[arg-type]
        assert params.name == "bob"
        assert params.count == 0

    def test_empty_params_class_needs_no_agentstate_keys(self) -> None:
        params = _extract_params(PingAction(), {})
        assert params is not None

    def test_key_error_message_includes_action_class_name(self) -> None:
        action = _RequiredField()
        with pytest.raises(KeyError, match="_RequiredField"):
            _extract_params(action, {})  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# TestWrapAction
# ─────────────────────────────────────────────────────────────────────────────


class TestWrapAction:
    def test_wrapped_node_has_correct_name(self) -> None:
        node_fn = wrap_action(PingAction(), MagicMock(), MagicMock(), {})
        assert node_fn.__name__ == "ping"

    async def test_wrapped_node_calls_machine_run(self) -> None:
        mock_machine = AsyncMock()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"message": "pong"}
        mock_machine.run.return_value = mock_result

        node_fn = wrap_action(PingAction(), mock_machine, MagicMock(), {})
        result = await node_fn({})

        mock_machine.run.assert_awaited_once()
        assert result == {"message": "pong"}

    async def test_wrapped_node_returns_result_model_dump(self) -> None:
        mock_machine = AsyncMock()
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"status": "ok", "count": 3}
        mock_machine.run.return_value = mock_result

        node_fn = wrap_action(PingAction(), mock_machine, MagicMock(), {})
        result = await node_fn({})

        assert result == {"status": "ok", "count": 3}

    async def test_wrapped_node_passes_filtered_connections(self) -> None:
        mock_machine = AsyncMock()
        mock_machine.run.return_value = MagicMock(model_dump=lambda: {})
        mock_db = MagicMock()

        node_fn = wrap_action(PingAction(), mock_machine, MagicMock(), {"db": mock_db})
        await node_fn({})

        _, call_kwargs = mock_machine.run.call_args
        assert call_kwargs.get("connections") == {"db": mock_db}

    async def test_wrapped_node_extracts_params_from_agentstate(self) -> None:
        mock_machine = AsyncMock()
        mock_machine.run.return_value = MagicMock(model_dump=lambda: {})

        # Use a fake action stub with a required field
        class _NamedAction:
            class Params(BaseParams):
                name: str

        node_fn = wrap_action(
            _NamedAction(),  # type: ignore[arg-type]
            mock_machine,
            MagicMock(),
            {},
        )
        await node_fn({"name": "alice"})

        call_args, _ = mock_machine.run.call_args
        passed_params = call_args[2]  # positional: context, action, params
        assert passed_params.name == "alice"
