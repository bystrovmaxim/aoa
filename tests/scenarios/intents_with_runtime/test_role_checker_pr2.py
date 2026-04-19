# tests/scenarios/intents_with_runtime/test_role_checker_pr2.py
"""``RoleChecker`` modes, MRO expansion, and ``@check_roles`` mode validation."""

from __future__ import annotations

import pytest

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.auth.any_role import AnyRole
from action_machine.auth.base_role import BaseRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.exceptions import AuthorizationError
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from tests.scenarios.domain_model.domains import TestDomain


@role_mode(RoleMode.ALIVE)
class OrderViewerRole(BaseRole):
    name = "order_viewer"
    description = "View orders."


@role_mode(RoleMode.ALIVE)
class OrderCreatorRole(OrderViewerRole):
    name = "order_creator"
    description = "Create orders."


@role_mode(RoleMode.ALIVE)
class OrderManagerRole(OrderCreatorRole):
    name = "order_manager"
    description = "Manage orders."


@role_mode(RoleMode.DEPRECATED)
class LegacyAdminRole(BaseRole):
    name = "legacy_admin"
    description = "Deprecated admin."


@role_mode(RoleMode.UNUSED)
class RetiredRole(BaseRole):
    name = "retired"
    description = "Retired."


@role_mode(RoleMode.SILENCED)
class GhostRole(BaseRole):
    name = "ghost"
    description = "Silenced role."


class _P(BaseParams):
    pass


class _R(BaseResult):
    pass


@meta(description="viewer action", domain=TestDomain)
@check_roles(OrderViewerRole)
class _GetOrderAction(BaseAction[_P, _R]):
    @summary_aspect("s")
    async def build_summary(self, params, state, box, connections):
        return _R()


@meta(description="any role", domain=TestDomain)
@check_roles(AnyRole)
class _AnyRoleAction(BaseAction[_P, _R]):
    @summary_aspect("s")
    async def build_summary(self, params, state, box, connections):
        return _R()


def test_role_mro_implies_viewer_via_subclass() -> None:
    assert issubclass(OrderManagerRole, OrderViewerRole)
    assert issubclass(OrderManagerRole, OrderCreatorRole)


def test_check_roles_unused_raises() -> None:
    with pytest.raises(ValueError, match="UNUSED"):
        check_roles(RetiredRole)


def test_check_roles_deprecated_warns() -> None:
    with pytest.warns(DeprecationWarning, match="deprecated"):
        check_roles(LegacyAdminRole)


def test_manager_user_passes_viewer_requirement_via_mro() -> None:
    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    action = _GetOrderAction()
    ctx = Context(user=UserInfo(user_id="u1", roles=(OrderManagerRole,)))
    rt = machine._get_execution_cache(action.__class__)
    machine._role_checker.check(action, ctx, rt)


def test_silenced_only_user_fails_role_any() -> None:
    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    action = _AnyRoleAction()
    ctx = Context(user=UserInfo(user_id="u1", roles=(GhostRole,)))
    rt = machine._get_execution_cache(action.__class__)
    with pytest.raises(AuthorizationError, match="Authentication required"):
        machine._role_checker.check(action, ctx, rt)
