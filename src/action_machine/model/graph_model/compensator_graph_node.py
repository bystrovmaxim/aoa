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
``IntentIntrospection.description_for_callable`` (``CallableKind.COMPENSATE``) when present;
``edges`` are empty. Host class and method name come from :class:`TypeIntrospection`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Callable[..., Any]   unbound/bound compensator method  ->  ``node_obj``
              │
              v
    CompensatorGraphNode(compensator_func)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from action_machine.introspection_tools import CallableKind, IntentIntrospection, TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(init=False, frozen=True)
class CompensatorGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``@compensate`` callable on a ``BaseAction`` host class.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(action_cls) + ':' + method_name``; :attr:`NODE_TYPE` matches facet ``Compensator``; ``properties`` include ``description`` when ``IntentIntrospection.description_for_callable(..., COMPENSATE)`` returns it; ``edges`` empty.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Compensator"

    def __init__(self, compensator_func: Callable[..., Any]) -> None:
        action_cls = TypeIntrospection.owner_type_for_method(compensator_func)
        method_name = TypeIntrospection.unwrapped_callable_name(compensator_func)
        action_id = TypeIntrospection.full_qualname(action_cls)
        desc = IntentIntrospection.description_for_callable(compensator_func, CallableKind.COMPENSATE)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=CompensatorGraphNode.NODE_TYPE,
            label=method_name,
            properties={"description": desc} if desc is not None else {},
            node_obj=compensator_func,
        )
