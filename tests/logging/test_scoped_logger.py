# tests/logging/test_scoped_logger.py
"""
Тесты для ScopedLogger — логгера, привязанного к scope текущего аспекта.

Проверяется:
- info/warning/error/debug добавляют ключ "level" в var с правильным значением.
- Пользовательские kwargs попадают в var.
- LogScope создаётся с правильными ключами в правильном порядке:
  machine, mode, action, aspect.
- emit вызывается с правильными параметрами: BaseState(), BaseParams(),
  переданный indent, scope, context.
- Координатор логирования вызывается ровно один раз на каждый вызов метода.
- Пользовательский ключ "level" в kwargs игнорируется — используется
  системное значение.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.scoped_logger import ScopedLogger


class TestScopedLogger:
    """Тесты для ScopedLogger."""

    @pytest.fixture
    def mock_coordinator(self) -> AsyncMock:
        """Мок координатора логирования с асинхронным методом emit."""
        coordinator = AsyncMock(spec=LogCoordinator)
        coordinator.emit = AsyncMock()
        return coordinator

    @pytest.fixture
    def context(self) -> Context:
        """Тестовый контекст."""
        return Context()

    @pytest.fixture
    def logger(self, mock_coordinator: AsyncMock, context: Context) -> ScopedLogger:
        """Создаёт ScopedLogger с заданными параметрами."""
        return ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=2,
            machine_name="TestMachine",
            mode="test_mode",
            action_name="myapp.actions.TestAction",
            aspect_name="test_aspect",
            context=context,
        )

    # ------------------------------------------------------------------
    # ТЕСТЫ: Проверка вызова emit
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_info_calls_emit_with_level_info(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock, context: Context
    ) -> None:
        """info вызывает emit с level='info'."""
        await logger.info("Test message", user="john", count=42)

        mock_coordinator.emit.assert_awaited_once()
        args, kwargs = mock_coordinator.emit.call_args

        var = kwargs["var"]
        assert var["level"] == "info"
        assert var["user"] == "john"
        assert var["count"] == 42

    @pytest.mark.anyio
    async def test_warning_calls_emit_with_level_warning(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """warning вызывает emit с level='warning'."""
        await logger.warning("Test warning")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "warning"

    @pytest.mark.anyio
    async def test_error_calls_emit_with_level_error(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """error вызывает emit с level='error'."""
        await logger.error("Test error")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "error"

    @pytest.mark.anyio
    async def test_debug_calls_emit_with_level_debug(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """debug вызывает emit с level='debug'."""
        await logger.debug("Test debug")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "debug"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Передача параметров в emit
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_receives_correct_message(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Параметр message передаётся в emit без изменений."""
        await logger.info("Hello, world!")

        mock_coordinator.emit.assert_awaited_once()
        assert mock_coordinator.emit.call_args.kwargs["message"] == "Hello, world!"

    @pytest.mark.anyio
    async def test_emit_receives_correct_scope(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """emit получает LogScope с правильными ключами."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        scope = mock_coordinator.emit.call_args.kwargs["scope"]

        assert isinstance(scope, LogScope)
        assert scope["machine"] == "TestMachine"
        assert scope["mode"] == "test_mode"
        assert scope["action"] == "myapp.actions.TestAction"
        assert scope["aspect"] == "test_aspect"
        # Проверка порядка ключей (важно для as_dotpath)
        assert list(scope.keys()) == ["machine", "mode", "action", "aspect"]

    @pytest.mark.anyio
    async def test_emit_receives_context(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock, context: Context
    ) -> None:
        """emit получает тот же контекст, что был передан в логгер."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        ctx = mock_coordinator.emit.call_args.kwargs["ctx"]
        assert ctx is context

    @pytest.mark.anyio
    async def test_emit_receives_empty_state_and_params(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """emit получает пустые экземпляры BaseState и BaseParams."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        state = mock_coordinator.emit.call_args.kwargs["state"]
        params = mock_coordinator.emit.call_args.kwargs["params"]

        assert isinstance(state, BaseState)
        assert state.to_dict() == {}
        assert isinstance(params, BaseParams)

    @pytest.mark.anyio
    async def test_emit_receives_correct_indent(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """emit получает уровень вложенности, заданный при создании логгера."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        indent = mock_coordinator.emit.call_args.kwargs["indent"]
        assert indent == 2

    # ------------------------------------------------------------------
    # ТЕСТЫ: Множественные вызовы
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_multiple_calls_multiple_emits(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Каждый вызов метода логирования приводит к отдельному emit."""
        await logger.info("First")
        await logger.warning("Second")
        await logger.error("Third")

        assert mock_coordinator.emit.await_count == 3

    # ------------------------------------------------------------------
    # ТЕСТЫ: Пользовательские kwargs
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_user_kwargs_are_passed_to_var(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Все пользовательские kwargs попадают в var."""
        await logger.info("msg", extra="data", flag=True, amount=100.5)

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["extra"] == "data"
        assert var["flag"] is True
        assert var["amount"] == 100.5
        assert var["level"] == "info"

    @pytest.mark.anyio
    async def test_user_kwargs_override_nothing(
        self, logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Пользователь может передать ключ 'level', но он будет перезаписан системным."""
        await logger.info("msg", level="user_level")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "info"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Граничные случаи
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_empty_message(self, logger: ScopedLogger, mock_coordinator: AsyncMock) -> None:
        """Пустое сообщение допустимо."""
        await logger.info("")

        mock_coordinator.emit.assert_awaited_once()
        assert mock_coordinator.emit.call_args.kwargs["message"] == ""

    @pytest.mark.anyio
    async def test_no_kwargs(self, logger: ScopedLogger, mock_coordinator: AsyncMock) -> None:
        """Вызов без kwargs передаёт только level."""
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var == {"level": "info"}
