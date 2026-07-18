# tests/auth/test_permission_namespace.py
"""Tests for compute_cache_partition — the opaque label behind PermissionNamespace."""

from __future__ import annotations

from aoa.action_machine.auth.permission_namespace import compute_cache_partition
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo

from ...support.domain_model.roles import AdminRole, ManagerRole


def _context(user_id: str | None, *roles: type) -> Context:
    return Context(user=UserInfo(user_id=user_id, roles=tuple(roles)))


class TestDeterminism:
    """The same identity always maps to the same label."""

    def test_same_identity_yields_the_same_partition(self) -> None:
        a = compute_cache_partition(_context("alice", ManagerRole))
        b = compute_cache_partition(_context("alice", ManagerRole))
        assert a == b

    def test_role_order_does_not_matter(self) -> None:
        a = compute_cache_partition(_context("alice", AdminRole, ManagerRole))
        b = compute_cache_partition(_context("alice", ManagerRole, AdminRole))
        assert a == b

    def test_anonymous_context_is_stable_too(self) -> None:
        a = compute_cache_partition(_context(None))
        b = compute_cache_partition(_context(None))
        assert a == b


class TestDistinctIdentitiesDiffer:
    """A different user_id or a different role set must map to a different label."""

    def test_different_user_id_differs(self) -> None:
        alice = compute_cache_partition(_context("alice", ManagerRole))
        bob = compute_cache_partition(_context("bob", ManagerRole))
        assert alice != bob

    def test_different_roles_for_the_same_user_id_differs(self) -> None:
        as_admin = compute_cache_partition(_context("alice", AdminRole))
        as_manager = compute_cache_partition(_context("alice", ManagerRole))
        assert as_admin != as_manager

    def test_more_roles_differs_from_fewer(self) -> None:
        one_role = compute_cache_partition(_context("alice", ManagerRole))
        two_roles = compute_cache_partition(_context("alice", ManagerRole, AdminRole))
        assert one_role != two_roles

    def test_anonymous_differs_from_a_real_identity(self) -> None:
        anonymous = compute_cache_partition(_context(None))
        alice = compute_cache_partition(_context("alice", ManagerRole))
        assert anonymous != alice


class TestOpaqueShape:
    """The label is a string that does not visibly embed the identity it was built from."""

    def test_label_does_not_contain_the_raw_user_id(self) -> None:
        label = compute_cache_partition(_context("alice", ManagerRole))
        assert "alice" not in label

    def test_label_is_a_non_empty_string(self) -> None:
        label = compute_cache_partition(_context("alice", ManagerRole))
        assert isinstance(label, str) and label
