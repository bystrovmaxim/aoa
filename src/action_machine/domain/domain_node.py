# src/action_machine/domain/domain_node.py
"""
DomainNode — interchange node for BaseDomain marker classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~action_machine.graph.base_graph_node.BaseGraphNode` view derived from
a ``BaseDomain`` subclass **without** retaining a reference to that class on the
node instance. All interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``links``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TDomain]   (``TDomain`` bound to ``BaseDomain``)
              │
              v
    DomainNode.parse  ──>  frozen ``BaseGraphNode`` (id, node_type, label, properties, links)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The domain class is not stored on :class:`DomainNode` instances (only interchange fields).
- ``label`` is the domain class ``__name__``; ``properties`` and ``links`` are empty in ``parse``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Shop context"

    n = DomainNode(ShopDomain)
    assert n.node_type == "Domain" and n.label == "ShopDomain"

Edge case: same interchange shape for any concrete ``BaseDomain`` subclass type passed in.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; ``BaseDomain`` concrete subclasses are validated at class definition where applicable.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Domain-scoped BaseGraphNode bridge for BaseDomain subclasses.
CONTRACT: Construct from ``type[TDomain]`` via ``parse``; ``node_type="Domain"``; dotted-path ``id``; label = class name; empty properties and links.
INVARIANTS: Immutable node; no domain type reference on the instance.
FLOW: domain class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, TypeVar

from action_machine.common import qualified_dotted_name
from action_machine.domain.base_domain import BaseDomain
from action_machine.graph.base_graph_node import BaseGraphNode

TDomain = TypeVar("TDomain", bound=BaseDomain)


@dataclass(init=False, frozen=True)
class DomainNode(BaseGraphNode[type[TDomain]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a bounded-context domain marker.
    CONTRACT: Built from ``type[TDomain]``; dotted ``id``, ``__name__`` label, empty ``properties`` and ``links``.
    AI-CORE-END
    """

    @classmethod
    def parse(cls, domain_cls: type[TDomain]) -> Any:
        return SimpleNamespace(
            id=qualified_dotted_name(domain_cls),
            node_type="Domain",
            label=domain_cls.__name__,
            properties={},
            links=[],
        )
