# tests/plugins/test_concurrency.py
"""
Тесты параллельного выполнения обработчиков плагинов.

Проверяется:
- Все обработчики запускаются параллельно через asyncio.gather
  внутри PluginRunContext.emit_event().
- Смешанные обработчики (с ignore_exceptions=True и False)
  выполняются корректно.
- Общее время выполнения близко к времени самого медленного
  обработчика, а не к сумме задержек.

Состояния плагинов изолированы в PluginRunContext, создаваемом
через PluginCoordinator.create_run_context().
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
    """Минимальное действие для тестов."""

    @summary_aspect("dummy")
    async def summary(self, params, state, box, connections):
        return BaseResult()


class SlowPlugin(Plugin):
    """Плагин с обработчиком, делающим паузу."""

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
    """Плагин, обработчик которого выбрасывает исключение (ignore=True)."""

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def failing_handler(self, state: dict, event: PluginEvent) -> dict:
        raise RuntimeError("Plugin error")


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _make_empty_factory() -> DependencyFactory:
    """Создаёт пустую замороженную фабрику зависимостей."""
    gate = DependencyGate()
    gate.freeze()
    return DependencyFactory(gate)


# ─────────────────────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorConcurrency:
    """Тесты параллельного выполнения обработчиков через PluginRunContext."""

    @pytest.mark.anyio
    async def test_all_handlers_run_concurrently(self):
        """
        Несколько медленных обработчиков запускаются параллельно.
        Общее время ~0.05с (время одного), а не ~0.1с (сумма).
        """
        slow1 = SlowPlugin(delay=0.05)
        slow2 = SlowPlugin(delay=0.05)
        fast = FastPlugin()

        coordinator = PluginCoordinator(plugins=[slow1, slow2, fast])
        plugin_ctx = await coordinator.create_run_context()

        action = DummyAction()
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

        assert elapsed < 0.09

        assert plugin_ctx.get_plugin_state(slow1)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(slow2)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(fast)["calls"] == ["fast"]

    @pytest.mark.anyio
    async def test_mixed_handlers_run_concurrently(self):
        """
        Смешанные обработчики: быстрый, медленный, падающий (ignore=True).
        Падающий не прерывает остальных.
        """
        slow = SlowPlugin(delay=0.05)
        fast = FastPlugin()
        failing = FailingPlugin()

        coordinator = PluginCoordinator(plugins=[slow, fast, failing])
        plugin_ctx = await coordinator.create_run_context()

        action = DummyAction()
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

        assert plugin_ctx.get_plugin_state(slow)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(fast)["calls"] == ["fast"]
