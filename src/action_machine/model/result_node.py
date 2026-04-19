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
    ResultNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, edges)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The result class is :attr:`~graph.base_graph_node.BaseGraphNode.obj`.
- ``node_type`` is ``"result_schema"``; ``label`` is the class ``__name__``; ``properties`` and ``edges`` are empty in ``parse``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderResult(BaseResult): ...
    n = ResultNode(OrderResult)
    assert n.node_type == "result_schema" and n.label == "OrderResult"

Edge case: same interchange shape for any concrete ``BaseResult`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; concrete ``BaseResult`` subclasses follow normal model rules where declared.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Model-scoped BaseGraphNode bridge for ``BaseResult`` schema hosts.
CONTRACT: Construct from ``type[TResult]`` via ``parse``; ``node_type="result_schema"``; dotted-path ``id``; label = class name; empty properties and edges.
INVARIANTS: Immutable node; host class on ``BaseGraphNode.obj``.
FLOW: result class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from action_machine.common import qualified_dotted_name
from action_machine.model.base_result import BaseResult
from graph.base_graph_node import BaseGraphNode, Payload

TResult = TypeVar("TResult", bound=BaseResult)


@dataclass(init=False, frozen=True)
class ResultNode(BaseGraphNode[type[TResult]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseResult`` result host class.
    CONTRACT: Built from ``type[TResult]``; ``node_type="result_schema"``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, result_cls: type[TResult]) -> Payload:
        return Payload(
            id=qualified_dotted_name(result_cls),
            node_type="result_schema",
            label=result_cls.__name__,
            properties={},
            edges=[],
        )
