# src/action_machine/testing/__init__.py
"""
ActionMachine testing infrastructure package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Contains core testing utilities for ActionMachine actions: ``TestBench`` as
single entry point, test doubles, context stubs, state validation helpers, and
cross-machine result comparison.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

Single entry point:

- **TestBench** - immutable fluent test harness. Internally creates async and
  sync production machines with mocks, executes actions on both, and compares
  results. Each fluent call (``.with_user``, ``.with_mocks``, etc.) returns a
  NEW ``TestBench`` instance, leaving original untouched and safe for parallel use.

  Terminal methods (mandatory ``rollup: bool``, no default):
  - ``run(action, params, rollup)`` - full execution on all machines.
  - ``run_aspect(action, aspect_name, params, state, rollup)`` - single aspect.
  - ``run_summary(action, params, state, rollup)`` - summary only.

Mocks:

- **MockAction** - action test double. Supports fixed ``result`` and dynamic
  ``side_effect`` responses. Tracks ``call_count`` and ``last_params``.

Stubs:

- **UserInfoStub** - user stub (defaults: ``user_id="test_user"``,
  ``roles=(StubTesterRole,)`` from ``action_machine.testing.stubs``).
- **RuntimeInfoStub** - runtime environment stub (``hostname="test-host"``).
- **RequestInfoStub** - request stub (``trace_id="test-trace-000"``).
- **ContextStub** - full context stub composing all three stubs.

Validation:

- **validate_state_for_aspect** / **validate_state_for_summary** -
  accept aspect tuple and checker callback (same shape as ``GraphCoordinator``).

Comparison:

- **compare_results** - compares results from two machines with detailed
  mismatch output.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Test case setup
         |
         v
    TestBench + stubs + mocks configuration
         |
         v
    Run action on async and sync machines
         |
         +--> optional aspect/summary-only execution
         +--> state validation helpers
         |
         v
    compare_results / assertions in test

"""

from action_machine.testing.bench import TestBench
from action_machine.testing.comparison import compare_results
from action_machine.testing.mock_action import MockAction
from action_machine.testing.state_validator import validate_state_for_aspect, validate_state_for_summary
from action_machine.testing.stubs import (
    ContextStub,
    RequestInfoStub,
    RuntimeInfoStub,
    StubTesterRole,
    UserInfoStub,
)

__all__ = [
    "ContextStub",
    "MockAction",
    "RequestInfoStub",
    "RuntimeInfoStub",
    "StubTesterRole",
    "TestBench",
    "UserInfoStub",
    "compare_results",
    "validate_state_for_aspect",
    "validate_state_for_summary",
]
