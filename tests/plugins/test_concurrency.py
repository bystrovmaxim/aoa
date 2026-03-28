# tests/plugins/test_concurrency.py
"""
Тесты параллельного и последовательного выполнения обработчиков плагинов.

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИЯ ВЫПОЛНЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

PluginRunContext выбирает стратегию на основе флагов ignore_exceptions:

- Все ignore=True → параллельно (asyncio.gather с return_exceptions=True).
- Хотя бы один ignore=False → последовательно.

Тесты на параллельность используют ignore_exceptions=True.
Тесты на последовательность используют ignore_exceptions=False.

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


class SlowPluginIgnore(Plugin):
    """
    Плагин с паузой. ignore_exceptions=True — для тестов параллельности.
    """

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def slow_handler(self, state: dict, event: PluginEvent) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FastPluginIgnore(Plugin):
    """Быстрый плагин. ignore_exceptions=True."""

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=True)
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
    """Создаёт пустую фабрику зависимостей."""
    return DependencyFactory(())


# ─────────────────────────────────────────────────────────────────────────────
# Тесты: параллельное выполнение (все ignore=True)
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorConcurrency:
    """Тесты параллельного выполнения через PluginRunContext."""

    @pytest.mark.anyio
    async def test_all_handlers_run_concurrently(self):
        """
        Все обработчики имеют ignore_exceptions=True → параллельное выполнение.
        Два медленных обработчика по 0.05с каждый. Параллельно — ~0.05с.
        """
        slow1 = SlowPluginIgnore(delay=0.05)
        slow2 = SlowPluginIgnore(delay=0.05)
        fast = FastPluginIgnore()

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

        # Параллельно — ~0.05с. Порог 0.09с с запасом.
        assert elapsed < 0.09

        assert plugin_ctx.get_plugin_state(slow1)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(slow2)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(fast)["calls"] == ["fast"]

    @pytest.mark.anyio
    async def test_mixed_handlers_run_concurrently(self):
        """
        Все обработчики ignore=True (включая падающий) → параллельно.
        Падающий не прерывает остальных.
        """
        slow = SlowPluginIgnore(delay=0.05)
        fast = FastPluginIgnore()
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
