# src/action_machine/graph_model/nodes/domain_graph_node.py
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
from typing import ClassVar, TypeVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode

TDomain = TypeVar("TDomain", bound=BaseDomain)


@dataclass(init=False, frozen=True)
class DomainGraphNode(BaseGraphNode[type[TDomain]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a bounded-context domain marker.
    CONTRACT: Built from ``type[TDomain]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label; ``properties`` carry ``name`` / ``description`` (facet ``node_meta`` parity). ``edges`` is empty ``AssociationGraphEdge`` stubs until coordinators wire targets.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Domain"

    def __init__(self, domain_cls: type[TDomain]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(domain_cls),
            node_type=DomainGraphNode.NODE_TYPE,
            label=domain_cls.__name__,
            properties={
                "name": domain_cls.name,
                "description": domain_cls.description,
            },
            node_obj=domain_cls,
        )
