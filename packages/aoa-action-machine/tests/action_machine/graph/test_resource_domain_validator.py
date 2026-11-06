# tests/action_machine/graph/test_resource_domain_validator.py
"""
An action uses only resources of its own domain, through ``@depends`` or ``@connection``.

The validator reads the graph's nodes: an action node, its ``@depends`` / ``@connection``
edges, and the resource nodes they reach. Nodes are hand-built over real classes; every
class declared here is excluded from the graph model.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.exceptions.dependency_declaration_error import DependencyDeclarationError
from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.validators.resource_domain_validator import validate_resource_domains
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources import BaseStorage

from ...support.domain_model.domains import OrdersDomain, SystemDomain


@exclude_graph_model
@meta(description="Places an order", domain=OrdersDomain)
class _PlaceOrderAction(BaseAction):  # type: ignore[type-arg]
    pass


@exclude_graph_model
@meta(description="Orders", domain=OrdersDomain)
class _OrdersStore(BaseStorage):  # type: ignore[type-arg]
    def get_wrapper_class(self) -> None:
        return None


@exclude_graph_model
@meta(description="Audit log", domain=SystemDomain)
class _AuditStore(BaseStorage):  # type: ignore[type-arg]
    def get_wrapper_class(self) -> None:
        return None


class _Use(AssociationGraphEdge):
    def __init__(self, edge_name: str, target_id: str) -> None:
        super().__init__(edge_name=edge_name, is_dag=True, target_node_id=target_id, target_node=None)

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {"source_id": source_id, "target_id": self.target_node_id, "type": self.edge_name, "properties": {}}


class _Node(BaseGraphNode[object]):
    def __init__(self, host: type, edges: list[BaseGraphEdge] | None = None) -> None:
        super().__init__(node_id=host.__name__, node_type="X", label=host.__name__, properties={}, node_obj=host)
        object.__setattr__(self, "_edges", edges or [])

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return list(self._edges)


def _nodes(edge_name: str, resource: type) -> list[_Node]:
    return [_Node(_PlaceOrderAction, [_Use(edge_name, resource.__name__)]), _Node(_OrdersStore), _Node(_AuditStore)]


@pytest.mark.parametrize("edge_name", ["@depends", "@connection"])
def test_a_resource_of_the_action_domain_is_used(edge_name: str) -> None:
    validate_resource_domains(_nodes(edge_name, _OrdersStore))


@pytest.mark.parametrize("edge_name", ["@depends", "@connection"])
def test_a_resource_of_another_domain_is_refused(edge_name: str) -> None:
    with pytest.raises(DependencyDeclarationError) as error:
        validate_resource_domains(_nodes(edge_name, _AuditStore))
    assert str(error.value) == (
        f"_PlaceOrderAction (OrdersDomain) uses _AuditStore (SystemDomain) through {edge_name}: an action uses only "
        "resources of its own domain; reach another domain through its actions."
    )
