# tests/logging/test_scoped_logger.py
"""
Тесты ScopedLogger — логгера, привязанного к scope текущего аспекта или плагина.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ScopedLogger — обёртка над LogCoordinator, привязанная к конкретному
scope выполнения. Автоматически добавляет координаты выполнения в LogScope
и передаёт их в LogCoordinator при каждом вызове info/warning/error/debug.

Создаётся ActionProductMachine (для аспектов) или PluginRunContext
(для плагинов). Аспекты получают ScopedLogger через ToolsBox,
обработчики плагинов — через параметр log.

═══════════════════════════════════════════════════════════════════════════════
ДВА РЕЖИМА ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

1. Логгер для аспектов действий
   Scope содержит поля: machine, mode, action, aspect, nest_level.
   Создаётся без plugin_name и event_name.

2. Логгер для обработчиков плагинов
   Scope содержит поля: machine, mode, plugin, action, event, nest_level.
   Создаётся с plugin_name и event_name.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- info/warning/error/debug добавляют ключ "level" в var с правильным значением.
- Пользовательские kwargs попадают в var.
- LogScope для аспектов создаётся с правильными ключами.
- LogScope для плагинов создаётся с правильными ключами.
- emit вызывается с правильными параметрами (state, params, indent, scope, context).
- Пользовательский ключ "level" в kwargs игнорируется.
- nest_level доступен в scope.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.scoped_logger import ScopedLogger


@pytest.fixture
def mock_coordinator() -> AsyncMock:
    """Мок координатора логирования."""
    coordinator = AsyncMock(spec=LogCoordinator)
    coordinator.emit = AsyncMock()
    return coordinator


@pytest.fixture
def context() -> Context:
    """Тестовый контекст."""
    return Context()


# ======================================================================
# ТЕСТЫ: Логгер для аспектов
# ======================================================================


class TestAspectLogger:
    """ScopedLogger в режиме аспекта (без plugin_name)."""

    @pytest.fixture
    def aspect_logger(
        self, mock_coordinator: AsyncMock, context: Context
    ) -> ScopedLogger:
        """Создаёт ScopedLogger с параметрами аспекта."""
        return ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=2,
            machine_name="TestMachine",
            mode="test_mode",
            action_name="myapp.actions.TestAction",
            aspect_name="test_aspect",
            context=context,
        )

    @pytest.mark.anyio
    async def test_info_adds_level_info(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """
        info() вызывает emit с level='info' в var.
        """
        # Act
        await aspect_logger.info("Test message", user="john", count=42)

        # Assert
        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "info"
        assert var["user"] == "john"
        assert var["count"] == 42

    @pytest.mark.anyio
    async def test_warning_adds_level_warning(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """warning() вызывает emit с level='warning'."""
        await aspect_logger.warning("Warning message")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "warning"

    @pytest.mark.anyio
    async def test_error_adds_level_error(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """error() вызывает emit с level='error'."""
        await aspect_logger.error("Error message")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "error"

    @pytest.mark.anyio
    async def test_debug_adds_level_debug(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """debug() вызывает emit с level='debug'."""
        await aspect_logger.debug("Debug message")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "debug"

    @pytest.mark.anyio
    async def test_user_kwargs_are_passed(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Пользовательские kwargs попадают в var."""
        await aspect_logger.info("msg", extra="data", flag=True, amount=100.5)

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["extra"] == "data"
        assert var["flag"] is True
        assert var["amount"] == 100.5
        assert var["level"] == "info"

    @pytest.mark.anyio
    async def test_user_level_override_ignored(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Пользовательский 'level' перезаписывается системным."""
        await aspect_logger.info("msg", level="user_level")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "info"

    @pytest.mark.anyio
    async def test_scope_has_correct_keys(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """
        Scope содержит: machine, mode, action, aspect, nest_level.
        Порядок ключей важен для as_dotpath.
        """
        await aspect_logger.info("msg")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        assert isinstance(scope, LogScope)
        assert scope["machine"] == "TestMachine"
        assert scope["mode"] == "test_mode"
        assert scope["action"] == "myapp.actions.TestAction"
        assert scope["aspect"] == "test_aspect"
        assert scope["nest_level"] == 2
        assert list(scope.keys()) == ["machine", "mode", "action", "aspect", "nest_level"]

    @pytest.mark.anyio
    async def test_passes_context(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock, context: Context
    ) -> None:
        """Контекст передаётся в emit."""
        await aspect_logger.info("msg")

        ctx = mock_coordinator.emit.call_args.kwargs["ctx"]
        assert ctx is context

    @pytest.mark.anyio
    async def test_passes_empty_state_and_params(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Если state и params не переданы — создаются пустые экземпляры."""
        await aspect_logger.info("msg")

        state = mock_coordinator.emit.call_args.kwargs["state"]
        params = mock_coordinator.emit.call_args.kwargs["params"]
        assert isinstance(state, BaseState)
        assert state.to_dict() == {}
        assert isinstance(params, BaseParams)

    @pytest.mark.anyio
    async def test_passes_indent(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """indent = nest_level (2) передаётся в emit."""
        await aspect_logger.info("msg")

        indent = mock_coordinator.emit.call_args.kwargs["indent"]
        assert indent == 2

    @pytest.mark.anyio
    async def test_multiple_calls(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Каждый вызов метода логирования приводит к отдельному emit."""
        await aspect_logger.info("First")
        await aspect_logger.warning("Second")
        await aspect_logger.error("Third")

        assert mock_coordinator.emit.await_count == 3


# ======================================================================
# ТЕСТЫ: Логгер для плагинов
# ======================================================================


class TestPluginLogger:
    """ScopedLogger в режиме плагина (с plugin_name)."""

    @pytest.fixture
    def plugin_logger(
        self, mock_coordinator: AsyncMock, context: Context
    ) -> ScopedLogger:
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
    async def test_scope_has_correct_keys(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """
        Scope плагина содержит: machine, mode, plugin, action, event, nest_level.
        Поле aspect отсутствует.
        """
        await plugin_logger.info("Plugin message")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        assert isinstance(scope, LogScope)
        assert scope["machine"] == "TestMachine"
        assert scope["mode"] == "production"
        assert scope["plugin"] == "MetricsPlugin"
        assert scope["action"] == "myapp.actions.CreateOrder"
        assert scope["event"] == "global_finish"
        assert scope["nest_level"] == 1
        assert list(scope.keys()) == [
            "machine", "mode", "plugin", "action", "event", "nest_level"
        ]
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
    async def test_passes_indent(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """indent = nest_level (1) передаётся в emit."""
        await plugin_logger.info("msg")

        indent = mock_coordinator.emit.call_args.kwargs["indent"]
        assert indent == 1

    @pytest.mark.anyio
    async def test_level_in_var(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Уровень логирования передаётся в var."""
        await plugin_logger.warning("Warning from plugin")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == "warning"

    @pytest.mark.anyio
    async def test_user_kwargs(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock
    ) -> None:
        """Пользовательские kwargs попадают в var."""
        await plugin_logger.info("msg", duration=0.5, action_count=10)

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["duration"] == 0.5
        assert var["action_count"] == 10
        assert var["level"] == "info"


# ======================================================================
# ТЕСТЫ: Передача реальных state и params
# ======================================================================


class TestWithStateAndParams:
    """ScopedLogger может получать реальные state и params."""

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
