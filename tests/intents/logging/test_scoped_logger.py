# tests/intents/logging/test_scoped_logger.py
"""Tests ScopedLogger - a logger tied to the scope of the current aspect or plugin.

Covered Scenarios:
- info/warning/critical add LogLevelPayload / LogChannelPayload, domain, domain_name to var.
- The first argument is Channel.
- Reserved keys in kwargs → ValueError.
- LogScope for aspects and plugins.
- One emit per call."""

from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.logging.channel import Channel, channel_mask_label
from action_machine.logging.level import Level, level_label
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState


@pytest.fixture
def mock_coordinator() -> AsyncMock:
    coordinator = AsyncMock(spec=LogCoordinator)
    coordinator.emit = AsyncMock()
    return coordinator


@pytest.fixture
def context() -> Context:
    return Context()


class TestAspectLogger:
    @pytest.fixture
    def aspect_logger(
        self, mock_coordinator: AsyncMock, context: Context,
    ) -> ScopedLogger:
        return ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=2,
            action_name="myapp.actions.TestAction",
            aspect_name="test_aspect",
            context=context,
            domain=None,
        )

    @pytest.mark.anyio
    async def test_info_adds_level_and_channels(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.info(
            Channel.business, "Test message", user="john", count=42,
        )

        mock_coordinator.emit.assert_awaited_once()
        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"] == LogLevelPayload(
            mask=Level.info, name=level_label(Level.info),
        )
        assert var["channels"] == LogChannelPayload(
            mask=Channel.business, names=channel_mask_label(Channel.business),
        )
        assert var["domain"] is None
        assert var["domain_name"] is None
        assert var["user"] == "john"
        assert var["count"] == 42

    @pytest.mark.anyio
    async def test_warning_adds_level_warning(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.warning(Channel.debug, "Warning message")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"].mask == Level.warning
        assert var["channels"].mask == Channel.debug

    @pytest.mark.anyio
    async def test_critical_adds_level_critical(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.critical(Channel.error, "Critical message")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"].mask == Level.critical
        assert var["channels"].mask == Channel.error

    @pytest.mark.anyio
    async def test_user_kwargs_are_passed(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.info(
            Channel.debug,
            "msg",
            extra="data",
            flag=True,
            amount=100.5,
        )

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["extra"] == "data"
        assert var["flag"] is True
        assert var["amount"] == 100.5
        assert var["level"].mask == Level.info

    @pytest.mark.anyio
    async def test_reserved_level_in_kwargs_raises(
        self, aspect_logger: ScopedLogger,
    ) -> None:
        with pytest.raises(ValueError, match="Reserved keys"):
            await aspect_logger.info(Channel.debug, "msg", level="user_level")

    @pytest.mark.anyio
    async def test_scope_has_correct_keys(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.info(Channel.debug, "msg")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        assert isinstance(scope, LogScope)
        assert scope["action"] == "myapp.actions.TestAction"
        assert scope["aspect"] == "test_aspect"
        assert scope["nest_level"] == 2
        assert list(scope.keys()) == [
            "action", "aspect", "nest_level",
        ]

    @pytest.mark.anyio
    async def test_passes_context(
        self,
        aspect_logger: ScopedLogger,
        mock_coordinator: AsyncMock,
        context: Context,
    ) -> None:
        await aspect_logger.info(Channel.debug, "msg")

        ctx = mock_coordinator.emit.call_args.kwargs["ctx"]
        assert ctx is context

    @pytest.mark.anyio
    async def test_passes_empty_state_and_params(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.info(Channel.debug, "msg")

        state = mock_coordinator.emit.call_args.kwargs["state"]
        params = mock_coordinator.emit.call_args.kwargs["params"]
        assert isinstance(state, BaseState)
        assert state.to_dict() == {}
        assert isinstance(params, BaseParams)

    @pytest.mark.anyio
    async def test_passes_indent(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.info(Channel.debug, "msg")

        indent = mock_coordinator.emit.call_args.kwargs["indent"]
        assert indent == 2

    @pytest.mark.anyio
    async def test_multiple_calls(
        self, aspect_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await aspect_logger.info(Channel.debug, "First")
        await aspect_logger.warning(Channel.business, "Second")
        await aspect_logger.critical(Channel.error, "Third")

        assert mock_coordinator.emit.await_count == 3


class TestPluginLogger:
    @pytest.fixture
    def plugin_logger(
        self, mock_coordinator: AsyncMock, context: Context,
    ) -> ScopedLogger:
        return ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=1,
            action_name="myapp.actions.CreateOrder",
            aspect_name="",
            context=context,
            plugin_name="MetricsPlugin",
            event_name="global_finish",
            domain=None,
        )

    @pytest.mark.anyio
    async def test_scope_has_correct_keys(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await plugin_logger.info(Channel.debug, "Plugin message")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        assert isinstance(scope, LogScope)
        assert scope["plugin"] == "MetricsPlugin"
        assert scope["action"] == "myapp.actions.CreateOrder"
        assert scope["event"] == "global_finish"
        assert scope["nest_level"] == 1
        assert list(scope.keys()) == [
            "plugin", "action", "event", "nest_level",
        ]
        assert "aspect" not in scope

    @pytest.mark.anyio
    async def test_plugin_scope_dotpath(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await plugin_logger.info(Channel.debug, "msg")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        dotpath = scope.as_dotpath()
        expected = "MetricsPlugin.myapp.actions.CreateOrder.global_finish.1"
        assert dotpath == expected

    @pytest.mark.anyio
    async def test_passes_indent(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await plugin_logger.info(Channel.debug, "msg")

        indent = mock_coordinator.emit.call_args.kwargs["indent"]
        assert indent == 1

    @pytest.mark.anyio
    async def test_level_in_var(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await plugin_logger.warning(Channel.security, "Warning from plugin")

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["level"].mask == Level.warning
        assert var["channels"].mask == Channel.security

    @pytest.mark.anyio
    async def test_user_kwargs(
        self, plugin_logger: ScopedLogger, mock_coordinator: AsyncMock,
    ) -> None:
        await plugin_logger.info(
            Channel.debug,
            "msg",
            duration=0.5,
            action_count=10,
        )

        var = mock_coordinator.emit.call_args.kwargs["var"]
        assert var["duration"] == 0.5
        assert var["action_count"] == 10
        assert var["level"].mask == Level.info


class TestWithStateAndParams:
    @pytest.mark.anyio
    async def test_custom_state_and_params_passed(
        self, mock_coordinator: AsyncMock, context: Context,
    ) -> None:
        state = BaseState(total=1500.0, count=5)
        params = BaseParams()

        logger = ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=0,
            action_name="Action",
            aspect_name="aspect",
            context=context,
            state=state,
            params=params,
            domain=None,
        )

        await logger.info(Channel.debug, "msg")

        emitted_state = mock_coordinator.emit.call_args.kwargs["state"]
        emitted_params = mock_coordinator.emit.call_args.kwargs["params"]

        assert emitted_state is state
        assert emitted_state.to_dict() == {"total": 1500.0, "count": 5}
        assert emitted_params is params

    @pytest.mark.anyio
    async def test_nest_level_zero_in_scope(
        self, mock_coordinator: AsyncMock, context: Context,
    ) -> None:
        logger = ScopedLogger(
            coordinator=mock_coordinator,
            nest_level=0,
            action_name="RootAction",
            aspect_name="summary",
            context=context,
            domain=None,
        )

        await logger.info(Channel.business, "msg")

        scope = mock_coordinator.emit.call_args.kwargs["scope"]
        assert scope["nest_level"] == 0
        assert scope["nest_level"] == 0
