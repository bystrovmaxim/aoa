# tests/runtime/test_role_checker.py
"""Unit tests for ``RoleChecker`` wired against a built ``NodeGraphCoordinator``."""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import Field

from action_machine.auth.any_role import AnyRole
from action_machine.auth.application_role import ApplicationRole
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.exceptions import AuthorizationError
from action_machine.graph_model.edges.role_graph_edge import RoleGraphEdge
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.graph_model.nodes.role_graph_node import RoleGraphNode
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.role_checker import RoleChecker
from action_machine.runtime.tools_box import ToolsBox
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode
from graph.create_node_graph_coordinator import create_node_graph_coordinator
from tests.scenarios.domain_model.admin_action import AdminAction
from tests.scenarios.domain_model.domains import SystemDomain
from tests.scenarios.domain_model.ping_action import PingAction
from tests.scenarios.domain_model.roles import AdminRole, EditorRole, SpyRole, UserRole
from tests.scenarios.intents_with_runtime.test_role_checker_pr2 import (
    OrderManagerRole,
    OrderViewerRole,
)

importlib.import_module("tests.scenarios.domain_model.full_action")


@pytest.fixture(scope="module")
def coordinator_module():
    return create_node_graph_coordinator()


def _action_node(coord, cls: type) -> ActionGraphNode:
    nid = TypeIntrospection.full_qualname(cls)
    raw = coord.get_node_by_id(nid, ActionGraphNode.NODE_TYPE)
    return raw  # type: ignore[return-value]


class _BadRoleGraphNode(RoleGraphNode):
    """Vertex with invalid ``node_obj`` for ``RoleChecker`` edge-shape tests."""

    def __init__(self) -> None:
        BaseGraphNode.__init__(
            self,
            node_id="tests.runtime.test_role_checker._BadRoleGraphNode",
            node_type=RoleGraphNode.NODE_TYPE,
            label="BadRoleGraphNode",
            node_obj="not-a-role-class",  # type: ignore[arg-type]
            properties={},
        )


class _BrokenRoleChecker(RoleChecker):
    """Forces defensive ``check`` fallback on an impossible reconstructed spec."""

    @classmethod
    def _check_roles_spec_from_action_edges(
        cls,
        action_node: ActionGraphNode[BaseAction],  # type: ignore[type-arg]
    ) -> object:
        return object()


def test_ping_none_role_allows_anonymous_context(coordinator_module) -> None:
    checker = RoleChecker()
    checker.check(Context(), _action_node(coordinator_module, PingAction))


def test_admin_denied_without_role(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    with pytest.raises(AuthorizationError, match="admin"):
        checker.check(ctx, _action_node(coordinator_module, AdminAction))


def test_admin_allowed_with_matching_role(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    checker.check(ctx, _action_node(coordinator_module, AdminAction))


@meta(description="OR semantics for RoleChecker", domain=SystemDomain)
@check_roles([EditorRole, SpyRole])
class OrRolesProbeAction(BaseAction["OrRolesProbeAction.Params", "OrRolesProbeAction.Result"]):
    class Params(BaseParams):
        dummy: str = Field(default="x", description="Probe param")

    class Result(BaseResult):
        ok: bool = Field(description="Probe result")

    @summary_aspect("Summary")
    async def or_roles_summary(
        self,
        params: OrRolesProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> OrRolesProbeAction.Result:
        return OrRolesProbeAction.Result(ok=True)


def test_or_roles_one_alternative_matches(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="s1", roles=(SpyRole,)))
    checker.check(ctx, _action_node(coordinator_module, OrRolesProbeAction))


def test_or_roles_none_match(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    with pytest.raises(AuthorizationError, match="one of"):
        checker.check(ctx, _action_node(coordinator_module, OrRolesProbeAction))


@meta(description="AnyRole sentinel", domain=SystemDomain)
@check_roles(AnyRole)
class AnyRoleProbeAction(BaseAction["AnyRoleProbeAction.Params", "AnyRoleProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def any_probe_summary(
        self,
        params: AnyRoleProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AnyRoleProbeAction.Result:
        return AnyRoleProbeAction.Result(ok=True)


def test_any_role_requires_nonempty_active_roles(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="anon", roles=()))
    with pytest.raises(AuthorizationError, match="Authentication required"):
        checker.check(ctx, _action_node(coordinator_module, AnyRoleProbeAction))


def test_any_role_allows_registered_role(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(UserRole,)))
    checker.check(ctx, _action_node(coordinator_module, AnyRoleProbeAction))


@meta(description="Subclass role suffices for base-role requirement", domain=SystemDomain)
@check_roles(OrderViewerRole)
class HierarchyRoleProbeAction(BaseAction["HierarchyRoleProbeAction.Params", "HierarchyRoleProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def hierarchy_probe_summary(
        self,
        params: HierarchyRoleProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> HierarchyRoleProbeAction.Result:
        return HierarchyRoleProbeAction.Result(ok=True)


def test_required_base_role_met_by_strict_subclass_user(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="m", roles=(OrderManagerRole,)))
    checker.check(ctx, _action_node(coordinator_module, HierarchyRoleProbeAction))


@role_mode(RoleMode.SILENCED)
class SilencedRole(ApplicationRole):
    name = "silenced"
    description = "Filtered from active role checks"


def test_silenced_roles_dropped_before_match(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(SilencedRole, AdminRole)))
    checker.check(ctx, _action_node(coordinator_module, AdminAction))


def test_only_silenced_roles_fail_admin(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(SilencedRole,)))
    with pytest.raises(AuthorizationError):
        checker.check(ctx, _action_node(coordinator_module, AdminAction))


def test_check_raises_when_action_has_no_role_edges() -> None:
    action_node = MagicMock()
    action_node.node_id = "tests.FakeAction"
    action_node.roles = []
    with pytest.raises(TypeError, match="@check_roles"):
        RoleChecker().check(Context(), action_node)


def test_spec_from_edges_rejects_non_role_targets() -> None:
    unwired_edge = RoleGraphEdge(role_cls=AdminRole)
    action_node = SimpleNamespace(node_id="a.X", roles=[unwired_edge])
    with pytest.raises(TypeError, match="Role interchange row"):
        RoleChecker._check_roles_spec_from_action_edges(action_node)


def test_spec_from_edges_rejects_invalid_role_vertex_payload() -> None:
    edge = SimpleNamespace(target_node=_BadRoleGraphNode())
    action_node = SimpleNamespace(node_id="a.Y", roles=[edge])
    with pytest.raises(TypeError, match="invalid node_obj"):
        RoleChecker._check_roles_spec_from_action_edges(action_node)


def test_check_invalid_reconstructed_spec_type_error(coordinator_module) -> None:
    ctx = Context(user=UserInfo(user_id="u", roles=(AdminRole,)))
    with pytest.raises(TypeError, match="Invalid reconstructed"):
        _BrokenRoleChecker().check(ctx, _action_node(coordinator_module, PingAction))
