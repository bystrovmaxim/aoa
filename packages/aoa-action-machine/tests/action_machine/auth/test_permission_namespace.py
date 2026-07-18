# tests/auth/test_permission_namespace.py
"""Tests for compute_cache_partition — the opaque label behind PermissionNamespace."""

from __future__ import annotations

from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.auth.permission_namespace import compute_cache_partition
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode

from ...support.domain_model.roles import AdminRole, ManagerRole


def _context(user_id: str | None, *roles: type) -> Context:
    return Context(user=UserInfo(user_id=user_id, roles=tuple(roles)))


@role_mode(RoleMode.ALIVE)
class _PipedRole(ApplicationRole):
    """A role whose ``.name`` embeds the old delimiter -- ``BaseRole.name`` is a
    free-form, developer-chosen string with no character restrictions; only the
    Python *class name* is required to end in ``Role``."""

    name = "b|c"
    description = "Test-only role with a '|' in its name (audit finding 3)."


@role_mode(RoleMode.ALIVE)
class _CRole(ApplicationRole):
    name = "c"
    description = "Test-only role named 'c', paired with _PipedRole (audit finding 3)."


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

    def test_empty_string_user_id_differs_from_anonymous(self) -> None:
        """Audit finding 4: user_id=None (anonymous) and user_id="" (an authenticated
        identity with an empty id -- nothing on UserInfo forbids constructing one)
        used to hash to the same partition for the same role set, via an
        f"{user_id or ''}" default that cannot tell "absent" from "empty"."""
        anonymous = compute_cache_partition(_context(None, ManagerRole))
        empty_id = compute_cache_partition(_context("", ManagerRole))
        assert anonymous != empty_id


class TestNoDelimiterCollision:
    """Audit finding 3: joining fields with a plain "|"/"," separator lets two
    different identities hash to the same partition whenever a field's own
    content contains that separator -- ``"a|b" + "|" + "c"`` and
    ``"a" + "|" + "b|c"`` are both ``"a|b|c"``. Length-prefixed framing removes
    the ambiguity structurally, regardless of what user_id/role names contain."""

    def test_pipe_in_user_id_does_not_collide_with_a_role_name_boundary(self) -> None:
        # "a|b" as user_id with role "c" versus "a" as user_id with role "b|c":
        # the pre-fix f"{user_id}|{roles}" join produced "a|b|c" for both.
        straddled_in_user_id = compute_cache_partition(_context("a|b", _CRole))
        straddled_in_role_name = compute_cache_partition(_context("a", _PipedRole))
        assert straddled_in_user_id != straddled_in_role_name


class TestOpaqueShape:
    """The label is a string that does not visibly embed the identity it was built from."""

    def test_label_does_not_contain_the_raw_user_id(self) -> None:
        label = compute_cache_partition(_context("alice", ManagerRole))
        assert "alice" not in label

    def test_label_is_a_non_empty_string(self) -> None:
        label = compute_cache_partition(_context("alice", ManagerRole))
        assert isinstance(label, str) and label
