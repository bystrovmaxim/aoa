# tests/plugins/test_handlers.py
"""
Тесты выполнения обработчиков плагинов и управления состояниями.

Проверяется:
- Запуск одного обработчика обновляет состояние плагина.
- Запуск нескольких обработчиков одного плагина обновляет состояние
  последовательно.
- Независимость состояний разных плагинов.
- Инициализация начальных состояний через get_initial_state().
- Идемпотентность: повторное создание контекста даёт свежие состояния.

Все операции выполняются через PluginRunContext, создаваемый
через PluginCoordinator.create_run_context().
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.dependencies.dependency_gate import DependencyGate
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_event import PluginEvent

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

@CheckRoles(CheckRoles.NONE, desc="")
class DummyAction(BaseAction[BaseParams, BaseResult]):
    @summary_aspect("dummy")
    async def summary(self, params, state, box, connections):
        return BaseResult()


class CounterPlugin(Plugin):
    """Плагин-счётчик с одним обработчиком."""

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def count(self, state: dict, event: PluginEvent) -> dict:
        state["count"] += 1
        return state


class DualHandlerPlugin(Plugin):
    """Плагин с двумя обработчиками на одно событие."""

    async def get_initial_state(self) -> dict:
        return {"a": 0, "b": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def handler_a(self, state: dict, event: PluginEvent) -> dict:
        state["a"] += 1
        return state

    @on("global_finish", ".*", ignore_exceptions=False)
    async def handler_b(self, state: dict, event: PluginEvent) -> dict:
        state["b"] += 10
        return state


class CustomInitPlugin(Plugin):
    """Плагин с кастомным начальным состоянием."""

    def __init__(self, initial_value: int = 100):
        self._initial = initial_value

    async def get_initial_state(self) -> dict:
        return {"value": self._initial}

    @on("global_finish", ".*")
    async def increment(self, state: dict, event: PluginEvent) -> dict:
        state["value"] += 1
        return state


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _make_empty_factory() -> DependencyFactory:
    gate = DependencyGate()
    gate.freeze()
    return DependencyFactory(gate)


async def _emit_global_finish(plugin_ctx):
    await plugin_ctx.emit_event(
        event_name="global_finish",
        action=DummyAction(),
        params=BaseParams(),
        state_aspect=None,
        is_summary=False,
        result=None,
        duration=1.0,
        factory=_make_empty_factory(),
        context=Context(),
        nest_level=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: запуск обработчиков
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorRunHandlers:
    """Тесты выполнения обработчиков и обновления состояний."""

    @pytest.mark.anyio
    async def test_run_single_handler(self):
        """Один обработчик обновляет состояние плагина."""
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        await _emit_global_finish(plugin_ctx)

        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 1

    @pytest.mark.anyio
    async def test_run_multiple_handlers_same_plugin(self):
        """
        Два обработчика одного плагина на одно событие:
        оба выполняются и обновляют общее состояние.
        """
        plugin = DualHandlerPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        await _emit_global_finish(plugin_ctx)

        state = plugin_ctx.get_plugin_state(plugin)
        assert state["a"] == 1
        assert state["b"] == 10

    @pytest.mark.anyio
    async def test_plugins_independent_states(self):
        """Разные плагины имеют независимые состояния."""
        counter = CounterPlugin()
        dual = DualHandlerPlugin()
        coordinator = PluginCoordinator(plugins=[counter, dual])
        plugin_ctx = await coordinator.create_run_context()

        await _emit_global_finish(plugin_ctx)

        counter_state = plugin_ctx.get_plugin_state(counter)
        dual_state = plugin_ctx.get_plugin_state(dual)

        assert counter_state["count"] == 1
        assert "a" not in counter_state
        assert dual_state["a"] == 1
        assert dual_state["b"] == 10
        assert "count" not in dual_state


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: инициализация состояний
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorStates:
    """Тесты инициализации и изоляции начальных состояний."""

    @pytest.mark.anyio
    async def test_init_plugin_states(self):
        """create_run_context() инициализирует состояния всех плагинов."""
        counter = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[counter])
        plugin_ctx = await coordinator.create_run_context()

        state = plugin_ctx.get_plugin_state(counter)
        assert state == {"count": 0}

    @pytest.mark.anyio
    async def test_init_plugin_states_with_custom_initial(self):
        """Кастомное начальное состояние через конструктор плагина."""
        plugin = CustomInitPlugin(initial_value=42)
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        state = plugin_ctx.get_plugin_state(plugin)
        assert state == {"value": 42}

    @pytest.mark.anyio
    async def test_init_plugin_states_idempotent(self):
        """
        Повторный вызов create_run_context() создаёт новый контекст
        с начальными состояниями, независимый от предыдущего.
        """
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])

        # Первый контекст
        ctx1 = await coordinator.create_run_context()
        await _emit_global_finish(ctx1)
        state1 = ctx1.get_plugin_state(plugin)
        assert state1["count"] == 1

        # Второй контекст — свежее начальное состояние
        ctx2 = await coordinator.create_run_context()
        state2 = ctx2.get_plugin_state(plugin)
        assert state2["count"] == 0  # начальное, а не 1

        # Первый контекст не изменился
        assert ctx1.get_plugin_state(plugin)["count"] == 1
