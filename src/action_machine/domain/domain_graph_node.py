# src/action_machine/domain/domain_graph_node.py
"""
DomainGraphNode — interchange node for BaseDomain marker classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a ``BaseDomain`` subclass. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the domain class is the same object as
:attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TDomain]   (``TDomain`` bound to ``BaseDomain``)
              │
              v
    DomainGraphNode(...)  ──>  frozen ``BaseGraphNode`` (node_id, node_type, label, properties, edges)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Shop context"

    n = DomainGraphNode(ShopDomain)
    assert n.node_type == "Domain" and n.label == "ShopDomain"

Edge case: same interchange shape for any concrete ``BaseDomain`` subclass type passed in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from action_machine.domain.base_domain import BaseDomain
from graph.qualified_name import cls_qualified_dotted_id
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import EdgeRelationship

TDomain = TypeVar("TDomain", bound=BaseDomain)


@dataclass(init=False, frozen=True)
class DomainGraphNode(BaseGraphNode[type[TDomain]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a bounded-context domain marker.
    CONTRACT: Built from ``type[TDomain]``; dotted ``id``, ``__name__`` label; ``properties`` carry ``name`` / ``description`` (facet ``node_meta`` parity); ``belongs_to`` → ``ApplicationContext`` in ``edges``.
    AI-CORE-END
    """

    def __init__(self, domain_cls: type[TDomain]) -> None:
        # Local import: avoid loading ``application`` package (and inspector) during ``domain`` import.
        from action_machine.legacy.application_context import (  # pylint: disable=import-outside-toplevel
            ApplicationContext,
        )

        app_id = cls_qualified_dotted_id(ApplicationContext)
        super().__init__(
            node_id=cls_qualified_dotted_id(domain_cls),
            node_type="Domain",
            label=domain_cls.__name__,
            properties={
                "name": domain_cls.name,
                "description": domain_cls.description,
            },
            edges=[
                BaseGraphEdge(
                    edge_name="belongs_to",
                    is_dag=False,
                    source_node_id=cls_qualified_dotted_id(domain_cls),
                    source_node_type="Domain",
                    source_node_obj=domain_cls,
                    source_node_relationship=EdgeRelationship.COMPOSITION,
                    target_node_id=app_id,
                    target_node_type="Application",
                    target_node_obj=ApplicationContext,
                    target_node_relationship=EdgeRelationship.ASSOCIATION,
                ),
            ],
            node_obj=domain_cls,
        )
