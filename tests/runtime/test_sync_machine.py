# tests/runtime/test_sync_machine.py
"""Tests SyncActionProductMachine — synchronous wrapper for ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

SyncActionProductMachine inherits ActionProductMachine and overrides public
``run()`` with a synchronous entry point.

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS COVERED
═══════════════════════════════════════════════════════════════════════════════

Inheritance from ActionProductMachine:

    - isinstance(sync_machine, ActionProductMachine) → True.
    - _run_internal() is available and working.
    - run() invokes asyncio.run on _run_internal with rollup=False, nested_level=0.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.sync_action_product_machine import SyncActionProductMachine
from action_machine.testing.stubs import ContextStub
from tests.scenarios.domain_model.child_action import ChildAction


@pytest.fixture()
def sync_machine() -> SyncActionProductMachine:
    """SyncActionProductMachine with a silent logger for unit tests."""
    return SyncActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[]),
    )


class TestInheritance:
    """SyncActionProductMachine inherits ActionProductMachine."""

    def test_isinstance_action_product_machine(self, sync_machine) -> None:
        assert isinstance(sync_machine, ActionProductMachine)
        assert isinstance(sync_machine, SyncActionProductMachine)

    def test_has_run_internal(self, sync_machine) -> None:
        assert hasattr(sync_machine, "_run_internal")
        assert callable(sync_machine._run_internal)

def test_public_run_wraps_asyncio_run(
    monkeypatch: pytest.MonkeyPatch,
    sync_machine: SyncActionProductMachine,
) -> None:
    ctx = ContextStub()
    action = ChildAction()
    params = ChildAction.Params(value="sync-args")
    expected = ChildAction.Result(processed="mocked")

    mocked_internal = AsyncMock(return_value=expected)
    monkeypatch.setattr(sync_machine, "_run_internal", mocked_internal)

    result = sync_machine.run(ctx, action, params, connections=None)

    assert result is expected
    mocked_internal.assert_awaited_once_with(
        context=ctx,
        action=action,
        params=params,
        resources=None,
        connections=None,
        nested_level=0,
        rollup=False,
    )
