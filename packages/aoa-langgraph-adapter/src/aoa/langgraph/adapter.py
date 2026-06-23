"""LangGraphAdapter — fluent builder that turns AOA Actions into LangGraph nodes."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from langgraph.graph import StateGraph

from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver
from aoa.action_machine.model.base_action import BaseAction
from aoa.langgraph.agent_state import AgentState
from aoa.langgraph.exceptions import (
    MissingConnectionError,
    RouteKeyError,
    StateFieldMismatchError,
    UnregisteredNodeError,
)
from aoa.langgraph.node_wrapper import _node_name, wrap_action

if TYPE_CHECKING:
    from aoa.action_machine.context.context import Context
    from aoa.action_machine.resources.base_resource import BaseResource
    from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class LangGraphAdapter[S: AgentState]:
    """Fluent builder: registers AOA Actions (or plain async functions) as LangGraph nodes."""

    def __init__(
        self,
        *,
        machine: ActionProductMachine,
        context: Context,
        agentstate: type[S],
        connections: dict[str, BaseResource] | None = None,
    ) -> None:
        self._machine = machine
        self._context = context
        self._agentstate = agentstate
        self._connections: dict[str, Any] = dict(connections or {})

        # name → (callable, is_action, action_instance | None, params_mapper | None, response_mapper | None)
        self._nodes: dict[str, tuple[Any, bool, Any, Any, Any]] = {}
        self._edges: list[tuple[str, str]] = []
        self._conditional_edges: list[tuple[str, Callable[..., Any], str, str]] = []
        self._routes: list[tuple[str, Callable[..., Any], dict[str, str]]] = []
        self._start_name: str | None = None

    # ── node registration ────────────────────────────────────────────────────

    def node(
        self,
        action_or_fn: Any,
        *,
        name: str | None = None,
        params_mapper: Callable[..., Any] | None = None,
        response_mapper: Callable[..., Any] | None = None,
    ) -> LangGraphAdapter[S]:
        """Register an AOA Action or a plain async function as a node.

        params_mapper: called with the full agentstate dict; must return a Params instance.
            Use it when state field names differ from Action Params field names.
        response_mapper: called with the Action result; must return a dict or a Pydantic model.
            Use it to rename or reshape result fields before they are merged into agentstate.
        """
        if isinstance(action_or_fn, BaseAction):
            node_name = _node_name(type(action_or_fn))
            self._nodes[node_name] = (action_or_fn, True, action_or_fn, params_mapper, response_mapper)
        else:
            if name is None:
                raise ValueError("Plain function nodes require an explicit name=... argument.")
            if not inspect.iscoroutinefunction(action_or_fn):
                raise TypeError(f"Node '{name}' must be an async function or an AOA Action instance.")
            self._nodes[name] = (action_or_fn, False, None, None, None)

        return self

    # ── edges ────────────────────────────────────────────────────────────────

    def edge(self, source: Any, target: Any) -> LangGraphAdapter[S]:
        src = self._resolve_name(source, context="edge source")
        dst = self._resolve_name(target, context="edge target")
        self._edges.append((src, dst))
        return self

    def conditional_edge(
        self,
        source: Any,
        *,
        when: Callable[[Any], bool],
        if_true: Any,
        if_false: Any,
    ) -> LangGraphAdapter[S]:
        src = self._resolve_name(source, context="conditional_edge source")
        true_name = self._resolve_name(if_true, context="conditional_edge if_true")
        false_name = self._resolve_name(if_false, context="conditional_edge if_false")
        self._conditional_edges.append((src, when, true_name, false_name))
        return self

    def route(
        self,
        source: Any,
        *,
        on: Callable[[Any], Any],
        paths: dict[Any, Any],
    ) -> LangGraphAdapter[S]:
        src = self._resolve_name(source, context="route source")
        resolved_paths = {k: self._resolve_name(v, context=f"route path '{k}'") for k, v in paths.items()}
        self._routes.append((src, on, resolved_paths))
        return self

    def start(self, action_or_name: Any) -> LangGraphAdapter[S]:
        self._start_name = self._resolve_name(action_or_name, context="start")
        return self

    # ── compile ──────────────────────────────────────────────────────────────

    def build_graph(self) -> Any:
        """Build and return a StateGraph (not yet compiled).

        Raises MissingConnectionError if any Action node declares a @connection
        key that is absent from the adapter connections pool.
        """
        self._validate()

        graph: Any = StateGraph(self._agentstate)

        for node_name, (action_or_fn, is_action, action, params_mapper, response_mapper) in self._nodes.items():
            if is_action:
                declared = self._declared_connections(action)
                filtered = {k: v for k, v in self._connections.items() if k in declared}
                callable_node = wrap_action(
                    action, self._machine, self._context, filtered,
                    params_mapper=params_mapper,
                    response_mapper=response_mapper,
                )
            else:
                callable_node = action_or_fn
            graph.add_node(node_name, callable_node)

        for src, dst in self._edges:
            graph.add_edge(src, dst)

        for src, when, true_name, false_name in self._conditional_edges:

            def _router(
                s: Any,
                _w: Callable[[Any], bool] = when,
                _t: str = true_name,
                _f: str = false_name,
            ) -> str:
                return _t if _w(s) else _f

            graph.add_conditional_edges(src, _router, {true_name: true_name, false_name: false_name})

        for src, on, resolved_paths in self._routes:

            def _multi_router(
                s: Any,
                _on: Callable[[Any], Any] = on,
                _p: dict[str, str] = resolved_paths,
                _src: str = src,
            ) -> str:
                key = _on(s)
                if key not in _p:
                    raise RouteKeyError(
                        f"route from '{_src}': key {key!r} not found in paths. "
                        f"Available: {sorted(_p)}"
                    )
                return _p[key]

            graph.add_conditional_edges(src, _multi_router, {v: v for v in resolved_paths.values()})

        if self._start_name:
            graph.set_entry_point(self._start_name)

        return graph

    def compile(self) -> Any:
        """Build, validate, and compile the graph.

        Returns a standard LangGraph CompiledGraph — ainvoke(), astream(),
        get_graph().draw_mermaid() all work out of the box.

        Raises MissingConnectionError (via build_graph) if a connection is missing.
        """
        return self.build_graph().compile()

    # ── internals ────────────────────────────────────────────────────────────

    def _resolve_name(self, action_or_name: Any, *, context: str) -> str:
        if isinstance(action_or_name, type) and issubclass(action_or_name, BaseAction):
            name = _node_name(action_or_name)
        elif isinstance(action_or_name, BaseAction):
            name = _node_name(type(action_or_name))
        elif isinstance(action_or_name, str):
            name = action_or_name
        else:
            raise TypeError(
                f"{context}: expected an Action class, Action instance, or str, "
                f"got {type(action_or_name).__name__}."
            )

        # LangGraph sentinels ("__end__", "__start__") pass through without registration.
        if name.startswith("__") and name.endswith("__"):
            return name

        if name not in self._nodes:
            raise UnregisteredNodeError(
                f"{context}: '{name}' is not registered. " f"Call .node(...) before declaring edges."
            )
        return name

    def _validate(self) -> None:
        """Validate connections and Result/AgentState field compatibility for Action nodes."""
        is_typed_state = isinstance(self._agentstate, type) and issubclass(self._agentstate, AgentState)

        for _name, (_, is_action, action, _pm, _rm) in self._nodes.items():
            if not is_action:
                continue

            declared = self._declared_connections(action)
            missing = declared - self._connections.keys()
            if missing:
                raise MissingConnectionError(
                    f"{type(action).__name__} requires {missing}, "
                    f"not found in adapter connections pool. "
                    f"Available: {set(self._connections.keys())}"
                )

            # Skip Result field check when response_mapper handles the output or state has no model_fields.
            if _rm is not None or not is_typed_state:
                continue
            try:
                result_type = ActionSchemaIntentResolver.resolve_result_type(type(action))
            except (ValueError, TypeError):
                continue
            state_fields = set(self._agentstate.model_fields)
            missing_in_state = sorted(set(result_type.model_fields) - state_fields)
            if missing_in_state:
                raise StateFieldMismatchError(
                    action_name=type(action).__name__,
                    missing_fields=missing_in_state,
                    state_class=self._agentstate.__name__,
                )

    def _declared_connections(self, action: Any) -> set[str]:
        infos = getattr(type(action), "_connection_info", [])
        return {info.key for info in infos}
