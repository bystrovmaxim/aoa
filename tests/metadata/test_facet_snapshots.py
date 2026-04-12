"""Tests for BaseFacetSnapshot + GateCoordinator facet snapshot cache."""

from __future__ import annotations

from action_machine.auth.check_roles import check_roles
from action_machine.auth.role_gate_host_inspector import RoleGateHostInspector
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.core.meta_decorator import meta
from action_machine.core.meta_gate_host_inspector import MetaGateHostInspector
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.domain.base_domain import BaseDomain
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from tests.domain_model.roles import AdminRole


@check_roles(AdminRole)
class _SnapProbeAction(BaseAction[BaseParams, BaseResult]):
    """Concrete action with @check_roles for snapshot tests."""

    pass


def test_role_facet_snapshot_round_trip_with_graph() -> None:
    coord = CoreActionMachine.create_coordinator()

    snap = coord.get_snapshot(_SnapProbeAction, "role")
    assert snap is not None
    assert isinstance(snap, RoleGateHostInspector.Snapshot)
    assert snap.class_ref is _SnapProbeAction
    assert snap.spec is AdminRole

    payload = snap.to_facet_payload()
    assert payload.node_type == "role"
    assert payload.node_class is _SnapProbeAction
    assert dict(payload.node_meta)["spec"] is AdminRole

    role_name = BaseGateHostInspector._make_node_name(_SnapProbeAction)
    role_node = coord.get_node("role", role_name)
    assert role_node is not None
    meta = role_node.get("meta")
    assert meta is not None
    assert meta.get("spec") is AdminRole


class _FacetOrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders domain"


@meta(description="Meta facet probe", domain=_FacetOrdersDomain)
class _MetaFacetProbe(ActionMetaGateHost):
    pass


def test_meta_facet_snapshot_matches_inspect_payload() -> None:
    coord = CoreActionMachine.create_coordinator()

    snap = coord.get_snapshot(_MetaFacetProbe, "meta")
    assert snap is not None
    assert isinstance(snap, MetaGateHostInspector.Snapshot)
    assert snap.class_ref is _MetaFacetProbe
    assert snap.description == "Meta facet probe"
    assert snap.domain is _FacetOrdersDomain

    from_payload = snap.to_facet_payload()
    from_inspect = MetaGateHostInspector.inspect(_MetaFacetProbe)
    assert from_inspect is not None
    assert from_payload.node_type == from_inspect.node_type
    assert from_payload.node_name == from_inspect.node_name
    assert from_payload.node_class is from_inspect.node_class
    assert from_payload.node_meta == from_inspect.node_meta
    assert len(from_payload.edges) == len(from_inspect.edges) == 1


def test_no_snapshot_for_class_without_check_roles() -> None:
    class _NoRoleAction(BaseAction[BaseParams, BaseResult]):
        pass

    coord = CoreActionMachine.create_coordinator()
    assert coord.get_snapshot(_NoRoleAction, "role") is None
