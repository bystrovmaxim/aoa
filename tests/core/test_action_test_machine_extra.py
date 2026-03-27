# tests/core/test_action_test_machine_extra.py
"""
Дополнительные тесты для ActionTestMachine.

Проверяется:
- Подготовка моков (_prepare_mock) для всех поддерживаемых типов:
  MockAction, BaseAction, BaseResult, callable, произвольный объект.
- Прямой запуск MockAction через run() (обход конвейера аспектов).
- Метод run_with_context() для доступа к состоянию плагинов.
- Изоляция состояний плагинов между вызовами run_with_context().

Состояния плагинов изолированы в PluginRunContext: каждый вызов run()
или run_with_context() создаёт новый контекст с начальными состояниями,
полученными через get_initial_state().
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
from action_machine.core.mock_action import MockAction
from action_machine.core.tools_box import ToolsBox
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


@CheckRoles(CheckRoles.NONE, desc="Без аутентификации")
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
    """Тестовый плагин-счётчик для проверки изоляции состояний."""

    async def get_initial_state(self) -> dict[str, int]:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def count_call(self, state: dict[str, int], event: PluginEvent) -> dict[str, int]:
        state["count"] = state.get("count", 0) + 1
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
        """run_with_context() возвращает кортеж (result, plugin_ctx)."""
        result, plugin_ctx = await self.machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        assert isinstance(result, DummyResult)
        assert result["executed"] is True

        # Проверяем состояние плагина
        state = plugin_ctx.get_plugin_state(self.counter_plugin)
        assert state["count"] == 1

    @pytest.mark.anyio
    async def test_plugin_states_isolated_between_runs(self):
        """
        Каждый вызов run_with_context() создаёт изолированный PluginRunContext.
        Состояние плагина начинается с начального значения (count=0)
        в каждом новом запросе.
        """
        # Первый запрос
        result1, ctx1 = await self.machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )
        state1 = ctx1.get_plugin_state(self.counter_plugin)
        assert state1["count"] == 1

        # Второй запрос — новый контекст, новое начальное состояние
        result2, ctx2 = await self.machine.run_with_context(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )
        state2 = ctx2.get_plugin_state(self.counter_plugin)
        assert state2["count"] == 1  # 1, а не 2 — изоляция

        # Старый контекст не изменился
        state1_again = ctx1.get_plugin_state(self.counter_plugin)
        assert state1_again["count"] == 1

    @pytest.mark.anyio
    async def test_run_with_context_mock_action(self):
        """
        run_with_context() с MockAction создаёт пустой PluginRunContext
        (без отправки событий) и возвращает результат мока.
        """
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

        # PluginRunContext создан, но события не отправлялись
        state = plugin_ctx.get_plugin_state(self.counter_plugin)
        assert state["count"] == 0  # начальное состояние, без изменений

    @pytest.mark.anyio
    async def test_regular_run_does_not_expose_plugin_ctx(self):
        """
        Обычный run() возвращает только результат (обратная совместимость).
        PluginRunContext создаётся внутри и уничтожается после завершения.
        """
        result = await self.machine.run(
            context=self.context,
            action=SimpleSummaryAction(),
            params=DummyParams(),
        )

        assert isinstance(result, DummyResult)
        assert result["executed"] is True
        # Нет способа получить plugin_ctx через обычный run()


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: множественные плагины
# ─────────────────────────────────────────────────────────────────────────────

class AnotherCounterPlugin(Plugin):
    """Второй плагин-счётчик для проверки независимости состояний."""

    async def get_initial_state(self) -> dict[str, int]:
        return {"total": 0}

    @on("global_finish", ".*")
    async def track(self, state: dict[str, int], event: PluginEvent) -> dict[str, int]:
        state["total"] = state.get("total", 0) + 1
        return state


class TestMultiplePlugins:
    """Тесты изоляции состояний для нескольких плагинов."""

    @pytest.mark.anyio
    async def test_multiple_plugins_independent_states(self):
        """Каждый плагин имеет независимое состояние в PluginRunContext."""
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

        # Состояния независимы: у plugin_a нет "total", у plugin_b нет "count"
        assert "total" not in state_a
        assert "count" not in state_b
