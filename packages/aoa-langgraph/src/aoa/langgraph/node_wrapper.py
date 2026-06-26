"""Wraps an AOA Action into an async LangGraph node callable."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver

if TYPE_CHECKING:
    from pydantic import BaseModel

    from aoa.action_machine.context.context import Context
    from aoa.action_machine.model.base_action import BaseAction
    from aoa.action_machine.resources.base_resource import BaseResource
    from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


def wrap_action(
    action: BaseAction[Any, Any],
    machine: ActionProductMachine,
    context: Context,
    connections: dict[str, BaseResource],
    *,
    params_mapper: Callable[[dict[str, Any]], Any] | None = None,
    response_mapper: Callable[[Any], Any] | None = None,
) -> Any:
    """Return an async callable suitable as a LangGraph node."""

    async def node_fn(agentstate: Any) -> dict[str, Any]:
        if params_mapper is not None:
            params = params_mapper(agentstate)
        else:
            params = _extract_params(action, agentstate)
        result = await machine.run(context, action, params, connections=connections)
        if response_mapper is not None:
            mapped = response_mapper(result)
            return mapped.model_dump() if hasattr(mapped, "model_dump") else dict(mapped)
        return result.model_dump()  # type: ignore[no-any-return]

    node_fn.__name__ = _node_name(type(action))
    return node_fn


def _extract_params(action: BaseAction[Any, Any], agentstate: Any) -> Any:
    """Build the Action's Params instance from matching fields in the current agentstate."""
    params_cls = _params_class(action)
    fields = params_cls.model_fields
    data: dict[str, Any] = {}
    for name, field in fields.items():
        if name in agentstate:
            data[name] = agentstate[name]
        elif field.is_required():
            raise KeyError(
                f"{type(action).__name__} requires field '{name}' in agentstate, "
                f"but it is missing and has no default."
            )
        # else: field has a default or default_factory — Pydantic applies it
    return params_cls(**data)


def _params_class(action: BaseAction[Any, Any]) -> type[BaseModel]:
    """Resolve the Params class for an action via schema introspection or nested Params class."""
    try:
        cls = ActionSchemaIntentResolver.resolve_params_type(type(action))
        if cls is not None:
            return cls
    except (ValueError, TypeError):
        pass
    nested = getattr(type(action), "Params", None)
    if nested is not None:
        return cast("type[BaseModel]", nested)
    raise TypeError(
        f"{type(action).__name__} has no resolvable Params type. "
        "Declare the class as BaseAction[YourParams, YourResult]."
    )


def _node_name(action_cls: type) -> str:
    """Convert ActionClassName → action_class_name (strip trailing 'Action')."""
    name = action_cls.__name__
    if name.endswith("Action"):
        name = name[:-6]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
