# src/action_machine/model/params_node.py
"""
ParamsNode — interchange node for ``BaseParams`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a concrete params **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

Interchange ``node_type`` is ``"params_schema"`` (aligned with facet ``params_schema`` hosts); ``id`` is the dotted class path.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TParams]   (``TParams`` bound to ``BaseParams``)
              │
              v
    ParamsNode(...)  ──>  frozen ``BaseGraphNode`` (node_id, node_type, label, properties, edges)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from action_machine.model.base_params import BaseParams
from graph.base_graph_node import BaseGraphNode
from graph.qualified_name import cls_qualified_dotted_id

TParams = TypeVar("TParams", bound=BaseParams)


@dataclass(init=False, frozen=True)
class ParamsNode(BaseGraphNode[type[TParams]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseParams`` params host class.
    CONTRACT: Built from ``type[TParams]``; ``node_type="params_schema"``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    def __init__(self, params_cls: type[TParams]) -> None:
        super().__init__(
            node_id=cls_qualified_dotted_id(params_cls),
            node_type="params_schema",
            label=params_cls.__name__,
            properties={},
            edges=[],
            node_obj=params_cls,
        )
