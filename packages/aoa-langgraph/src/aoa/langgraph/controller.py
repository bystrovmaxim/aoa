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

from dataclasses import dataclass

from pydantic import BaseModel

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.langgraph.exceptions import (
    ControllerAlreadyBuiltError,
    DuplicateFieldError,
    MissingFieldDescriptionError,
)


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
        self._inp_fields: dict[str, FieldMeta] = {}
        self._mid_fields: dict[str, FieldMeta] = {}
        self._out_fields: list[str] = []
        self._built: bool = False

    # ── BaseResource abstract method overrides ────────────────────────────────

    def get_wrapper_class(self) -> type[BaseResource] | None:
        from aoa.langgraph.wrapper_langgraph_controller import WrapperLangGraphController
        return WrapperLangGraphController

    async def check_rollup_support(self) -> bool:
        return False

    # ── field declaration ─────────────────────────────────────────────────────

    def inp(
        self,
        name_or_cls: str | type,
        type_: type | None = None,
        description: str | None = None,
    ) -> LangGraphController:
        """Declare an input field, or expand a Pydantic model class into input fields.

        String form:  .inp("issue", str, "Raw text of the submitted ticket")
        Class form:   .inp(CheckParams)  — descriptions from Field(description=...)
        """
        self._check_not_built()
        if isinstance(name_or_cls, type) and issubclass(name_or_cls, BaseModel):
            return self._expand_model(name_or_cls, target=self._inp_fields)
        name: str = name_or_cls  # type: ignore[assignment]
        if not description:
            raise MissingFieldDescriptionError(name)
        self._check_duplicate(name)
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
        self._check_duplicate(name)
        self._mid_fields[name] = FieldMeta(name=name, type=type_, description=description)
        return self

    def out(self, name: str) -> LangGraphController:
        """Declare an output field returned by ainvoke(). Must be declared in .inp() or .mid()."""
        self._check_not_built()
        if name in self._out_fields:
            raise DuplicateFieldError(name)
        self._out_fields.append(name)
        return self

    # ── private helpers ───────────────────────────────────────────────────────

    def _check_not_built(self) -> None:
        if self._built:
            raise ControllerAlreadyBuiltError(
                "LangGraphController is already built. "
                "No fluent methods can be called after .build()."
            )

    def _check_duplicate(self, name: str) -> None:
        if name in self._inp_fields or name in self._mid_fields:
            raise DuplicateFieldError(name)

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
            self._check_duplicate(field_name)
            target[field_name] = FieldMeta(
                name=field_name,
                type=field_info.annotation,  # type: ignore[arg-type]
                description=desc,
            )
        return self
