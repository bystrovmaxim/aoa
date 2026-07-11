# tests/intents/check_roles/test_auth_coordinator_protocol.py
"""Tests for AuthCoordinatorProtocol — structural typing for auth_coordinator=."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.auth_coordinator import AuthCoordinator, NoAuthCoordinator
from aoa.action_machine.auth.auth_coordinator_protocol import AuthCoordinatorProtocol
from aoa.action_machine.context.context import Context


async def test_auth_coordinator_satisfies_protocol() -> None:
    coordinator = AuthCoordinator(
        extractor=None,  # type: ignore[arg-type]
        auth_instance=None,  # type: ignore[arg-type]
        assembler=None,  # type: ignore[arg-type]
    )

    assert isinstance(coordinator, AuthCoordinatorProtocol)


async def test_no_auth_coordinator_satisfies_protocol() -> None:
    coordinator = NoAuthCoordinator(context=Context())

    assert isinstance(coordinator, AuthCoordinatorProtocol)


async def test_duck_typed_coordinator_with_no_inheritance_satisfies_protocol() -> None:
    """The whole point of Protocol: a matching process() is enough, no base class needed.

    Mirrors examples/step_13_fastapi/02_auth_override.py's DenyAllCoordinator --
    a real, already-shipped example of exactly this pattern.
    """

    class DuckTypedCoordinator:
        async def process(self, request_data: Any) -> Context | None:
            _ = request_data
            return None

    assert isinstance(DuckTypedCoordinator(), AuthCoordinatorProtocol)


def test_object_without_process_does_not_satisfy_protocol() -> None:
    """Negative case: the check is meaningful, not vacuously true for anything."""

    class NotACoordinator:
        pass

    assert not isinstance(NotACoordinator(), AuthCoordinatorProtocol)
    assert not isinstance(object(), AuthCoordinatorProtocol)
