# src/action_machine/model/graph_model/result_graph_node.py
"""
ResultGraphNode — interchange node for ``BaseResult`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a concrete result **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

Interchange ``node_type`` is ``"Result"``; ``id`` is the dotted class path. (Legacy facet rows may still use the string ``result_schema``.)

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TResult]   (``TResult`` bound to ``BaseResult``)
              │
              v
    ResultGraphNode(...)  ──>  frozen ``BaseGraphNode`` (node_id, node_type, label, properties, edges)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.model.base_result import BaseResult
from graph.base_graph_node import BaseGraphNode
from action_machine.tools import Introspection

TResult = TypeVar("TResult", bound=BaseResult)


@dataclass(init=False, frozen=True)
class ResultGraphNode(BaseGraphNode[type[TResult]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseResult`` result host class.
    CONTRACT: Built from ``type[TResult]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Result"

    def __init__(self, result_cls: type[TResult]) -> None:
        super().__init__(
            node_id=Introspection.full_qualname(result_cls),
            node_type=ResultGraphNode.NODE_TYPE,
            label=result_cls.__name__,
            properties={},
            edges=[],
            node_obj=result_cls,
        )
