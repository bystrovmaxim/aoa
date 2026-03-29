# tests/logging/test_scoped_logger.py
"""
Тесты для ScopedLogger — логгера, привязанного к scope текущего аспекта
или плагина.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- info/warning/error/debug добавляют ключ "level" в var с правильным значением.
- Пользовательские kwargs попадают в var.
- LogScope для аспектов создаётся с ключами: machine, mode, action, aspect,
  nest_level (в этом порядке).
- LogScope для плагинов создаётся с ключами: machine, mode, plugin, action,
  event, nest_level (в этом порядке).
- emit вызывается с правильными параметрами: BaseState(), BaseParams(),
  переданный indent, scope, context.
- Координатор логирования вызывается ровно один раз на каждый вызов метода.
- Пользовательский ключ "level" в kwargs игнорируется — используется
  системное значение.
- nest_level доступен в scope через scope["nest_level"].
- plugin_name и event_name корректно формируют scope плагина.
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
    """Тесты для ScopedLogger в режиме аспекта (без plugin_name)."""

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
        """Создаёт ScopedLogger с параметрами аспекта (без plugin_name)."""
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
        """
        emit получает LogScope с правильными ключами для аспекта.

        Порядок ключей: machine, mode, action, aspect, nest_level.
        nest_level включён в scope и доступен через scope["nest_level"].
        """
        await logger.info("msg")

        mock_coordinator.emit.assert_awaited_once()
        scope = mock_coordinator.emit.call_args.kwargs["scope"]

        assert isinstance(scope, LogScope)
        assert scope["machine"] == "TestMachine"
        assert scope["mode"] == "test_mode"
        assert scope["action"] == "myapp.actions.TestAction"
        assert scope["aspect"] == "test_aspect"
        assert scope["nest_level"] == 2
        # Проверка порядка ключей (важно для as_dotpath)
        assert list(scope.keys()) == ["machine", "mode", "action", "aspect", "nest_level"]

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


class TestScopedLoggerPluginMode:
    """
    Тесты для ScopedLogger в режиме плагина (с plugin_name).

    Когда ScopedLogger создаётся с параметром plugin_name, scope содержит
    поля: machine, mode, plugin, action, event, nest_level.
    Поле aspect отсутствует — вместо него plugin и event.
    """

    @pytest.fixture
    def mock_coordinator(self) -> AsyncMock:
        """Мок координатора логирования."""
        coordinator = AsyncMock(spec=LogCoordinator)
        coordinator.emit = AsyncMock()
        return coordinator

    @pytest.fixture
    def context(self) -> Context:
        """Тестовый контекст."""
        return Context()

    @pytest.fixture
    def plugin_logger(self, mock_coordinator: AsyncMock, context: Context) -> ScopedLogger:
        """Создаёт ScopedLogger с параметрами плагина."""
        return ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=1,
            machine_name="TestMachine",
            mode="production",
            action_name="myapp.actions.CreateOrder",
            aspect_name="",
            context=context,
            plugin_name="MetricsPlugin",
            event_name="global_finish",
        )

    @pytest.mark.anyio
    async def test_plugin_scope_has_correct_keys(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """
        Scope плагина содержит поля: machine, mode, plugin, action,
        event, nest_level (в этом порядке). Поле aspect отсутствует.
        """
        await plugin_logger.info("Plugin message")

        mock_coordinator.emit.assert_awaited_once()
        scope = mock_coordinator.emit.call_args.kwargs["scope"]

        assert isinstance(scope, LogScope)
        assert scope["machine"] == "TestMachine"
        assert scope["mode"] == "production"
        assert scope["plugin"] == "MetricsPlugin"
        assert scope["action"] == "myapp.actions.CreateOrder"
        assert scope["event"] == "global_finish"
        assert scope["nest_level"] == 1
        # Проверка порядка ключей
        assert list(scope.keys()) == [
            "machine", "mode", "plugin", "action", "event", "nest_level"
        ]
        # Поле aspect отсутствует в scope плагина
        assert "aspect" not in scope

    @pytest.mark.anyio
    async def test_plugin_scope_dotpath(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """as_dotpath() для scope плагина объединяет все непустые значения."""
        await plugin_logger.info("msg")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        dotpath = scope.as_dotpath()
        assert dotpath == "TestMachine.production.MetricsPlugin.myapp.actions.CreateOrder.global_finish.1"

    @pytest.mark.anyio
    async def test_plugin_logger_passes_indent(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """indent для scope плагина равен nest_level."""
        await plugin_logger.info("msg")

        indent = mock_coordinator.emit.call_args.kwargs["indent"]
        assert indent == 1

    @pytest.mark.anyio
    async def test_plugin_logger_level_in_var(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Уровень логирования корректно передаётся в var."""
        await plugin_logger.warning("Warning from plugin")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "warning"

    @pytest.mark.anyio
    async def test_plugin_logger_user_kwargs(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Пользовательские kwargs попадают в var."""
        await plugin_logger.info("msg", duration=0.5, action_count=10)

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["duration"] == 0.5
        assert var["action_count"] == 10
        assert var["level"] == "info"


class TestScopedLoggerWithState:
    """Тесты передачи реальных state и params в ScopedLogger."""

    @pytest.fixture
    def mock_coordinator(self) -> AsyncMock:
        coordinator = AsyncMock(spec=LogCoordinator)
        coordinator.emit = AsyncMock()
        return coordinator

    @pytest.fixture
    def context(self) -> Context:
        return Context()

    @pytest.mark.anyio
    async def test_custom_state_and_params_passed(
        self, mock_coordinator: AsyncMock, context: Context
    ) -> None:
        """Если state и params переданы в конструктор, они попадают в emit."""
        state = BaseState({"total": 1500.0, "count": 5})
        params = BaseParams()

        logger = ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=0,
            machine_name="Machine",
            mode="test",
            action_name="Action",
            aspect_name="aspect",
            context=context,
            state=state,
            params=params,
        )

        await logger.info("msg")

        emitted_state = mock_coordinator.emit.call_args.kwargs["state"]
        emitted_params = mock_coordinator.emit.call_args.kwargs["params"]

        assert emitted_state is state
        assert emitted_state.to_dict() == {"total": 1500.0, "count": 5}
        assert emitted_params is params

    @pytest.mark.anyio
    async def test_nest_level_zero_in_scope(
        self, mock_coordinator: AsyncMock, context: Context
    ) -> None:
        """nest_level=0 корректно попадает в scope."""
        logger = ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=0,
            machine_name="Machine",
            mode="prod",
            action_name="RootAction",
            aspect_name="summary",
            context=context,
        )

        await logger.info("msg")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        assert scope["nest_level"] == 0
