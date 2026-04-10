# tests/metadata/test_new_inspectors_core.py
"""
Unit tests for newly introduced graph inspectors in metadata migration.

Covered inspectors:
- MetaGateHostInspector
- DependencyGateHostInspector
- ConnectionGateHostInspector

The tests verify inspector-local behavior only:
- returns None when source metadata is missing
- returns payload when source metadata exists
- edge shape and structural flags match the migration contract

These tests do not validate full coordinator integration yet; they keep scope
small and deterministic for inspector units.
"""

from __future__ import annotations

from action_machine.core.meta_decorator import meta
from action_machine.core.meta_gate_host_inspector import MetaGateHostInspector
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.dependencies.dependency_gate_host_inspector import (
    DependencyGateHostInspector,
)
from action_machine.dependencies.depends import depends
from action_machine.domain.base_domain import BaseDomain
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.resource_managers.connection import connection
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost
from action_machine.resource_managers.connection_gate_host_inspector import (
    ConnectionGateHostInspector,
)


class _OrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders domain"


@meta(description="Meta with domain", domain=_OrdersDomain)
class _MetaWithDomain(ActionMetaGateHost):
    pass


@meta(description="Meta without domain")
class _MetaNoDomain(ActionMetaGateHost):
    pass


class _MetaMissing(ActionMetaGateHost):
    pass


class _ServiceA:
    pass


class _ServiceB:
    pass


@depends(_ServiceA, description="a")
@depends(_ServiceB, description="b")
class _DependsAction(DependencyGateHost[object]):
    pass


class _NoDependsAction(DependencyGateHost[object]):
    pass


class _DbManager(BaseResourceManager):
    def get_wrapper_class(self):
        return None


@connection(_DbManager, key="db", description="primary")
class _ConnectionAction(ConnectionGateHost):
    pass


class _NoConnectionAction(ConnectionGateHost):
    pass


@depends(_ServiceA, description="svc")
@connection(_DbManager, key="db", description="primary")
class _DependsAndConnectionAction(DependencyGateHost[object], ConnectionGateHost):
    pass


def test_meta_inspector_returns_none_without_meta() -> None:
    assert MetaGateHostInspector.inspect(_MetaMissing) is None


def test_meta_inspector_builds_payload_with_domain_edge() -> None:
    payload = MetaGateHostInspector.inspect(_MetaWithDomain)
    assert payload is not None
    assert payload.node_type == "meta"
    assert dict(payload.node_meta)["description"] == "Meta with domain"
    assert len(payload.edges) == 1
    assert payload.edges[0].edge_type == "belongs_to"
    assert payload.edges[0].is_structural is False


def test_meta_inspector_builds_payload_without_domain_edge() -> None:
    payload = MetaGateHostInspector.inspect(_MetaNoDomain)
    assert payload is not None
    assert payload.edges == ()


def test_dependency_inspector_returns_none_without_depends() -> None:
    assert DependencyGateHostInspector.inspect(_NoDependsAction) is None


def test_dependency_inspector_builds_structural_depends_edges() -> None:
    payload = DependencyGateHostInspector.inspect(_DependsAction)
    assert payload is not None
    assert payload.node_type == "action"
    assert len(payload.edges) == 2
    assert all(edge.edge_type == "depends" for edge in payload.edges)
    assert all(edge.is_structural is True for edge in payload.edges)


def test_connection_inspector_returns_none_without_connections() -> None:
    assert ConnectionGateHostInspector.inspect(_NoConnectionAction) is None


def test_connection_inspector_builds_structural_connection_edge() -> None:
    payload = ConnectionGateHostInspector.inspect(_ConnectionAction)
    assert payload is not None
    assert payload.node_type == "action"
    assert len(payload.edges) == 1
    edge = payload.edges[0]
    assert edge.edge_type == "connection"
    assert edge.is_structural is True
    assert dict(edge.edge_meta)["key"] == "db"


def test_coordinator_merges_action_payloads_from_dependency_and_connection() -> None:
    coord = (
        GateCoordinator()
        .register(DependencyGateHostInspector)
        .register(ConnectionGateHostInspector)
        .build()
    )
    action_nodes = [n for n in coord.get_nodes_for_class(_DependsAndConnectionAction) if n.get("node_type") == "action"]
    assert len(action_nodes) == 1
    # committed graph stores edges separately; check via graph API if needed
    keys = coord._class_index.get(_DependsAndConnectionAction, [])  # pylint: disable=protected-access
    assert len(keys) == 1
    idx = coord._node_index[keys[0]]  # pylint: disable=protected-access
    out_edges = coord._graph.out_edges(idx)  # pylint: disable=protected-access
    assert len(out_edges) == 2
