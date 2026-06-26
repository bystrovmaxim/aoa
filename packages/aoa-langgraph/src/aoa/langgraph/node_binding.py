# packages/aoa-langgraph/src/aoa/langgraph/node_binding.py
"""
Runtime node helpers for LangGraphController.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides the async node function executed for each Action node in the compiled
LangGraph state graph.

``_run_action_node``
    Entry point called by LangGraph.  Extracts typed Params from the current
    AgentState, runs the Action via ``box.run()``, returns result fields as a
    dict update merged back into state by LangGraph.

``_extract_params``
    UNSET-aware param builder.  Reads fields via ``getattr`` (not the
    ``__getitem__`` path which raises ``FieldNotReadyError``).  Required fields
    that are UNSET raise the error; optional fields that are UNSET are skipped
    so Pydantic applies their default.

``_resolve_params_class``
    Resolves the concrete Params class from an Action class via schema
    introspection or the nested ``Params`` attribute.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    LangGraphController.compile(box)
        │
        ▼  functools.partial(_run_action_node, action_cls, connections, box)
        │
    LangGraph calls node_fn(agentstate)   [agentstate = 4th positional arg]
        │
        ▼  _extract_params(action_cls, agentstate)
        │      reads via getattr — UNSET-aware, never raises on optional fields
        │
        ▼  box.run(action_cls, params, connections=connections)
        │
        ▼  result.model_dump() → returned as dict; LangGraph merges into state

"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from aoa.action_machine.model.base_action import BaseAction
from aoa.langgraph.exceptions import FieldNotReadyError, UnexpectedResultFieldError
from aoa.langgraph.sentinel import UNSET, UnsetType

if TYPE_CHECKING:
    from aoa.action_machine.runtime.tools_box import ToolsBox


async def _run_action_node(
    action_cls: type[BaseAction[Any, Any]],
    params_mapper: Callable[[Any], Any] | None,
    response_mapper: Callable[[Any], Any] | None,
    connections: dict[str, Any] | None,
    box: ToolsBox,
    agentstate: Any,
) -> dict[str, Any]:
    """Execute an Action class as a LangGraph node via box.run(); return result fields."""
    params = params_mapper(agentstate) if params_mapper is not None else _extract_params(action_cls, agentstate)
    result = await box.run(action_cls, params, connections=connections)
    if response_mapper is not None:
        mapped: Any = response_mapper(result)
        raw: dict[str, Any] = mapped.model_dump() if hasattr(mapped, "model_dump") else dict(mapped)
    else:
        raw = result.model_dump()
    state_keys = set(agentstate.model_fields.keys())
    unexpected = [k for k in raw if k not in state_keys]
    if unexpected:
        raise UnexpectedResultFieldError(action_cls, unexpected)
    return raw


def _extract_params(action_cls: type[BaseAction[Any, Any]], agentstate: Any) -> BaseModel:
    """Build Params from agentstate; UNSET mid-fields: required → error, optional → default."""
    params_cls = _resolve_params_class(action_cls)
    data: dict[str, Any] = {}
    for name, field_info in params_cls.model_fields.items():
        raw = getattr(agentstate, name, UNSET)
        if isinstance(raw, UnsetType):
            if field_info.is_required():
                raise FieldNotReadyError(name)
            # optional with default — skip; Pydantic will apply the default
        else:
            data[name] = raw
    return params_cls(**data)


def _resolve_params_class(action_cls: type[BaseAction[Any, Any]]) -> type[BaseModel]:
    """Resolve the Params class for an Action class via schema introspection or nested Params."""
    try:
        cls = ActionSchemaIntentResolver.resolve_params_type(action_cls)
        if cls is not None:
            return cls
    except (ValueError, TypeError):
        pass
    nested = getattr(action_cls, "Params", None)
    if nested is not None:
        return nested  # type: ignore[no-any-return]
    raise TypeError(
        f"{action_cls.__name__} has no resolvable Params type. "
        "Declare the class as BaseAction[YourParams, YourResult]."
    )
