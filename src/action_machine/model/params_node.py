# src/action_machine/model/params_node.py
"""
ParamsNode — interchange node for ``BaseParams`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a concrete params **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.obj`.

Interchange ``node_type`` is ``"params_schema"`` (aligned with facet ``params_schema`` hosts); ``id`` is the dotted class path.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TParams]   (``TParams`` bound to ``BaseParams``)
              │
              v
    ParamsNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, edges)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The params class is :attr:`~graph.base_graph_node.BaseGraphNode.obj`.
- ``node_type`` is ``"params_schema"``; ``label`` is the class ``__name__``; ``properties`` and ``edges`` are empty in ``parse``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderParams(BaseParams): ...
    n = ParamsNode(OrderParams)
    assert n.node_type == "params_schema" and n.label == "OrderParams"

Edge case: same interchange shape for any concrete ``BaseParams`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; concrete ``BaseParams`` subclasses follow normal model rules where declared.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Model-scoped BaseGraphNode bridge for ``BaseParams`` schema hosts.
CONTRACT: Construct from ``type[TParams]`` via ``parse``; ``node_type="params_schema"``; dotted-path ``id``; label = class name; empty properties and edges.
INVARIANTS: Immutable node; host class on ``BaseGraphNode.obj``.
FLOW: params class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from action_machine.legacy.qualified_name import qualified_dotted_name
from action_machine.model.base_params import BaseParams
from graph.base_graph_node import BaseGraphNode, Payload

TParams = TypeVar("TParams", bound=BaseParams)


@dataclass(init=False, frozen=True)
class ParamsNode(BaseGraphNode[type[TParams]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseParams`` params host class.
    CONTRACT: Built from ``type[TParams]``; ``node_type="params_schema"``; dotted ``id``, ``__name__`` label; empty ``properties`` and ``edges``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, params_cls: type[TParams]) -> Payload:
        return Payload(
            id=qualified_dotted_name(params_cls),
            node_type="params_schema",
            label=params_cls.__name__,
            properties={},
            edges=[],
        )
