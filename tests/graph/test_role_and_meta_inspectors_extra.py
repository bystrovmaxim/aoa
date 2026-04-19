"""Extra tests for role/meta inspectors with low coverage."""

from __future__ import annotations

from action_machine.graph.facet_edge import FacetEdge
from action_machine.auth.application_role import ApplicationRole
from action_machine.auth.base_role import BaseRole
from action_machine.legacy.check_roles_intent import CheckRolesIntent
from action_machine.legacy.role_intent_inspector import RoleIntentInspector
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from action_machine.intents.meta.meta_intent_inspector import MetaIntentInspector
from action_machine.intents.meta.action_meta_intent import ActionMetaIntent


@role_mode(RoleMode.ALIVE)
class _InspectFixtureRole(BaseRole):
    """Minimal assignable role for RoleIntentInspector branch coverage."""

    name = "inspect_fixture"
    description = "Fixture role for inspector tests."


class _RoleMissing(CheckRolesIntent):
    pass


class _RoleFilled(CheckRolesIntent):
    _role_info = {"spec": _InspectFixtureRole}


class _MetaMissing(ActionMetaIntent):
    pass


class _MetaFilled(ActionMetaIntent):
    _meta_info = {"description": "desc", "domain": None}


def test_role_intent_inspector_branches() -> None:
    assert RoleIntentInspector.inspect(_RoleMissing) is None
    payload = RoleIntentInspector.inspect(_RoleFilled)
    assert payload is not None
    assert payload.node_type == "Action"
    assert dict(payload.node_meta)["spec"] is _InspectFixtureRole
    assert any(
        isinstance(e, FacetEdge)
        and e.edge_type == "requires_role"
        and e.target_node_type == "role_class"
        and e.target_class_ref is ApplicationRole
        for e in payload.edges
    )
    assert isinstance(RoleIntentInspector._subclasses_recursive(), list)


def test_meta_intent_inspector_branches() -> None:
    assert MetaIntentInspector.inspect(_MetaMissing) is None
    payload = MetaIntentInspector.inspect(_MetaFilled)
    assert payload is not None
    assert payload.node_type == "meta"
    assert dict(payload.node_meta)["description"] == "desc"
    assert MetaIntentInspector._has_domain_invariant(_MetaFilled) is False
