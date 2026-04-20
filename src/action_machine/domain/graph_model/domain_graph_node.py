# src/action_machine/domain/graph_model/domain_graph_node.py
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

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.domain.base_domain import BaseDomain
from graph.base_graph_node import BaseGraphNode
from graph.qualified_name import cls_qualified_dotted_id

TDomain = TypeVar("TDomain", bound=BaseDomain)


@dataclass(init=False, frozen=True)
class DomainGraphNode(BaseGraphNode[type[TDomain]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a bounded-context domain marker.
    CONTRACT: Built from ``type[TDomain]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label; ``properties`` carry ``name`` / ``description`` (facet ``node_meta`` parity). ``edges`` is empty on the interchange row until an ``Application`` node exists in the same coordinator graph (facet layer still models ``belongs_to`` via ``ApplicationContextInspector``).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Domain"

    def __init__(self, domain_cls: type[TDomain]) -> None:
        super().__init__(
            node_id=cls_qualified_dotted_id(domain_cls),
            node_type=DomainGraphNode.NODE_TYPE,
            label=domain_cls.__name__,
            properties={
                "name": domain_cls.name,
                "description": domain_cls.description,
            },
            edges=[],
            node_obj=domain_cls,
        )
