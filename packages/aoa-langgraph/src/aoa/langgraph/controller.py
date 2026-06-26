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

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, overload

from pydantic import BaseModel

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.langgraph.exceptions import (
    ControllerAlreadyBuiltError,
    DuplicateFieldError,
    MissingFieldDescriptionError,
    UnregisteredNodeError,
)
from aoa.langgraph.wrapper_langgraph_controller import WrapperLangGraphController


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

    # ── BaseResource abstract method overrides ────────────────────────────────

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return WrapperLangGraphController

    async def check_rollup_support(self) -> bool:
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

    # ── private helpers ───────────────────────────────────────────────────────

    def _check_not_built(self) -> None:
        if self._built:
            raise ControllerAlreadyBuiltError(
                "LangGraphController is already built. "
                "No fluent methods can be called after .build()."
            )

    def _check_duplicate_field(self, name: str) -> None:
        if name in self._inp_fields or name in self._mid_fields:
            raise DuplicateFieldError(name)

    def _clear_pending_finishes(self) -> None:
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
