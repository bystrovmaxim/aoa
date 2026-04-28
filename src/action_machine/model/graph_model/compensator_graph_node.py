# src/action_machine/model/graph_model/compensator_graph_node.py
"""
CompensatorGraphNode — interchange node for a ``@compensate`` method on an action class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one
compensator **callable** on a concrete ``BaseAction`` subclass: ``node_id`` is the action
dotted id plus ``:`` plus the method name, interchange ``node_type`` is
``Compensator``, ``label`` is the method name; ``properties`` may carry ``description`` from
``CompensateIntentResolver.resolve_description`` when present;
``edges`` are empty. Host class and method name come from :class:`TypeIntrospection`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.intents.compensate.compensate_intent_resolver import CompensateIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(init=False, frozen=True)
class CompensatorGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``@compensate`` callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(_action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``Compensator``; ``properties`` include ``description`` when ``CompensateIntentResolver.resolve_description(...)`` returns it; ``edges`` empty.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Compensator"

    def __init__(self, compensator_func: Callable[..., Any], _action_cls: type[Any]) -> None:
        method_name = TypeIntrospection.unwrapped_callable_name(compensator_func)
        action_id = TypeIntrospection.full_qualname(_action_cls)
        desc = CompensateIntentResolver.resolve_description(compensator_func)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=CompensatorGraphNode.NODE_TYPE,
            label=method_name,
            properties={"description": desc} if desc is not None else {},
            node_obj=compensator_func,
        )
