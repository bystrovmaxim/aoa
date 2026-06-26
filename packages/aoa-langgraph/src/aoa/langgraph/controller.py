# packages/aoa-langgraph/src/aoa/langgraph/controller.py
"""
LangGraphController — fluent builder for a compiled LangGraph state graph.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``LangGraphController`` is the canonical AOA primitive for a compiled LangGraph
graph. It owns the graph lifecycle: built once at application start, invoked
per request. It is a ``BaseController`` — an internal long-lived dependency
whose lifecycle the process fully owns.

The fluent API has three ordered phases:

1. **Data contract** — ``.inp()`` / ``.mid()`` / ``.out()``
2. **Topology** — ``.node()`` / ``.edge()`` / ``.start()`` / ``.finish()``
3. **Build** — ``.build()`` validates the contract and compiles the graph

After ``.build()`` the controller is immutable and safe to share across
concurrent ``.ainvoke()`` calls.

═══════════════════════════════════════════════════════════════════════════════
DATA CONTRACT
═══════════════════════════════════════════════════════════════════════════════

Three field kinds with distinct roles:

``inp``
    Caller-provided input. Set from the dict passed to ``.ainvoke(data, box)``
    before the first node runs. Readable by all nodes.

``mid``
    Inter-node produced values. Start ``UNSET``; a node reads an ``UNSET``
    mid-field via ``AgentState.__getitem__`` and gets ``FieldNotReadyError``.

``out``
    Fields returned by ``.ainvoke()``. Must be declared in ``inp`` or ``mid``;
    name is the only argument — type and description are inherited.

═══════════════════════════════════════════════════════════════════════════════
TOPOLOGY
═══════════════════════════════════════════════════════════════════════════════

``_pending_finishes`` tracks the most recent ``.finish()`` calls so that
subsequent ``.out()`` calls bind to those specific finish nodes.  Any
topology method other than ``.out()`` and ``.finish()`` clears the list.

Multiple ``.start()`` calls register parallel start nodes; all fire via
``add_edge(START, name)`` in ``compile()``.

``connections=`` in ``.node()`` must contain only app-lifetime / stateless
resources.  Request-scoped resources reach the node through the per-call
``box`` via ``@depends`` / ``@connection`` on the Action.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    LangGraphController()
        .inp("issue", str, "Raw text of the submitted support ticket")
        .mid("category", str, "bug | feature | billing — set by ClassifyAction")
        .out("category")
        .node(ClassifyAction)
        .node(ResolveAction)
        .edge(ClassifyAction, ResolveAction)
        .start(ClassifyAction)
        .finish(ResolveAction)
        .build()                    # _built = True; _agentstate generated
         │
         ▼
    controller.ainvoke({"issue": "..."}, box)
         │
         ▼  compile(box) — StateGraph + partial(_run_action_node, ..., box)
         │
         ▼  LangGraph executes nodes; UNSET travels via schema(**input)
         │
         ▼  _extract_output — reads out-fields, raises if still UNSET

"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, overload

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, create_model

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.langgraph.agent_state import AgentState
from aoa.langgraph.exceptions import (
    CompileBeforeBuildError,
    ControllerAlreadyBuiltError,
    DuplicateFieldError,
    InconsistentFinishOutputError,
    MissingFieldDescriptionError,
    NoOutputFieldsError,
    RouteKeyError,
    UndeclaredOutputFieldError,
    UnregisteredNodeError,
)
from aoa.langgraph.node_binding import _run_action_node
from aoa.langgraph.sentinel import UNSET, UnsetType
from aoa.langgraph.wrapper_langgraph_controller import WrapperLangGraphController

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from aoa.action_machine.runtime.tools_box import ToolsBox


@dataclass(frozen=True)
class FieldMeta:
    """
    AI-CORE-BEGIN
        ROLE: Immutable descriptor for a single declared field (inp or mid).
        CONTRACT: name, type, and description are set once at declaration; never mutated.
        INVARIANTS: Frozen dataclass; description is always non-empty.
    AI-CORE-END
    """

    name: str
    type: type
    description: str


@dataclass
class NodeInfo:
    """
    AI-CORE-BEGIN
        ROLE: Per-node metadata stored at .node() time (= application start).
        CONTRACT: connections must be app-lifetime / stateless; request-scoped resources go via box.
        INVARIANTS: name is unique within _nodes; action_or_fn is an Action class or async callable.
    AI-CORE-END
    """

    name: str
    action_or_fn: Any
    params_mapper: Any | None = None
    response_mapper: Any | None = None
    connections: dict[str, Any] | None = None


@dataclass
class ConditionalEdgeInfo:
    """
    AI-CORE-BEGIN
        ROLE: Descriptor for a .conditional_edge() declaration.
        CONTRACT: src, if_true, if_false are registered node names.
        INVARIANTS: when is a sync callable returning bool.
    AI-CORE-END
    """

    src: str
    when: Any
    if_true: str
    if_false: str


@dataclass
class RouteInfo:
    """
    AI-CORE-BEGIN
        ROLE: Descriptor for a .route() declaration.
        CONTRACT: src is a registered node name; paths values are registered node names.
        INVARIANTS: on is a sync callable returning a key present in paths at runtime.
    AI-CORE-END
    """

    src: str
    on: Any
    paths: dict[str, str] = field(default_factory=dict)


# ── Compile-time routing helpers ─────────────────────────────────────────────


def _make_cond_edge_fn(when: Any, if_true: str, if_false: str) -> Callable[[Any], str]:
    """Create a binary condition router for .conditional_edge() declarations."""
    def _route(s: Any) -> str:
        return if_true if when(s) else if_false
    return _route


def _make_route_fn(on: Any, paths: dict[str, str]) -> Callable[[Any], str]:
    """Create a multi-path router for .route() declarations; raises RouteKeyError on unknown key."""
    def _route(s: Any) -> str:
        key = on(s)
        if key not in paths:
            raise RouteKeyError(
                f"Route key '{key}' not found. Declared paths: {list(paths)}."
            )
        return paths[key]
    return _route


# ── Controller ────────────────────────────────────────────────────────────────


@exclude_graph_model
class LangGraphController(BaseController):
    """
    AI-CORE-BEGIN
        ROLE: Owner of a compiled LangGraph graph; executes it per-request via ainvoke().
        CONTRACT: Immutable after .build(); safe to share across concurrent ainvoke() calls.
        INVARIANTS: _built=True after build(); no _box or _compiled stored — both are per-call.
    AI-CORE-END
    """

    def __init__(self) -> None:
        """Initialise an empty controller ready for fluent field and topology declaration."""
        # data contract
        self._inp_fields: dict[str, FieldMeta] = {}
        self._mid_fields: dict[str, FieldMeta] = {}
        self._out_fields: list[str] = []
        # topology
        self._nodes: dict[str, NodeInfo] = {}
        self._edges: list[tuple[str, str]] = []
        self._conditional_edges: list[ConditionalEdgeInfo] = []
        self._routes: list[RouteInfo] = []
        self._start_names: list[str] = []
        self._finish_nodes: dict[str, list[str]] = {}
        self._pending_finishes: list[str] = []
        # lifecycle
        self._built: bool = False
        self._agentstate: type[AgentState] | None = None

    # ── BaseResource abstract method overrides ────────────────────────────────

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """Return WrapperLangGraphController so child actions receive a restricted proxy."""
        return WrapperLangGraphController

    async def check_rollup_support(self) -> bool:
        """Controllers do not participate in rollup transactions."""
        return False

    # ── field declaration ─────────────────────────────────────────────────────

    @overload
    def inp(self, name: str, type_: type, description: str) -> LangGraphController: ...

    @overload
    def inp(self, cls: type[BaseModel]) -> LangGraphController: ...

    def inp(self, name_or_cls: Any, type_: type | None = None, description: str | None = None) -> LangGraphController:  # type: ignore[misc]
        """Declare an input field, or expand a Pydantic model class into input fields.

        String form:  .inp("issue", str, "Raw text of the submitted ticket")
        Class form:   .inp(CheckParams)  — descriptions from Field(description=...)
        """
        self._check_not_built()
        if isinstance(name_or_cls, type) and issubclass(name_or_cls, BaseModel):
            return self._expand_model(name_or_cls, target=self._inp_fields)
        name: str = name_or_cls
        if not description:
            raise MissingFieldDescriptionError(name)
        self._check_duplicate_field(name)
        self._inp_fields[name] = FieldMeta(name=name, type=type_, description=description)  # type: ignore[arg-type]
        return self

    def mid(
        self,
        name: str,
        type_: type,
        description: str | None = None,
    ) -> LangGraphController:
        """Declare an intermediate field produced by a node during execution."""
        self._check_not_built()
        if not description:
            raise MissingFieldDescriptionError(name)
        self._check_duplicate_field(name)
        self._mid_fields[name] = FieldMeta(name=name, type=type_, description=description)
        return self

    def out(self, name: str) -> LangGraphController:
        """Declare an output field returned by ainvoke(). Must be declared in .inp() or .mid().

        If called after .finish(), binds the field to those specific finish nodes.
        Otherwise adds to the global output list.
        """
        self._check_not_built()
        if self._pending_finishes:
            for finish_name in self._pending_finishes:
                if name in self._finish_nodes[finish_name]:
                    raise DuplicateFieldError(name)
                self._finish_nodes[finish_name].append(name)
        else:
            if name in self._out_fields:
                raise DuplicateFieldError(name)
            self._out_fields.append(name)
        return self

    # ── topology ──────────────────────────────────────────────────────────────

    @overload
    def node(
        self,
        action_or_fn: type[BaseAction[Any, Any]],
        *,
        name: str | None = None,
        params_mapper: Any | None = None,
        response_mapper: Any | None = None,
        connections: dict[str, Any] | None = None,
    ) -> LangGraphController: ...

    @overload
    def node(
        self,
        action_or_fn: Callable[..., Any],
        *,
        name: str,
        params_mapper: Any | None = None,
        response_mapper: Any | None = None,
        connections: dict[str, Any] | None = None,
    ) -> LangGraphController: ...

    def node(
        self,
        action_or_fn: Any,
        *,
        name: str | None = None,
        params_mapper: Any | None = None,
        response_mapper: Any | None = None,
        connections: dict[str, Any] | None = None,
    ) -> LangGraphController:
        """Register a graph node.

        Action class:    .node(ClassifyAction)
        Async function:  .node(some_fn, name="process")
        Partial:         .node(partial(some_fn, arg), name="process")
        """
        self._check_not_built()
        self._clear_pending_finishes()
        is_action_cls = isinstance(action_or_fn, type) and issubclass(action_or_fn, BaseAction)
        if is_action_cls:
            node_name = name or TypeIntrospection.qualname_of(action_or_fn)
        else:
            if name is None:
                raise ValueError(
                    f"name= is required for non-Action nodes (got {action_or_fn!r})."
                )
            if not inspect.iscoroutinefunction(action_or_fn):
                raise TypeError(
                    f"Node '{name}' must be an async callable "
                    f"(inspect.iscoroutinefunction returned False). "
                    f"Note: functools.partial wrapping an async fn may return False on Python < 3.12."
                )
            node_name = name
        self._nodes[node_name] = NodeInfo(
            name=node_name,
            action_or_fn=action_or_fn,
            params_mapper=params_mapper,
            response_mapper=response_mapper,
            connections=connections,
        )
        return self

    def edge(self, src: Any, dst: Any) -> LangGraphController:
        """Declare a directed edge between two registered nodes."""
        self._check_not_built()
        self._clear_pending_finishes()
        src_name = self._resolve_registered(src)
        dst_name = self._resolve_registered(dst)
        self._edges.append((src_name, dst_name))
        return self

    def conditional_edge(
        self,
        src: Any,
        *,
        when: Any,
        if_true: Any,
        if_false: Any,
    ) -> LangGraphController:
        """Declare a conditional edge: when(state) → True → if_true, False → if_false."""
        self._check_not_built()
        self._clear_pending_finishes()
        src_name = self._resolve_registered(src)
        if_true_name = self._resolve_registered(if_true)
        if_false_name = self._resolve_registered(if_false)
        self._conditional_edges.append(
            ConditionalEdgeInfo(src=src_name, when=when, if_true=if_true_name, if_false=if_false_name)
        )
        return self

    def route(
        self,
        src: Any,
        *,
        on: Any,
        paths: dict[Any, Any],
    ) -> LangGraphController:
        """Declare a multi-path routing edge: on(state) → key → paths[key]."""
        self._check_not_built()
        self._clear_pending_finishes()
        src_name = self._resolve_registered(src)
        resolved_paths = {key: self._resolve_registered(target) for key, target in paths.items()}
        self._routes.append(RouteInfo(src=src_name, on=on, paths=resolved_paths))
        return self

    def start(self, action_or_name: Any) -> LangGraphController:
        """Mark a node as a start node. Multiple calls register parallel start nodes."""
        self._check_not_built()
        self._clear_pending_finishes()
        self._start_names.append(self._resolve_registered(action_or_name))
        return self

    def finish(self, action_or_name: Any) -> LangGraphController:
        """Mark a node as a finish node. Subsequent .out() calls bind to this finish."""
        self._check_not_built()
        name = self._resolve_registered(action_or_name)
        self._finish_nodes[name] = []
        self._pending_finishes.append(name)
        return self

    # ── build ─────────────────────────────────────────────────────────────────

    def build(self, silent: bool = False) -> LangGraphController | None:
        """Validate the data contract, build _agentstate, set _built = True.

        Returns self on success. With silent=True returns None on validation error.
        May be called again to rebuild after topology changes.
        """
        self._built = False
        self._agentstate = None
        try:
            self._validate_contract()
            self._agentstate = self._build_agentstate()
            self._built = True
            return self
        except (NoOutputFieldsError, InconsistentFinishOutputError, UndeclaredOutputFieldError):
            if silent:
                return None
            raise

    def compile(self, box: ToolsBox) -> CompiledStateGraph[Any]:
        """Build a fresh StateGraph from declared topology and return the compiled graph.

        Synchronous — no IO, no await.  Builds a new graph on every call so
        ``box`` is never stored on the controller (see box-free invariant).
        """
        if not self._built:
            raise CompileBeforeBuildError(
                "Call .build() before .compile()."
            )

        assert self._agentstate is not None  # guaranteed by _built=True
        sg = StateGraph(self._agentstate)

        for node_name, node_info in self._nodes.items():
            action_or_fn = node_info.action_or_fn
            is_action = isinstance(action_or_fn, type) and issubclass(action_or_fn, BaseAction)
            if is_action:
                node_fn: Any = functools.partial(
                    _run_action_node, action_or_fn, node_info.connections, box
                )
            else:
                node_fn = action_or_fn
            sg.add_node(node_name, node_fn)

        for src, dst in self._edges:
            sg.add_edge(src, dst)

        for ce in self._conditional_edges:
            sg.add_conditional_edges(
                ce.src,
                _make_cond_edge_fn(ce.when, ce.if_true, ce.if_false),
            )

        for rt in self._routes:
            sg.add_conditional_edges(rt.src, _make_route_fn(rt.on, rt.paths))

        for start_name in self._start_names:
            sg.add_edge(START, start_name)

        for finish_name in self._finish_nodes:
            sg.add_edge(finish_name, END)

        return sg.compile()

    # ── private helpers ───────────────────────────────────────────────────────

    def _check_not_built(self) -> None:
        """Raise ControllerAlreadyBuiltError if .build() has already been called."""
        if self._built:
            raise ControllerAlreadyBuiltError(
                "LangGraphController is already built. "
                "No fluent methods can be called after .build()."
            )

    def _check_duplicate_field(self, name: str) -> None:
        """Raise DuplicateFieldError if name is already declared in inp or mid."""
        if name in self._inp_fields or name in self._mid_fields:
            raise DuplicateFieldError(name)

    def _clear_pending_finishes(self) -> None:
        """Clear pending finishes; called by every topology method except .finish() and .out()."""
        self._pending_finishes.clear()

    def _resolve_name(self, thing: Any) -> str:
        """Convert an Action class, Action instance, callable, or str to a node name."""
        if isinstance(thing, str):
            return thing
        if isinstance(thing, type) and issubclass(thing, BaseAction):
            return TypeIntrospection.qualname_of(thing)
        if isinstance(thing, type):
            return TypeIntrospection.qualname_of(thing)
        if isinstance(thing, BaseAction):
            return TypeIntrospection.qualname_of(type(thing))
        if hasattr(thing, "__name__"):
            return str(thing.__name__)
        raise TypeError(f"Cannot resolve node name from {thing!r}.")

    def _resolve_registered(self, thing: Any) -> str:
        """Resolve to node name and verify it is registered in _nodes."""
        name = self._resolve_name(thing)
        if name not in self._nodes:
            raise UnregisteredNodeError(
                f"Node '{name}' is not registered. Call .node() before referencing it in edges."
            )
        return name

    def _expand_model(
        self,
        cls: type[BaseModel],
        *,
        target: dict[str, FieldMeta],
    ) -> LangGraphController:
        """Expand all fields of a Pydantic model class into the given field registry."""
        for field_name, field_info in cls.model_fields.items():
            desc = field_info.description
            if not desc:
                raise MissingFieldDescriptionError(field_name)
            self._check_duplicate_field(field_name)
            target[field_name] = FieldMeta(
                name=field_name,
                type=field_info.annotation,  # type: ignore[arg-type]
                description=desc,
            )
        return self

    def _all_out_names(self) -> set[str]:
        """Collect all output field names: global out-fields plus all per-finish out-fields."""
        names: set[str] = set(self._out_fields)
        for outs in self._finish_nodes.values():
            names.update(outs)
        return names

    def _validate_contract(self) -> None:
        """Run all data-contract checks; raise on the first violation found."""
        all_out = self._all_out_names()

        if not all_out:
            raise NoOutputFieldsError("No output fields declared. Call .out() at least once.")

        if self._finish_nodes:
            with_outs = [n for n, outs in self._finish_nodes.items() if outs]
            without_outs = [n for n, outs in self._finish_nodes.items() if not outs]
            if with_outs and without_outs:
                raise InconsistentFinishOutputError(with_outs, without_outs)

        declared = set(self._inp_fields) | set(self._mid_fields)
        for name in all_out:
            if name not in declared:
                raise UndeclaredOutputFieldError(name)

    def _build_agentstate(self) -> type[AgentState]:
        """Create the dynamic AgentState subclass with typed inp and UNSET-defaulted mid fields."""
        field_definitions: dict[str, Any] = {}

        for name, meta in self._inp_fields.items():
            field_definitions[name] = (meta.type, ...)

        for name, meta in self._mid_fields.items():
            field_definitions[name] = (meta.type | UnsetType, UNSET)

        return create_model("AgentState", __base__=AgentState, **field_definitions)
