"""Tests for BaseFacetSnapshot + GraphCoordinator facet snapshot cache."""

from __future__ import annotations

from pydantic import Field

from action_machine.domain.base_domain import BaseDomain
from action_machine.intents.check_roles.check_roles_decorator import check_roles
from action_machine.intents.meta.action_meta_intent import ActionMetaIntent
from action_machine.intents.meta.meta_decorator import meta
from action_machine.legacy.core import Core
from action_machine.legacy.meta_intent_inspector import MetaIntentInspector
from action_machine.legacy.role_intent_inspector import RoleIntentInspector
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from graph.base_intent_inspector import BaseIntentInspector
from tests.scenarios.domain_model.roles import AdminRole


class _SnapProbeParams(BaseParams):
    token: str = Field(default="snap", description="Snapshot probe params")


class _SnapProbeResult(BaseResult):
    ok: bool = Field(default=True, description="Snapshot probe result")


@check_roles(AdminRole)
class _SnapProbeAction(BaseAction[_SnapProbeParams, _SnapProbeResult]):
    """Concrete action with @check_roles for snapshot tests."""

    pass


def test_role_facet_snapshot_round_trip_with_graph() -> None:
    coord = Core.create_coordinator()

    snap = coord.get_snapshot(_SnapProbeAction, "role")
    assert snap is not None
    assert isinstance(snap, RoleIntentInspector.Snapshot)
    assert snap.class_ref is _SnapProbeAction
    assert snap.spec is AdminRole

    payload = snap.to_facet_vertex()
    assert payload.node_type == "Action"
    assert payload.node_class is _SnapProbeAction
    assert dict(payload.node_meta)["spec"] is AdminRole

    action_name = BaseIntentInspector._make_node_name(_SnapProbeAction)
    action_node = coord.get_node("Action", action_name)
    assert action_node is not None
    rows = action_node.get("facet_rows")
    assert rows is not None
    assert rows.get("spec") is AdminRole


class _FacetOrdersDomain(BaseDomain):
    name = "orders"
    description = "Orders domain"


@meta(description="Meta facet probe", domain=_FacetOrdersDomain)
class _MetaFacetProbe(ActionMetaIntent):
    pass


def test_meta_facet_snapshot_matches_inspect_payload() -> None:
    coord = Core.create_coordinator()

    snap = coord.get_snapshot(_MetaFacetProbe, "meta")
    assert snap is not None
    assert isinstance(snap, MetaIntentInspector.Snapshot)
    assert snap.class_ref is _MetaFacetProbe
    assert snap.description == "Meta facet probe"
    assert snap.domain is _FacetOrdersDomain

    from_payload = snap.to_facet_vertex()
    from_inspect = MetaIntentInspector.inspect(_MetaFacetProbe)
    assert from_inspect is not None
    assert from_payload.node_type == from_inspect.node_type
    assert from_payload.node_name == from_inspect.node_name
    assert from_payload.node_class is from_inspect.node_class
    assert from_payload.node_meta == from_inspect.node_meta
    assert len(from_payload.edges) == len(from_inspect.edges) == 1


def test_no_snapshot_for_class_without_check_roles() -> None:
    class _NoRoleAction(BaseAction[BaseParams, BaseResult]):
        pass

    coord = Core.create_coordinator()
    assert coord.get_snapshot(_NoRoleAction, "role") is None
