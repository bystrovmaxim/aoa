"""RoleGraphEdge.get_role_edges — one edge per distinct role, with no condition data."""

from __future__ import annotations

from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.graph.edges.role_graph_edge import RoleGraphEdge
from aoa.action_machine.intents.check_roles.check_roles_decorator import check_roles

from ....support.domain_model.roles import AdminRole, ManagerRole


def test_a_bare_role_yields_one_edge_with_empty_properties() -> None:
    @check_roles(AdminRole)
    class _Action:
        pass

    edges = RoleGraphEdge.get_role_edges(_Action)
    assert len(edges) == 1
    assert edges[0].target_node_id.endswith("AdminRole")
    assert edges[0].properties == {}


def test_several_positional_roles_yield_one_edge_each_in_order() -> None:
    @check_roles(AdminRole, ManagerRole)
    class _Action:
        pass

    edges = RoleGraphEdge.get_role_edges(_Action)
    assert [edge.target_node_id.split(".")[-1] for edge in edges] == ["AdminRole", "ManagerRole"]


def test_a_role_named_twice_yields_one_edge() -> None:
    @check_roles(AdminRole, AdminRole)
    class _Action:
        pass

    edges = RoleGraphEdge.get_role_edges(_Action)
    assert len(edges) == 1
    assert edges[0].target_node_id.endswith("AdminRole")


def test_a_sentinel_still_gets_exactly_one_edge() -> None:
    @check_roles(GuestRole)
    class _Action:
        pass

    edges = RoleGraphEdge.get_role_edges(_Action)
    assert len(edges) == 1
    assert edges[0].target_node_id.endswith("GuestRole")
    assert edges[0].properties == {}


def test_to_dict_exports_an_empty_properties_map() -> None:
    @check_roles(AdminRole)
    class _Action:
        pass

    edge = RoleGraphEdge.get_role_edges(_Action)[0]
    assert edge.to_dict(source_id="tests.X") == {
        "source_id": "tests.X",
        "target_id": edge.target_node_id,
        "type": "@check_roles",
        "relationship": edge.edge_relationship.archimate_name,
        "is_dag": False,
        "properties": {},
    }
