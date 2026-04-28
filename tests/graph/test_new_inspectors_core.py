# tests/graph/test_new_inspectors_core.py
"""
Unit tests for newly introduced graph inspectors in metadata migration.

Covered inspectors:
- MetaIntentInspector
- DependencyIntentInspector

The tests verify inspector-local behavior only:
- returns None when source metadata is missing
- returns payload when source metadata exists
- edge shape and structural flags match the migration contract

These tests do not validate full coordinator integration yet; they keep scope
small and deterministic for inspector units.
"""

from __future__ import annotations

import pytest

from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.connection import connection
from action_machine.intents.connection.connection_intent import ConnectionIntent
from action_machine.intents.depends import depends
from action_machine.intents.depends.depends_intent import DependsIntent
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.meta.meta_intent import MetaIntent
from action_machine.legacy.dependency_intent_inspector import DependencyIntentInspector
from action_machine.legacy.meta_intent_inspector import MetaIntentInspector
from action_machine.resources.base_resource import BaseResource
from graph.graph_coordinator import GraphCoordinator


class _OrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders domain"


@meta(description="Meta with domain", domain=_OrdersDomain)
class _MetaWithDomain(MetaIntent):
    pass


class _MetaMissing(MetaIntent):
    pass


class _ServiceA:
    pass


class _ServiceB:
    pass


@depends(_ServiceA, description="a")
@depends(_ServiceB, description="b")
class _DependsAction(DependsIntent[object]):
    pass


class _NoDependsAction(DependsIntent[object]):
    pass


class _DbManager(BaseResource):
    def get_wrapper_class(self):
        return None


@depends(_ServiceA, description="svc")
@connection(_DbManager, key="db", description="primary")
class _DependsAndConnectionAction(DependsIntent[object], ConnectionIntent):
    pass


def test_meta_inspector_returns_none_without_meta() -> None:
    assert MetaIntentInspector.inspect(_MetaMissing) is None


def test_meta_inspector_builds_payload_with_domain_edge() -> None:
    payload = MetaIntentInspector.inspect(_MetaWithDomain)
    assert payload is not None
    assert payload.node_type == "meta"
    assert dict(payload.node_meta)["description"] == "Meta with domain"
    assert len(payload.edges) == 1
    assert payload.edges[0].edge_type == "belongs_to"
    assert payload.edges[0].is_structural is False


def test_meta_decorator_requires_domain_keyword() -> None:
    with pytest.raises(TypeError, match="domain"):
        meta("no domain argument")


def test_dependency_inspector_returns_none_without_depends() -> None:
    assert DependencyIntentInspector.inspect(_NoDependsAction) is None


def test_dependency_inspector_builds_structural_depends_edges() -> None:
    payload = DependencyIntentInspector.inspect(_DependsAction)
    assert payload is not None
    assert payload.node_type == "Action"
    assert len(payload.edges) == 2
    assert all(edge.edge_type == "depends" for edge in payload.edges)
    assert all(edge.is_structural is True for edge in payload.edges)


def test_coordinator_merged_action_node_carries_depends_only_without_connection_inspector() -> None:
    """Without a connection inspector, only ``@depends`` contributes out-edges on the facet graph."""
    coord = GraphCoordinator().register(DependencyIntentInspector).build()
    action_nodes = [
        n for n in coord.get_nodes_for_class(_DependsAndConnectionAction) if n.get("node_type") == "Action"
    ]
    assert len(action_nodes) == 1
    keys = coord._class_index.get(_DependsAndConnectionAction, [])  # pylint: disable=protected-access
    assert len(keys) == 1
    idx = coord._node_index[keys[0]]  # pylint: disable=protected-access
    out_edges = coord._facet_graph.out_edges(idx)  # pylint: disable=protected-access
    assert len(out_edges) == 1
