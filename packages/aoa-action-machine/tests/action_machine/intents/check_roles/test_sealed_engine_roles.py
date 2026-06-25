# tests/intents/check_roles/test_sealed_engine_roles.py
"""Engine sentinel roles reject subclassing."""

import pytest

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.guest_role import GuestRole


def test_any_role_rejects_subclassing() -> None:
    with pytest.raises(TypeError, match="Cannot subclass sealed engine role AnyRole"):

        class _Bad(AnyRole):
            pass


def test_guest_role_rejects_subclassing() -> None:
    with pytest.raises(TypeError, match="Cannot subclass sealed engine role GuestRole"):

        class _Bad(GuestRole):
            pass
