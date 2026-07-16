"""RoleGraphEdge.get_role_edges — one edge per grant, carrying when= (access-control-cascade step 4)."""

from __future__ import annotations

from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.graph.edges.role_graph_edge import RoleGraphEdge
from aoa.action_machine.intents.check_roles.check_roles_decorator import check_roles
from aoa.action_machine.intents.check_roles.grant import grant

from ....support.domain_model.roles import AdminRole, ManagerRole


def _sales_only(user: object) -> bool:
    return True


def test_bare_role_edge_has_no_when() -> None:
    @check_roles(AdminRole)
    class _Action:
        pass

    edges = RoleGraphEdge.get_role_edges(_Action)
    assert len(edges) == 1
    assert edges[0].target_node_id.endswith("AdminRole")
    assert edges[0].properties["when"] is None


def test_one_edge_per_grant_carries_its_own_when() -> None:
    @check_roles(grant(AdminRole), grant(ManagerRole, when=_sales_only))
    class _Action:
        pass

    edges = RoleGraphEdge.get_role_edges(_Action)
    assert len(edges) == 2
    assert edges[0].properties["when"] is None
    assert edges[1].properties["when"] is _sales_only


def test_sentinel_role_still_gets_exactly_one_edge() -> None:
    """Regression guard: RoleChecker treats an empty ``action_node.roles`` as
    "no @check_roles decorator at all" — GuestRole/AnyRole must still produce one edge."""

    @check_roles(GuestRole)
    class _Action:
        pass

    edges = RoleGraphEdge.get_role_edges(_Action)
    assert len(edges) == 1
    assert edges[0].properties["when"] is None


def test_to_dict_never_exports_when() -> None:
    """``when`` is runtime-only, like ``DependsGraphEdge``'s ``factory`` — never serialized."""

    @check_roles(grant(AdminRole, when=_sales_only))
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
