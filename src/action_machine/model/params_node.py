# src/action_machine/model/params_node.py
"""
ParamsNode — interchange node for ``BaseParams`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~action_machine.graph.base_graph_node.BaseGraphNode` view derived from
a concrete params **class** object **without** retaining a reference to that class on the
node instance. All interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``links``.

Interchange ``node_type`` is ``"Params"``; ``id`` follows the same dotted-path rules as
described-fields / coordinator facets.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TParams]   (``TParams`` bound to ``BaseParams``)
              │
              v
    ParamsNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, links)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The params class is not stored on :class:`ParamsNode` instances (only interchange fields).
- ``node_type`` is ``"Params"``; ``label`` is the class ``__name__``; ``properties`` and ``links`` are empty in ``parse``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderParams(BaseParams): ...
    n = ParamsNode(OrderParams)
    assert n.node_type == "Params" and n.label == "OrderParams"

Edge case: same interchange shape for any concrete ``BaseParams`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; concrete ``BaseParams`` subclasses follow normal model rules where declared.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Model-scoped BaseGraphNode bridge for ``BaseParams`` schema hosts.
CONTRACT: Construct from ``type[TParams]`` via ``parse``; ``node_type="Params"``; dotted-path ``id``; label = class name; empty properties and links.
INVARIANTS: Immutable node; no params type reference on the instance.
FLOW: params class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
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
from action_machine.model.base_params import BaseParams

TParams = TypeVar("TParams", bound=BaseParams)


@dataclass(init=False, frozen=True)
class ParamsNode(BaseGraphNode[type[TParams]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseParams`` params host class.
    CONTRACT: Built from ``type[TParams]``; dotted ``id``, ``__name__`` label, empty ``properties`` and ``links``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, params_cls: type[TParams]) -> Any:
        return SimpleNamespace(
            id=qualified_dotted_name(params_cls),
            node_type="Params",
            label=params_cls.__name__,
            properties={},
            links=[],
        )
