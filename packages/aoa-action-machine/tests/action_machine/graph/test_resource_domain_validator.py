# tests/action_machine/graph/test_resource_domain_validator.py
"""
An action depends only on resources of its own domain; a connection the caller hands over is not judged.

The validator reads the graph's nodes: an action node, its ``@depends`` and ``@connection``
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
class _OrdersStoreStorage(BaseStorage):  # type: ignore[type-arg]
    @classmethod
    def get_wrapper_class(cls) -> None:
        return None


@exclude_graph_model
@meta(description="Audit log", domain=SystemDomain)
class _AuditStoreStorage(BaseStorage):  # type: ignore[type-arg]
    @classmethod
    def get_wrapper_class(cls) -> None:
        return None


class _UseGraphEdge(AssociationGraphEdge):
    def __init__(self, edge_name: str, target_id: str) -> None:
        super().__init__(edge_name=edge_name, is_dag=True, target_node_id=target_id, target_node=None)

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        return {"source_id": source_id, "target_id": self.target_node_id, "type": self.edge_name, "properties": {}}


class _TestGraphNode(BaseGraphNode[object]):
    def __init__(self, host: type, edges: list[BaseGraphEdge] | None = None) -> None:
        super().__init__(node_id=host.__name__, node_type="X", label=host.__name__, properties={}, node_obj=host)
        object.__setattr__(self, "_edges", edges or [])

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return list(self._edges)


def _nodes(edge_name: str, resource: type) -> list[_TestGraphNode]:
    return [_TestGraphNode(_PlaceOrderAction, [_UseGraphEdge(edge_name, resource.__name__)]), _TestGraphNode(_OrdersStoreStorage), _TestGraphNode(_AuditStoreStorage)]


@pytest.mark.parametrize("edge_name", ["@depends", "@connection"])
def test_a_resource_of_the_action_domain_is_used(edge_name: str) -> None:
    validate_resource_domains(_nodes(edge_name, _OrdersStoreStorage))


def test_a_dependency_on_a_resource_of_another_domain_is_refused() -> None:
    with pytest.raises(DependencyDeclarationError) as error:
        validate_resource_domains(_nodes("@depends", _AuditStoreStorage))
    assert str(error.value) == (
        "_PlaceOrderAction (OrdersDomain) uses _AuditStoreStorage (SystemDomain) through @depends: an action uses only "
        "resources of its own domain; reach another domain through its actions."
    )


def test_a_connection_handed_over_from_another_domain_is_not_judged() -> None:
    """A transport's socket channel is a connection the caller hands over, whatever its domain."""
    validate_resource_domains(_nodes("@connection", _AuditStoreStorage))
