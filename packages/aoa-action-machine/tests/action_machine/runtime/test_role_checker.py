# tests/runtime/test_role_checker.py
"""Unit tests for ``RoleChecker`` wired against a built ``NodeGraphCoordinator``."""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import Field

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.role_graph_edge import RoleGraphEdge
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.graph.nodes.role_graph_node import RoleGraphNode
from aoa.action_machine.intents.access_control import FailSecurityVerdict
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.role_checker import RoleChecker
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core import TypeIntrospection

from ...action_machine.scenarios.intents_with_runtime.test_role_checker_pr2 import OrderManagerRole, OrderViewerRole
from ...support.domain_model.admin_action import AdminAction
from ...support.domain_model.domains import SystemDomain
from ...support.domain_model.ping_action import PingAction
from ...support.domain_model.roles import AdminRole, EditorRole, ManagerRole, SpyRole, UserRole

importlib.import_module("tests.support.domain_model.full_action")


@pytest.fixture(scope="module")
def coordinator_module():
    return create_node_graph_coordinator()


def _action_node(coord, cls: type) -> ActionGraphNode:
    nid = TypeIntrospection.full_qualname(cls)
    raw = coord.get_node_by_id(nid, ActionGraphNode.NODE_TYPE)
    return raw  # type: ignore[return-value]


class _BadRoleGraphNode(RoleGraphNode):
    """Graph node stub with invalid ``node_obj`` for ``RoleChecker`` edge-shape tests."""

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


def test_spec_from_edges_rejects_invalid_role_graph_node_payload() -> None:
    edge = SimpleNamespace(target_node=_BadRoleGraphNode())
    action_node = SimpleNamespace(node_id="a.Y", roles=[edge])
    with pytest.raises(TypeError, match="invalid node_obj"):
        RoleChecker._check_roles_spec_from_action_edges(action_node)


def test_check_invalid_reconstructed_spec_type_error(coordinator_module) -> None:
    ctx = Context(user=UserInfo(user_id="u", roles=(AdminRole,)))
    with pytest.raises(TypeError, match="Invalid reconstructed"):
        _BrokenRoleChecker().check(ctx, _action_node(coordinator_module, PingAction))


def _is_sales_agent(user) -> bool:
    return user.user_id == "sales_agent"


def _order_not_archived(user, params) -> bool:
    return not params.order_id.startswith("ARCHIVED-")


@meta(description="grant()/guard= probe for RoleChecker level 2", domain=SystemDomain)
@check_roles(
    grant(AdminRole),
    grant(ManagerRole, when=_is_sales_agent, reason=FailSecurityVerdict("not the sales agent")),
    guard=_order_not_archived,
    reason=FailSecurityVerdict("order archived"),
)
class GrantGuardProbeAction(BaseAction["GrantGuardProbeAction.Params", "GrantGuardProbeAction.Result"]):
    class Params(BaseParams):
        order_id: str = Field(default="ORD-1")

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: GrantGuardProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GrantGuardProbeAction.Result:
        return GrantGuardProbeAction.Result(ok=True)


def test_denied_without_any_role_match_sets_level_1(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    with pytest.raises(AuthorizationError) as excinfo:
        checker.check(ctx, _action_node(coordinator_module, GrantGuardProbeAction), GrantGuardProbeAction.Params())
    assert excinfo.value.level == 1
    assert excinfo.value.reason == "FORBIDDEN_ROLE"


def test_bare_grant_matches_unconditionally(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    checker.check(ctx, _action_node(coordinator_module, GrantGuardProbeAction), GrantGuardProbeAction.Params())


def test_grant_when_false_falls_through_to_level_2(coordinator_module) -> None:
    """ManagerRole matches structurally, but when= rejects (wrong user_id); no other
    grant matches a ManagerRole-only user, so this is a level-2, not level-1, denial."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="not_sales", roles=(ManagerRole,)))
    with pytest.raises(AuthorizationError) as excinfo:
        checker.check(ctx, _action_node(coordinator_module, GrantGuardProbeAction), GrantGuardProbeAction.Params())
    assert excinfo.value.level == 2
    assert excinfo.value.reason == "not the sales agent"


def test_grant_when_true_allows_a_later_grant_to_win(coordinator_module) -> None:
    """The first grant (AdminRole, unconditional) does not match this user — the second
    grant (ManagerRole + when=) is tried next and wins. Proves any()/declaration order."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="sales_agent", roles=(ManagerRole,)))
    checker.check(ctx, _action_node(coordinator_module, GrantGuardProbeAction), GrantGuardProbeAction.Params())


def test_guard_false_denies_with_level_2(coordinator_module) -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    with pytest.raises(AuthorizationError) as excinfo:
        checker.check(
            ctx,
            _action_node(coordinator_module, GrantGuardProbeAction),
            GrantGuardProbeAction.Params(order_id="ARCHIVED-1"),
        )
    assert excinfo.value.level == 2
    assert excinfo.value.reason == "order archived"


def test_check_without_params_still_works_when_action_has_no_guard(coordinator_module) -> None:
    """Existing call shape ``check(context, action_node)`` — no params — must keep working
    for actions with no guard= (guard is None, never called, so a missing params is fine)."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    checker.check(ctx, _action_node(coordinator_module, AdminAction))


def _always_false(user) -> bool:
    return False


@meta(description="GuestRole grant with its own when= probe", domain=SystemDomain)
@check_roles(grant(GuestRole, when=_always_false, reason=FailSecurityVerdict("guest when rejected")))
class GuestWhenProbeAction(BaseAction["GuestWhenProbeAction.Params", "GuestWhenProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: GuestWhenProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GuestWhenProbeAction.Result:
        return GuestWhenProbeAction.Result(ok=True)


def test_guest_role_grant_when_false_denies_with_level_2(coordinator_module) -> None:
    """Regression: `grant(GuestRole, when=...)` is a valid declaration (GuestRole is an
    ordinary BaseRole subclass as far as grant() is concerned) — its when= must not be
    silently ignored just because GuestRole normally bypasses role matching entirely."""
    checker = RoleChecker()
    with pytest.raises(AuthorizationError) as excinfo:
        checker.check(Context(), _action_node(coordinator_module, GuestWhenProbeAction))
    assert excinfo.value.level == 2
    assert excinfo.value.reason == "guest when rejected"


@meta(description="AnyRole grant with its own when= probe", domain=SystemDomain)
@check_roles(grant(AnyRole, when=_always_false, reason=FailSecurityVerdict("any-role when rejected")))
class AnyWhenProbeAction(BaseAction["AnyWhenProbeAction.Params", "AnyWhenProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: AnyWhenProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AnyWhenProbeAction.Result:
        return AnyWhenProbeAction.Result(ok=True)


def test_any_role_grant_when_false_denies_with_level_2(coordinator_module) -> None:
    """Same regression as above, for AnyRole: at least one active role is present
    (AnyRole's own gate passes), but the grant's own when= must still be honored."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(UserRole,)))
    with pytest.raises(AuthorizationError) as excinfo:
        checker.check(ctx, _action_node(coordinator_module, AnyWhenProbeAction))
    assert excinfo.value.level == 2
    assert excinfo.value.reason == "any-role when rejected"
