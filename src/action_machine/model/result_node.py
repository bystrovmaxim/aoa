# src/action_machine/model/result_node.py
"""
ResultNode — interchange node for ``BaseResult`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~action_machine.graph.base_graph_node.BaseGraphNode` view derived from
a concrete result **class** object **without** retaining a reference to that class on the
node instance. All interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``links``.

Interchange ``node_type`` is ``"Result"``; ``id`` follows the same dotted-path rules as
described-fields / coordinator facets.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TResult]   (``TResult`` bound to ``BaseResult``)
              │
              v
    ResultNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, links)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The result class is not stored on :class:`ResultNode` instances (only interchange fields).
- ``node_type`` is ``"Result"``; ``label`` is the class ``__name__``; ``properties`` and ``links`` are empty in ``parse``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderResult(BaseResult): ...
    n = ResultNode(OrderResult)
    assert n.node_type == "Result" and n.label == "OrderResult"

Edge case: same interchange shape for any concrete ``BaseResult`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; concrete ``BaseResult`` subclasses follow normal model rules where declared.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Model-scoped BaseGraphNode bridge for ``BaseResult`` schema hosts.
CONTRACT: Construct from ``type[TResult]`` via ``parse``; ``node_type="Result"``; dotted-path ``id``; label = class name; empty properties and links.
INVARIANTS: Immutable node; no result type reference on the instance.
FLOW: result class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, TypeVar

from action_machine.common import qualified_dotted_name
from action_machine.graph.base_graph_node import BaseGraphNode
from action_machine.model.base_result import BaseResult

TResult = TypeVar("TResult", bound=BaseResult)


@dataclass(init=False, frozen=True)
class ResultNode(BaseGraphNode[type[TResult]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseResult`` result host class.
    CONTRACT: Built from ``type[TResult]``; dotted ``id``, ``__name__`` label, empty ``properties`` and ``links``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, result_cls: type[TResult]) -> Any:
        return SimpleNamespace(
            id=qualified_dotted_name(result_cls),
            node_type="Result",
            label=result_cls.__name__,
            properties={},
            links=[],
        )
