# tests/auth/test_role_checker_pr2.py
"""PR-2: ``RoleChecker`` modes, transitive ``includes``, and ``@check_roles`` mode validation."""

from __future__ import annotations

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import check_roles, get_declared_role_mode
from action_machine.auth.base_role import BaseRole
from action_machine.auth.constants import ROLE_ANY
from action_machine.auth.role_expansion import expand_role_privileges, resolve_role_name_to_type
from action_machine.auth.role_mode import RoleMode
from action_machine.auth.role_mode_decorator import role_mode
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import AuthorizationError
from action_machine.core.meta_decorator import meta
from action_machine.logging.log_coordinator import LogCoordinator
from tests.domain_model.domains import TestDomain


@role_mode(RoleMode.ALIVE)
class OrderViewerRole(BaseRole):
    name = "order_viewer"
    description = "View orders."
    includes = ()


@role_mode(RoleMode.ALIVE)
class OrderCreatorRole(BaseRole):
    name = "order_creator"
    description = "Create orders."
    includes = (OrderViewerRole,)


@role_mode(RoleMode.ALIVE)
class OrderManagerRole(BaseRole):
    name = "order_manager"
    description = "Manage orders."
    includes = (OrderCreatorRole,)


@role_mode(RoleMode.DEPRECATED)
class LegacyAdminRole(BaseRole):
    name = "legacy_admin"
    description = "Deprecated admin."
    includes = ()


@role_mode(RoleMode.UNUSED)
class RetiredRole(BaseRole):
    name = "retired"
    description = "Retired."
    includes = ()


@role_mode(RoleMode.SILENCED)
class GhostRole(BaseRole):
    name = "ghost"
    description = "Silenced role."
    includes = ()


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
@check_roles(ROLE_ANY)
class _AnyRoleAction(BaseAction[_P, _R]):
    @summary_aspect("s")
    async def build_summary(self, params, state, box, connections):
        return _R()


def test_expand_privileges_includes_chain() -> None:
    priv = expand_role_privileges(OrderManagerRole)
    assert OrderManagerRole in priv
    assert OrderCreatorRole in priv
    assert OrderViewerRole in priv


def test_resolve_prefers_declared_class_over_registry() -> None:
    assert resolve_role_name_to_type("order_manager") is OrderManagerRole


def test_check_roles_unused_raises() -> None:
    with pytest.raises(ValueError, match="UNUSED"):
        check_roles(RetiredRole)


def test_check_roles_deprecated_warns() -> None:
    with pytest.warns(DeprecationWarning, match="deprecated"):
        check_roles(LegacyAdminRole)


def test_manager_user_passes_viewer_requirement_via_includes() -> None:
    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    action = _GetOrderAction()
    ctx = Context(user=UserInfo(user_id="u1", roles=["order_manager"]))
    rt = machine._get_execution_cache(action.__class__)
    machine._role_checker.check(action, ctx, rt)


def test_silenced_only_user_fails_role_any() -> None:
    machine = ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )
    action = _AnyRoleAction()
    ctx = Context(user=UserInfo(user_id="u1", roles=["ghost"]))
    rt = machine._get_execution_cache(action.__class__)
    with pytest.raises(AuthorizationError, match="Authentication required"):
        machine._role_checker.check(action, ctx, rt)


def test_get_declared_role_mode_round_trip() -> None:
    assert get_declared_role_mode(OrderViewerRole) is RoleMode.ALIVE
