# tests/logging/test_action_bound_logger.py
"""
Tests for ActionBoundLogger — logger bound to the current aspect.

Checks:
- info/warning/error/debug add "level" key to var with correct value.
- User kwargs end up in var.
- LogScope is created with correct keys in correct order: machine, mode, action, aspect.
- emit is called with correct parameters: BaseState(), BaseParams(), passed indent, scope, context.
- Log coordinator is called exactly once per call.

Изменения (этап 1):
- В тестах не требуется изменений, так как ActionBoundLogger не изменил публичный API.
- Обновлены комментарии.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.action_bound_logger import ActionBoundLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope


class TestActionBoundLogger:
    """Tests for ActionBoundLogger."""

    @pytest.fixture
    def mock_coordinator(self) -> AsyncMock:
        """Mock log coordinator with async emit method."""
        coordinator = AsyncMock(spec=LogCoordinator)
        coordinator.emit = AsyncMock()
        return coordinator

    @pytest.fixture
    def context(self) -> Context:
        """Test context."""
        return Context()

    @pytest.fixture
    def logger(self, mock_coordinator: AsyncMock, context: Context) -> ActionBoundLogger:
        """Creates ActionBoundLogger with given parameters."""
        return ActionBoundLogger(
            coordinator=mock_coordinator,
            nest_level=2,
            machine_name="TestMachine",
            mode="test_mode",
            action_name="myapp.actions.TestAction",
            aspect_name="test_aspect",
            context=context,
        )

    # ------------------------------------------------------------------
    # TESTS: emit call verification
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_info_calls_emit_with_level_info(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock, context: Context
    ) -> None:
        """info calls emit with level='info'."""
        await logger.info("Test message", user="john", count=42)

        mock_coordinator.emit.assert_awaited_once()
        args, kwargs = mock_coordinator.emit.call_args

        # Check var
        var = kwargs["var"]
        assert var["level"] == "info"
        assert var["user"] == "john"
        assert var["count"] == 42

    @pytest.mark.anyio
    async def test_warning_calls_emit_with_level_warning(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """warning calls emit with level='warning'."""
        await logger.warning("Test warning")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "warning"

    @pytest.mark.anyio
    async def test_error_calls_emit_with_level_error(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """error calls emit with level='error'."""
        await logger.error("Test error")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "error"

    @pytest.mark.anyio
    async def test_debug_calls_emit_with_level_debug(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """debug calls emit with level='debug'."""
        await logger.debug("Test debug")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "debug"

    # ------------------------------------------------------------------
    # TESTS: Parameter passing to emit
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_receives_correct_message(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """message parameter is passed to emit unchanged."""
        await logger.info("Hello, world!")

        mock_coordinator.emit.assert_awaited_once()
        assert mock_coordinator.emit.call_args.kwargs["message"] == "Hello, world!"

    @pytest.mark.anyio
    async def test_emit_receives_correct_scope(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """emit receives LogScope with correct keys."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        scope = mock_coordinator.emit.call_args.kwargs["scope"]

        assert isinstance(scope, LogScope)
        assert scope["machine"] == "TestMachine"
        assert scope["mode"] == "test_mode"
        assert scope["action"] == "myapp.actions.TestAction"
        assert scope["aspect"] == "test_aspect"
        # Check key order (important for as_dotpath)
        assert list(scope.keys()) == ["machine", "mode", "action", "aspect"]

    @pytest.mark.anyio
    async def test_emit_receives_context(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock, context: Context
    ) -> None:
        """emit receives the same context that was passed to the logger."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        ctx = mock_coordinator.emit.call_args.kwargs["ctx"]
        assert ctx is context

    @pytest.mark.anyio
    async def test_emit_receives_empty_state_and_params(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """emit receives empty BaseState and BaseParams instances."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        state = mock_coordinator.emit.call_args.kwargs["state"]
        params = mock_coordinator.emit.call_args.kwargs["params"]

        assert isinstance(state, BaseState)
        assert state.to_dict() == {}
        assert isinstance(params, BaseParams)

    @pytest.mark.anyio
    async def test_emit_receives_correct_indent(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """emit receives the nesting level set when creating the logger."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        indent = mock_coordinator.emit.call_args.kwargs["indent"]
        assert indent == 2

    # ------------------------------------------------------------------
    # TESTS: Multiple calls
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_multiple_calls_multiple_emits(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Each logging method call results in a separate emit."""
        await logger.info("First")
        await logger.warning("Second")
        await logger.error("Third")

        assert mock_coordinator.emit.await_count == 3

    # ------------------------------------------------------------------
    # TESTS: User kwargs
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_user_kwargs_are_passed_to_var(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """All user kwargs end up in var."""
        await logger.info("msg", extra="data", flag=True, amount=100.5)

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["extra"] == "data"
        assert var["flag"] is True
        assert var["amount"] == 100.5
        assert var["level"] == "info"  # not overwritten

    @pytest.mark.anyio
    async def test_user_kwargs_override_nothing(
        self, logger: ActionBoundLogger, mock_coordinator: AsyncMock
    ) -> None:
        """User can pass 'level' key, but it will be overwritten by system."""
        await logger.info("msg", level="user_level")  # user accidentally passes level

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        # Should be overwritten with system value
        assert var["level"] == "info"
        # User's level should not remain (overwritten)

    # ------------------------------------------------------------------
    # TESTS: Edge cases
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_empty_message(self, logger: ActionBoundLogger, mock_coordinator: AsyncMock) -> None:
        """Empty message is allowed."""
        await logger.info("")

        mock_coordinator.emit.assert_awaited_once()
        assert mock_coordinator.emit.call_args.kwargs["message"] == ""

    @pytest.mark.anyio
    async def test_no_kwargs(self, logger: ActionBoundLogger, mock_coordinator: AsyncMock) -> None:
        """Call without kwargs passes only level."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var == {"level": "info"}