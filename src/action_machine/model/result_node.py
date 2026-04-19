# src/action_machine/model/result_node.py
"""
ResultNode — interchange node for ``BaseResult`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a concrete result **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.obj`.

Interchange ``node_type`` is ``"result_schema"`` (aligned with facet ``result_schema`` hosts); ``id`` is the dotted class path.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TResult]   (``TResult`` bound to ``BaseResult``)
              │
              v
    ResultNode(...)  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, edges)

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Model-scoped BaseGraphNode bridge for ``BaseResult`` schema hosts.
CONTRACT: Construct from ``type[TResult]`` via ``__init__``; ``node_type="result_schema"``; dotted-path ``id``; label = class name; empty properties and edges.
INVARIANTS: Immutable node; host class on ``BaseGraphNode.obj``.
FLOW: result class -> ``ResultNode.__init__`` -> frozen ``BaseGraphNode`` fields.
EXTENSION POINTS: Other graph node specializations follow the same constructor pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from graph.qualified_name import cls_qualified_dotted_id
from action_machine.model.base_result import BaseResult
from graph.base_graph_node import BaseGraphNode

TResult = TypeVar("TResult", bound=BaseResult)


@dataclass(init=False, frozen=True)
class ResultNode(BaseGraphNode[type[TResult]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseResult`` result host class.
    CONTRACT: Built from ``type[TResult]``; ``node_type="result_schema"``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    def __init__(self, result_cls: type[TResult]) -> None:
        super().__init__(
            id=cls_qualified_dotted_id(result_cls),
            node_type="result_schema",
            label=result_cls.__name__,
            properties={},
            edges=[],
            obj=result_cls,
        )
