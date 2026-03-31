# tests/core/test_action_test_machine.py
"""
Тесты для ActionTestMachine.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Подготовка моков (_prepare_mock) для всех поддерживаемых типов:
  MockAction, BaseAction, BaseResult, callable, произвольный объект.
- Прямой запуск MockAction через run() (обход конвейера аспектов).
- Метод run_with_context() для доступа к состоянию плагинов.
- Изоляция состояний плагинов между вызовами run_with_context().
- Логгер в обработчиках плагинов: все обработчики получают ScopedLogger
  с scope плагина через параметр log.
- Множественные плагины с независимыми состояниями.
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_test_machine import ActionTestMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.mock_action import MockAction
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_event import PluginEvent
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

class DummyParams(BaseParams):
    pass


class DummyResult(BaseResult):
    pass


class DummyAction(BaseAction[DummyParams, DummyResult]):
    pass


@meta(description="Минимальное действие с одним summary-аспектом для тестов")
@CheckRoles(CheckRoles.NONE)
class SimpleSummaryAction(BaseAction[DummyParams, DummyResult]):
    """Минимальное действие с одним summary-аспектом для тестов."""

    @summary_aspect("simple summary")
    async def summary(
        self,
        params: DummyParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> DummyResult:
        result = DummyResult()
        result["executed"] = True
        return result


class TestCounterPlugin(Plugin):
    """Тестовый плагин-счётчик. Сигнатура обработчика: (self, state, event, log)."""

    async def get_initial_state(self) -> dict[str, int]:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def count_call(
        self, state: dict[str, int], event: PluginEvent, log: ScopedLogger,
    ) -> dict[str, int]:
        state["count"] = state.get("count", 0) + 1
        return state


class TestCounterPluginWithLogging(Plugin):
    """
    Тестовый плагин-счётчик с логированием.

    Обработчик использует ScopedLogger для записи в подсистему логирования
    машины. Сохраняет факт логирования в state для проверки в тестах.
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0, "logged_messages": []}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def count_call(
        self, state: dict, event: PluginEvent, log: ScopedLogger,
    ) -> dict:
        state["count"] = state.get("count", 0) + 1
        await log.info(
            "Вызов #{%var.count} действия {%scope.action}",
            count=state["count"],
        )
        state["logged_messages"].append(f"call_{state['count']}")
        return state


class TestPluginMultipleEvents(Plugin):
    """
    Плагин с обработчиками на разные события.

    Проверяет, что каждый обработчик получает свой ScopedLogger
    с правильным event_name в scope.
    """

    async def get_initial_state(self) -> dict:
        return {"start_count": 0, "finish_count": 0}

    @on("global_start", ".*")
    async def on_start(self, state: dict, event: PluginEvent, log: ScopedLogger) -> dict:
        state["start_count"] += 1
        await log.info("[{%scope.plugin}] Старт действия {%scope.action}")
        return state

    @on("global_finish", ".*")
    async def on_finish(self, state: dict, event: PluginEvent, log: ScopedLogger) -> dict:
        state["finish_count"] += 1
        await log.info("[{%scope.plugin}] Финиш действия {%scope.action}")
        return state


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: _prepare_mock
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_action_test_machine_prepare_mock():
    """Проверка _prepare_mock для всех поддерживаемых типов mock-значений."""
    machine = ActionTestMachine()

    # MockAction → используется как есть
    ma = MockAction()
    assert machine._prepare_mock(ma) is ma

    # BaseAction → используется как есть
    ba = DummyAction()
    assert machine._prepare_mock(ba) is ba

    # BaseResult → оборачивается в MockAction(result=...)
    res = DummyResult()
    pm1 = machine._prepare_mock(res)
    assert isinstance(pm1, MockAction)
    assert pm1.result is res

    # callable → оборачивается в MockAction(side_effect=...)
    def side_eff(p):
        return res
    pm2 = machine._prepare_mock(side_eff)
    assert isinstance(pm2, MockAction)
    assert pm2.side_effect is side_eff

    # Произвольный объект → используется как есть
    assert machine._prepare_mock("plain_string") == "plain_string"
    assert machine._prepare_mock(42) == 42
    assert machine._prepare_mock({"key": "value"}) == {"key": "value"}

    # Запуск MockAction напрямую (обходит конвейер)
    result = await machine.run(None, pm1, DummyParams())
    assert result is res


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: run_with_context и изоляция состояний плагинов
# ─────────────────────────────────────────────────────────────────────────────

class TestRunWithContext:
    """Тесты метода run_with_context() для доступа к состоянию плагинов."""

    def setup_method(self):
        self.counter_plugin = TestCounterPlugin()
        self.machine = ActionTestMachine(mode="test")
        self.machine._plugin_coordinator = PluginCoordinator(
            plugins=[self.counter_plugin],
        )
        self.context = Context(
            user=UserInfo(user_id="test_user", roles=["user"])
        )

    @pytest.mark.anyio
    async def test_run_with_context_returns_result_and_plugin_ctx(self):
        result, plugin_ctx = await self.machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        assert isinstance(result, DummyResult)
        assert result["executed"] is True

        state = plugin_ctx.get_plugin_state(self.counter_plugin)
        assert state["count"] == 1

    @pytest.mark.anyio
    async def test_plugin_states_isolated_between_runs(self):
        """Каждый вызов run_with_context() создаёт изолированный контекст."""
        result1, ctx1 = await self.machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )
        state1 = ctx1.get_plugin_state(self.counter_plugin)
        assert state1["count"] == 1

        result2, ctx2 = await self.machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )
        state2 = ctx2.get_plugin_state(self.counter_plugin)
        assert state2["count"] == 1  # 1, а не 2 — изоляция

        state1_again = ctx1.get_plugin_state(self.counter_plugin)
        assert state1_again["count"] == 1

    @pytest.mark.anyio
    async def test_run_with_context_mock_action(self):
        mock_result = DummyResult()
        mock_result["mock"] = True
        mock_action = MockAction(result=mock_result)

        result, plugin_ctx = await self.machine.run_with_context(
            context=self.context,
            action=mock_action,
            params=DummyParams(),
        )

        assert result is mock_result
        assert result["mock"] is True

        state = plugin_ctx.get_plugin_state(self.counter_plugin)
        assert state["count"] == 0  # начальное состояние, без изменений

    @pytest.mark.anyio
    async def test_regular_run_does_not_expose_plugin_ctx(self):
        result = await self.machine.run(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        assert isinstance(result, DummyResult)
        assert result["executed"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: логгер в обработчиках плагинов
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginHandlerWithLog:
    """
    Тесты для обработчиков плагинов с параметром log.

    Все обработчики получают ScopedLogger и могут логировать через него.
    """

    def setup_method(self):
        self.context = Context(
            user=UserInfo(user_id="test_user", roles=["user"])
        )

    @pytest.mark.anyio
    async def test_plugin_receives_scoped_logger(self):
        """Обработчик получает ScopedLogger и работает корректно."""
        plugin = TestCounterPluginWithLogging()
        machine = ActionTestMachine(mode="test")
        machine._plugin_coordinator = PluginCoordinator(plugins=[plugin])

        result, plugin_ctx = await machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 1
        assert state["logged_messages"] == ["call_1"]

    @pytest.mark.anyio
    async def test_plugin_multiple_events_each_gets_logger(self):
        """
        Плагин с обработчиками на разные события: каждый обработчик
        получает свой ScopedLogger.
        """
        plugin = TestPluginMultipleEvents()
        machine = ActionTestMachine(mode="test")
        machine._plugin_coordinator = PluginCoordinator(plugins=[plugin])

        result, plugin_ctx = await machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        state = plugin_ctx.get_plugin_state(plugin)
        assert state["start_count"] == 1
        assert state["finish_count"] == 1

    @pytest.mark.anyio
    async def test_plugin_log_multiple_runs_isolated(self):
        """
        Логгер создаётся заново при каждом emit_event.
        Состояния плагинов изолированы между запусками.
        """
        plugin = TestCounterPluginWithLogging()
        machine = ActionTestMachine(mode="test")
        machine._plugin_coordinator = PluginCoordinator(plugins=[plugin])

        # Первый запуск
        _, ctx1 = await machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )
        state1 = ctx1.get_plugin_state(plugin)
        assert state1["count"] == 1
        assert state1["logged_messages"] == ["call_1"]

        # Второй запуск — изолирован
        _, ctx2 = await machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )
        state2 = ctx2.get_plugin_state(plugin)
        assert state2["count"] == 1  # 1, а не 2
        assert state2["logged_messages"] == ["call_1"]  # не ["call_1", "call_2"]


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: множественные плагины
# ─────────────────────────────────────────────────────────────────────────────

class AnotherCounterPlugin(Plugin):
    """Второй плагин-счётчик для проверки независимости состояний."""

    async def get_initial_state(self) -> dict[str, int]:
        return {"total": 0}

    @on("global_finish", ".*")
    async def track(
        self, state: dict[str, int], event: PluginEvent, log: ScopedLogger,
    ) -> dict[str, int]:
        state["total"] = state.get("total", 0) + 1
        return state


class TestMultiplePlugins:
    """Тесты изоляции состояний для нескольких плагинов."""

    @pytest.mark.anyio
    async def test_multiple_plugins_independent_states(self):
        plugin_a = TestCounterPlugin()
        plugin_b = AnotherCounterPlugin()

        machine = ActionTestMachine(mode="test")
        machine._plugin_coordinator = PluginCoordinator(
            plugins=[plugin_a, plugin_b],
        )

        context = Context(user=UserInfo(user_id="test", roles=["user"]))

        result, plugin_ctx = await machine.run_with_context(
            context=context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        state_a = plugin_ctx.get_plugin_state(plugin_a)
        state_b = plugin_ctx.get_plugin_state(plugin_b)

        assert state_a["count"] == 1
        assert state_b["total"] == 1

        assert "total" not in state_a
        assert "count" not in state_b

    @pytest.mark.anyio
    async def test_multiple_plugins_all_with_logging(self):
        """Несколько плагинов с логированием работают вместе без конфликтов."""
        plugin_counter = TestCounterPluginWithLogging()
        plugin_events = TestPluginMultipleEvents()

        machine = ActionTestMachine(mode="test")
        machine._plugin_coordinator = PluginCoordinator(
            plugins=[plugin_counter, plugin_events],
        )

        context = Context(user=UserInfo(user_id="test", roles=["user"]))

        result, plugin_ctx = await machine.run_with_context(
            context=context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        state_counter = plugin_ctx.get_plugin_state(plugin_counter)
        state_events = plugin_ctx.get_plugin_state(plugin_events)

        assert state_counter["count"] == 1
        assert state_counter["logged_messages"] == ["call_1"]
        assert state_events["start_count"] == 1
        assert state_events["finish_count"] == 1
