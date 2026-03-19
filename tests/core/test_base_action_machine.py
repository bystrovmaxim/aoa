# tests/core/test_base_action_machine.py
"""
Tests for BaseActionMachine.sync_run.

Covers lines 87-98:
  - Normal call outside an event loop.
  - Error when called inside an event loop.

Strict typing: all parameters and return values are annotated.
state replaced with BaseState.
Updated: log parameter added to SimpleAction aspect.
"""

import warnings

import pytest

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.AspectMethod import summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Logging.action_bound_logger import ActionBoundLogger

################################################################################
# Helper classes
################################################################################


class MockParams(BaseParams):
    """Empty parameters for the test action."""
    pass


class MockResult(BaseResult):
    """Empty result for the test action."""
    pass


@CheckRoles(CheckRoles.NONE, desc="")
class SimpleAction(BaseAction[MockParams, MockResult]):
    """
    Minimal action for testing sync_run.

    Returns MockResult with no side effects.
    """

    @summary_aspect("test")
    async def summary(
        self,
        params: MockParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, object],
        log: ActionBoundLogger,  # added log parameter
    ) -> MockResult:
        """
        Main aspect of the action.

        Args:
            params:      input parameters.
            state:       aspect pipeline state.
            deps:        dependency factory.
            connections: connection dictionary.
            log:         bound logger (not used in test, but mandatory).

        Returns:
            MockResult: empty result.
        """
        # For the test we can do nothing with log
        return MockResult()


################################################################################
# Tests
################################################################################


class TestSyncRun:
    """Tests for the synchronous wrapper sync_run."""

    def test_sync_run_outside_event_loop_returns_result(self) -> None:
        """
        sync_run outside an async context executes the action and returns a result.

        Checks:
            - Calling sync_run without an active event loop succeeds.
            - The returned object is a MockResult instance.
        """
        machine: ActionProductMachine = ActionProductMachine(mode="test")
        action: SimpleAction = SimpleAction()
        params: MockParams = MockParams()
        context: Context = Context()  # empty context for test

        result: MockResult = machine.sync_run(context, action, params)

        assert isinstance(result, MockResult)

    @pytest.mark.anyio
    async def test_sync_run_inside_event_loop_raises_runtime_error(self) -> None:
        """
        sync_run inside a running event loop raises RuntimeError.

        Due to the implementation of except RuntimeError in sync_run,
        the actual error message comes from asyncio.run().

        The warning about an unawaited coroutine is suppressed – it's expected.

        Checks:
            - RuntimeError with the message "cannot be called from a running event loop".
        """
        machine: ActionProductMachine = ActionProductMachine(mode="test")
        action: SimpleAction = SimpleAction()
        params: MockParams = MockParams()
        context: Context = Context()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with pytest.raises(
                RuntimeError,
                match="cannot be called from a running event loop",
            ):
                machine.sync_run(context, action, params)