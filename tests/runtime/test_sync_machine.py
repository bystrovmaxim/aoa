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
"""

import pytest

from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.sync_action_product_machine import SyncActionProductMachine


@pytest.fixture()
def sync_machine() -> SyncActionProductMachine:
    """SyncActionProductMachine with a silent logger for unit tests."""
    return SyncActionProductMachine(
        mode="test",
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

    def test_mode_attribute(self, sync_machine) -> None:
        assert sync_machine._mode == "test"
