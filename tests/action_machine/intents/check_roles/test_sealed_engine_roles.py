# tests/intents/check_roles/test_sealed_engine_roles.py
"""Engine sentinel roles reject subclassing."""

import pytest

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.none_role import NoneRole


def test_any_role_rejects_subclassing() -> None:
    with pytest.raises(TypeError, match="Cannot subclass sealed engine role AnyRole"):

        class _Bad(AnyRole):
            pass


def test_none_role_rejects_subclassing() -> None:
    with pytest.raises(TypeError, match="Cannot subclass sealed engine role NoneRole"):

        class _Bad(NoneRole):
            pass
