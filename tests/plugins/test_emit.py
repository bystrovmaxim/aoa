# tests/plugins/test_emit.py
"""
Тесты отправки событий плагинам через PluginRunContext.

Проверяется:
- Обработчики вызываются при совпадении event_name и action_filter.
- Объект PluginEvent передаётся с правильными полями.
- При отсутствии обработчиков событие не вызывает ошибок.
- Пустой список плагинов корректно обрабатывается.

Все события отправляются через PluginRunContext.emit_event(),
который создаётся через PluginCoordinator.create_run_context().
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
    """Минимальное действие для тестов."""

    @summary_aspect("dummy")
    async def summary(self, params, state, box, connections):
        return BaseResult()


class RecordingPlugin(Plugin):
    """Плагин, записывающий все полученные события."""

    async def get_initial_state(self) -> dict:
        return {"events": []}

    @on("global_finish", ".*")
    async def record_finish(self, state: dict, event: PluginEvent) -> dict:
        state["events"].append({
            "event_name": event.event_name,
            "action_name": event.action_name,
            "nest_level": event.nest_level,
        })
        return state


class SelectivePlugin(Plugin):
    """Плагин, подписанный только на конкретное действие."""

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*DummyAction$")
    async def on_dummy(self, state: dict, event: PluginEvent) -> dict:
        state["count"] += 1
        return state


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _make_empty_factory() -> DependencyFactory:
    gate = DependencyGate()
    gate.freeze()
    return DependencyFactory(gate)


async def _emit_global_finish(plugin_ctx, action=None, nest_level=0):
    """Вспомогательная функция для отправки global_finish."""
    if action is None:
        action = DummyAction()
    await plugin_ctx.emit_event(
        event_name="global_finish",
        action=action,
        params=BaseParams(),
        state_aspect=None,
        is_summary=False,
        result=None,
        duration=1.0,
        factory=_make_empty_factory(),
        context=Context(),
        nest_level=nest_level,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorEmit:
    """Тесты отправки событий через PluginRunContext."""

    @pytest.mark.anyio
    async def test_emit_event_with_handlers(self):
        """Обработчик вызывается при совпадении event_name."""
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        await _emit_global_finish(plugin_ctx)

        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["events"]) == 1
        assert state["events"][0]["event_name"] == "global_finish"

    @pytest.mark.anyio
    async def test_emit_event_passes_correct_event_object(self):
        """PluginEvent содержит правильные поля."""
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        await _emit_global_finish(plugin_ctx, nest_level=3)

        state = plugin_ctx.get_plugin_state(plugin)
        event_record = state["events"][0]
        assert event_record["nest_level"] == 3
        assert "DummyAction" in event_record["action_name"]

    @pytest.mark.anyio
    async def test_emit_event_caches_handlers(self):
        """
        Повторные вызовы emit_event корректно находят обработчики.
        (В PluginRunContext кеширование обработчиков отсутствует —
        поиск выполняется при каждом вызове.)
        """
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        await _emit_global_finish(plugin_ctx)
        await _emit_global_finish(plugin_ctx)
        await _emit_global_finish(plugin_ctx)

        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["events"]) == 3

    @pytest.mark.anyio
    async def test_emit_event_no_handlers(self):
        """Событие без подходящих обработчиков не вызывает ошибок."""
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Отправляем событие, которое не совпадает с фильтром плагина
        await plugin_ctx.emit_event(
            event_name="global_start",  # SelectivePlugin подписан только на global_finish
            action=DummyAction(),
            params=BaseParams(),
            state_aspect=None,
            is_summary=False,
            result=None,
            duration=None,
            factory=_make_empty_factory(),
            context=Context(),
            nest_level=0,
        )

        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 0

    @pytest.mark.anyio
    async def test_emit_event_empty_plugins_list(self):
        """Пустой список плагинов — emit_event завершается без ошибок."""
        coordinator = PluginCoordinator(plugins=[])
        plugin_ctx = await coordinator.create_run_context()

        await _emit_global_finish(plugin_ctx)
        # Не должно быть исключений
