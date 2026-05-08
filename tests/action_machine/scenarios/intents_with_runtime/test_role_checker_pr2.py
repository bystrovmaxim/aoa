# tests/scenarios/intents_with_runtime/test_role_checker_pr2.py
"""``RoleChecker`` modes, MRO expansion, and ``@check_roles`` mode validation."""

from __future__ import annotations

import pytest

from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode


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


def test_role_mro_implies_viewer_via_subclass() -> None:
    assert issubclass(OrderManagerRole, OrderViewerRole)
    assert issubclass(OrderManagerRole, OrderCreatorRole)


def test_check_roles_unused_raises() -> None:
    with pytest.raises(ValueError, match="UNUSED"):
        check_roles(RetiredRole)


def test_check_roles_deprecated_warns() -> None:
    with pytest.warns(DeprecationWarning, match="deprecated"):
        check_roles(LegacyAdminRole)
