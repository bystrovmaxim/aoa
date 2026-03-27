# tests/plugins/test_basic.py
"""
Тесты базовой функциональности плагинов и параллельного выполнения обработчиков.

Проверяется:
- Все обработчики запускаются параллельно через asyncio.gather
  внутри PluginRunContext.emit_event().
- Смешанные обработчики (с ignore_exceptions=True и False)
  выполняются корректно.

Состояния плагинов изолированы в PluginRunContext, который создаётся
через PluginCoordinator.create_run_context() в начале каждого теста.
"""

import asyncio

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_event import PluginEvent

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

@CheckRoles(CheckRoles.NONE, desc="")
class DummyAction(BaseAction[BaseParams, BaseResult]):
    """Минимальное действие для тестов плагинов."""

    @summary_aspect("dummy")
    async def summary(self, params, state, box, connections):
        return BaseResult()


class SlowPlugin(Plugin):
    """
    Плагин с обработчиком, который делает паузу.
    Используется для проверки параллельного выполнения.
    """

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def slow_handler(self, state: dict, event: PluginEvent) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FastPlugin(Plugin):
    """Плагин с быстрым обработчиком."""

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def fast_handler(self, state: dict, event: PluginEvent) -> dict:
        state["calls"].append("fast")
        return state


class FailingPlugin(Plugin):
    """Плагин с обработчиком, который выбрасывает исключение."""

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def failing_handler(self, state: dict, event: PluginEvent) -> dict:
        raise RuntimeError("Plugin error")


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _make_dummy_action() -> DummyAction:
    return DummyAction()


def _make_empty_factory() -> DependencyFactory:
    from action_machine.dependencies.dependency_gate import DependencyGate
    gate = DependencyGate()
    gate.freeze()
    return DependencyFactory(gate)


# ─────────────────────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorConcurrency:
    """Тесты параллельного выполнения обработчиков плагинов."""

    @pytest.mark.anyio
    async def test_all_handlers_run_concurrently(self):
        """
        Несколько обработчиков запускаются параллельно через asyncio.gather.
        Общее время должно быть близко к времени самого медленного обработчика,
        а не к сумме всех задержек.
        """
        slow1 = SlowPlugin(delay=0.05)
        slow2 = SlowPlugin(delay=0.05)
        fast = FastPlugin()

        coordinator = PluginCoordinator(plugins=[slow1, slow2, fast])
        plugin_ctx = await coordinator.create_run_context()

        action = _make_dummy_action()
        factory = _make_empty_factory()

        start = asyncio.get_event_loop().time()
        await plugin_ctx.emit_event(
            event_name="global_finish",
            action=action,
            params=BaseParams(),
            state_aspect=None,
            is_summary=False,
            result=None,
            duration=None,
            factory=factory,
            context=Context(),
            nest_level=0,
        )
        elapsed = asyncio.get_event_loop().time() - start

        # Если бы выполнялись последовательно, заняло бы ~0.1с
        # Параллельно — ~0.05с
        assert elapsed < 0.09

        # Проверяем, что все обработчики были вызваны
        state_slow1 = plugin_ctx.get_plugin_state(slow1)
        state_slow2 = plugin_ctx.get_plugin_state(slow2)
        state_fast = plugin_ctx.get_plugin_state(fast)

        assert state_slow1["calls"] == ["slow"]
        assert state_slow2["calls"] == ["slow"]
        assert state_fast["calls"] == ["fast"]

    @pytest.mark.anyio
    async def test_mixed_handlers_run_concurrently(self):
        """
        Смешанные обработчики (быстрый, медленный, падающий)
        выполняются параллельно. Падающий с ignore_exceptions=True
        не прерывает остальных.
        """
        slow = SlowPlugin(delay=0.05)
        fast = FastPlugin()
        failing = FailingPlugin()

        coordinator = PluginCoordinator(plugins=[slow, fast, failing])
        plugin_ctx = await coordinator.create_run_context()

        action = _make_dummy_action()
        factory = _make_empty_factory()

        await plugin_ctx.emit_event(
            event_name="global_finish",
            action=action,
            params=BaseParams(),
            state_aspect=None,
            is_summary=False,
            result=None,
            duration=None,
            factory=factory,
            context=Context(),
            nest_level=0,
        )

        state_slow = plugin_ctx.get_plugin_state(slow)
        state_fast = plugin_ctx.get_plugin_state(fast)

        assert state_slow["calls"] == ["slow"]
        assert state_fast["calls"] == ["fast"]
