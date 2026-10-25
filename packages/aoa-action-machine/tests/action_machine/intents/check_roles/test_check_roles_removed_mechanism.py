# tests/action_machine/intents/check_roles/test_check_roles_removed_mechanism.py
"""The removed condition layer is gone, and what remains refuses clearly."""

from __future__ import annotations

import pytest

from aoa.action_machine.exceptions import RoleSpecTypeError
from aoa.action_machine.intents.check_roles import check_roles

from ....support.domain_model.roles import AdminRole


def test_grant_import_fails() -> None:
    with pytest.raises(ImportError):
        from aoa.action_machine.intents.check_roles import grant  # noqa: F401


def test_grant_type_import_fails() -> None:
    with pytest.raises(ImportError):
        from aoa.action_machine.intents.check_roles import Grant  # noqa: F401


def test_grant_is_not_an_attribute_of_the_package() -> None:
    import aoa.action_machine.intents.check_roles as check_roles_pkg

    assert not hasattr(check_roles_pkg, "grant")
    assert not hasattr(check_roles_pkg, "Grant")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"guard": lambda *_: False},
        {"guard_reason": "REASON"},
        {"when": lambda _: False},
    ],
)
def test_removed_keywords_refuse_with_a_migration_message(kwargs: dict) -> None:
    with pytest.raises(RoleSpecTypeError) as excinfo:

        @check_roles(AdminRole, **kwargs)
        class _Action:
            pass

    assert "@access_decide" in str(excinfo.value)


def test_unknown_keyword_refuses_without_a_migration_message() -> None:
    with pytest.raises(RoleSpecTypeError) as excinfo:

        @check_roles(AdminRole, required=True)
        class _Action:
            pass

    assert "@access_decide" not in str(excinfo.value)


def test_the_condition_exceptions_are_absent() -> None:
    import aoa.action_machine.exceptions as exc

    assert not hasattr(exc, "AccessConditionAsyncError")
    assert not hasattr(exc, "ConditionReasonError")
