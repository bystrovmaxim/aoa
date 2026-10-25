# tests/action_machine/intents/access_control/test_roles.py
"""Unit tests for ``RoleChecker`` — it answers, and the cascade asks it.

The checker never raises for a decision: it returns ``Refused`` naming
``CHECK_ROLES``, and ``None`` when the caller may continue. It reads the single
``spec`` ``@check_roles`` wrote rather than the assembled graph, so these tests
hand it an action class. A sentinel keeps the meaning it has alone: ``GuestRole``
among the alternatives opens the declaration, ``AnyRole`` among them requires at
least one role that is not silenced.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import MissingCheckRolesError
from aoa.action_machine.intents.access_control import Gate, Refused
from aoa.action_machine.intents.access_control.roles import RoleChecker
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....action_machine.scenarios.intents_with_runtime.test_role_checker_pr2 import OrderManagerRole, OrderViewerRole
from ....support.domain_model.admin_action import AdminAction
from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.ping_action import PingAction
from ....support.domain_model.roles import AdminRole, EditorRole, SpyRole, UserRole


def test_ping_none_role_allows_anonymous_context() -> None:
    checker = RoleChecker()
    assert checker.check(Context(), PingAction) is None


def test_admin_answered_check_roles_without_the_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    answer = checker.check(ctx, AdminAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_admin_allowed_with_matching_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    assert checker.check(ctx, AdminAction) is None


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
        connections: Connections,
    ) -> OrRolesProbeAction.Result:
        return OrRolesProbeAction.Result(ok=True)


def test_or_roles_one_alternative_matches() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="s1", roles=(SpyRole,)))
    assert checker.check(ctx, OrRolesProbeAction) is None


def test_or_roles_none_match() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    answer = checker.check(ctx, OrRolesProbeAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


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
        connections: Connections,
    ) -> AnyRoleProbeAction.Result:
        return AnyRoleProbeAction.Result(ok=True)


def test_any_role_requires_at_least_one_active_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="anon", roles=()))
    answer = checker.check(ctx, AnyRoleProbeAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_any_role_allows_registered_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(UserRole,)))
    assert checker.check(ctx, AnyRoleProbeAction) is None


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
        connections: Connections,
    ) -> HierarchyRoleProbeAction.Result:
        return HierarchyRoleProbeAction.Result(ok=True)


def test_required_base_role_met_by_strict_subclass_user() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="m", roles=(OrderManagerRole,)))
    assert checker.check(ctx, HierarchyRoleProbeAction) is None


@role_mode(RoleMode.SILENCED)
class SilencedRole(ApplicationRole):
    name = "silenced"
    description = "Filtered from active role checks"


def test_silenced_roles_dropped_before_match() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(SilencedRole, AdminRole)))
    assert checker.check(ctx, AdminAction) is None


def test_only_silenced_roles_fail_admin() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(SilencedRole,)))
    answer = checker.check(ctx, AdminAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_check_raises_when_the_action_declares_no_roles() -> None:
    """A declaration the checker cannot read is a build-time mistake, not an answer."""

    class UndeclaredProbe:
        """A class with no ``@check_roles`` declaration at all."""

    with pytest.raises(MissingCheckRolesError, match="@check_roles"):
        RoleChecker().check(Context(), UndeclaredProbe)  # type: ignore[arg-type]


# --- the matching contract of FR-013: a sentinel beside ordinary roles keeps its meaning ---


@check_roles(GuestRole, AdminRole)
class GuestBesideRoleProbe:
    pass


def test_guest_beside_role_allows_anonymous_caller() -> None:
    assert RoleChecker().check(Context(), GuestBesideRoleProbe) is None


def test_guest_beside_role_allows_registered_caller() -> None:
    ctx = Context(user=UserInfo(user_id="u", roles=(UserRole,)))
    assert RoleChecker().check(ctx, GuestBesideRoleProbe) is None


@check_roles(AnyRole, AdminRole)
class AnyBesideRoleProbe:
    pass


def test_any_beside_role_requires_an_active_role() -> None:
    answer = RoleChecker().check(Context(), AnyBesideRoleProbe)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_any_beside_role_allows_an_active_role() -> None:
    ctx = Context(user=UserInfo(user_id="u", roles=(UserRole,)))
    assert RoleChecker().check(ctx, AnyBesideRoleProbe) is None


@check_roles(AdminRole, AdminRole)
class DuplicateRoleProbe:
    pass


def test_duplicate_role_collapses_to_a_single_spec() -> None:
    assert DuplicateRoleProbe._role_info["spec"] is AdminRole


def test_duplicate_role_still_matches() -> None:
    ctx = Context(user=UserInfo(user_id="a", roles=(AdminRole,)))
    assert RoleChecker().check(ctx, DuplicateRoleProbe) is None


@check_roles(EditorRole, SpyRole)
class PositionalRolesProbe:
    pass


def test_several_positional_roles_is_a_choice() -> None:
    assert PositionalRolesProbe._role_info["spec"] == (EditorRole, SpyRole)
    ctx = Context(user=UserInfo(user_id="s", roles=(SpyRole,)))
    assert RoleChecker().check(ctx, PositionalRolesProbe) is None


def test_role_matching_needs_no_parameters() -> None:
    """Roles alone decide the role step; the object rule is a different step."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    assert checker.check(ctx, AdminAction) is None
