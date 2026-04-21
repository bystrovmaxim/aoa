# src/action_machine/model/graph_model/params_graph_node.py
"""
ParamsGraphNode — interchange node for ``BaseParams`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a concrete params **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

Interchange ``node_type`` is ``"Params"``; ``id`` is the dotted class path. (Legacy facet rows may still use the string ``params_schema``.)

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TParams]   (``TParams`` bound to ``BaseParams``)
              │
              v
    ParamsGraphNode(...)  ──>  frozen ``BaseGraphNode`` (node_id, node_type, label, properties, edges)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.model.base_params import BaseParams
from action_machine.introspection_tools import TypeIntrospection
from graph.base_graph_node import BaseGraphNode

TParams = TypeVar("TParams", bound=BaseParams)


@dataclass(init=False, frozen=True)
class ParamsGraphNode(BaseGraphNode[type[TParams]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseParams`` params host class.
    CONTRACT: Built from ``type[TParams]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Params"

    def __init__(self, params_cls: type[TParams]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(params_cls),
            node_type=ParamsGraphNode.NODE_TYPE,
            label=params_cls.__name__,
            properties={},
            edges=[],
            node_obj=params_cls,
        )
