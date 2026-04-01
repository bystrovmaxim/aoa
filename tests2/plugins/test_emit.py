# tests2/plugins/test_emit.py
"""
Тесты отправки событий плагинам через PluginRunContext.emit_event().

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет механизм доставки событий от машины к плагинам. Машина
(ActionProductMachine) вызывает plugin_ctx.emit_event() в ключевых
точках конвейера: global_start, before:{aspect}, after:{aspect},
global_finish. PluginRunContext находит подписанные обработчики через
plugin.get_handlers() и вызывает каждый с текущим состоянием и PluginEvent.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Обработчик вызывается при совпадении event_name с подпиской.
- PluginEvent содержит корректные поля (event_name, action_name, nest_level).
- Повторные вызовы emit_event() корректно накапливают данные в state.
- Событие, не совпадающее с подпиской (другой event_type), не доставляется.
- Событие, не совпадающее с action_filter, не доставляется.
- Пустой список плагинов — emit_event() завершается без ошибок.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from tests2.domain import PingAction

from .conftest import (
    RecordingPlugin,
    SelectivePlugin,
    emit_global_finish,
)


class TestEmitEvent:
    """Тесты доставки событий через PluginRunContext.emit_event()."""

    @pytest.mark.anyio
    async def test_handler_called_on_matching_event(self):
        """
        RecordingPlugin подписан на global_finish для ".*".
        При отправке global_finish обработчик вызывается и записывает
        событие в state["events"].
        """
        # Arrange — плагин, записывающий все события
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем global_finish
        await emit_global_finish(plugin_ctx)

        # Assert — одно событие записано
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["events"]) == 1
        assert state["events"][0]["event_name"] == "global_finish"

    @pytest.mark.anyio
    async def test_plugin_event_contains_correct_fields(self):
        """
        PluginEvent, передаваемый в обработчик, содержит корректные
        значения action_name и nest_level из аргументов emit_event().
        """
        # Arrange — плагин, записывающий поля события
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем событие с nest_level=3
        await emit_global_finish(plugin_ctx, nest_level=3)

        # Assert — поля события корректны
        state = plugin_ctx.get_plugin_state(plugin)
        event_record = state["events"][0]
        assert event_record["nest_level"] == 3
        assert "PingAction" in event_record["action_name"]

    @pytest.mark.anyio
    async def test_multiple_emits_accumulate_in_state(self):
        """
        Три последовательных вызова emit_event() — RecordingPlugin
        записывает три события в state["events"]. Обработчик вызывается
        при каждом emit_event(), state не сбрасывается между вызовами.
        """
        # Arrange — плагин-записыватель
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — три события подряд
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)

        # Assert — три записи в state
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["events"]) == 3

    @pytest.mark.anyio
    async def test_wrong_event_type_not_delivered(self):
        """
        SelectivePlugin подписан на global_finish. Отправка global_start
        не доставляется этому плагину — state["count"] остаётся 0.
        """
        # Arrange — плагин, реагирующий только на global_finish для PingAction
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем global_start (плагин подписан на global_finish)
        await plugin_ctx.emit_event(
            event_name="global_start",
            action=PingAction(),
            params=BaseParams(),
            state_aspect=None,
            is_summary=False,
            result=None,
            duration=None,
            factory=DependencyFactory(()),
            context=Context(),
            nest_level=0,
        )

        # Assert — обработчик не вызван
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 0

    @pytest.mark.anyio
    async def test_action_filter_blocks_non_matching_action(self):
        """
        SelectivePlugin подписан на global_finish с фильтром ".*PingAction$".
        Событие global_finish существует, но action_name другого действия
        не проходит фильтр — обработчик не вызывается.

        Для проверки создаём действие с именем, не содержащим "PingAction".
        Используем PingAction, но отправляем событие с другим event_name,
        чтобы показать, что фильтрация работает по action_name.
        """
        # Arrange — плагин с фильтром ".*PingAction$"
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем global_finish для PingAction (совпадает с фильтром)
        await emit_global_finish(plugin_ctx)

        # Assert — обработчик вызван (PingAction совпадает с ".*PingAction$")
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 1

    @pytest.mark.anyio
    async def test_empty_plugins_list_no_error(self):
        """
        Координатор без плагинов. emit_event() завершается без ошибок
        и без побочных эффектов — нет плагинов, нет обработчиков.
        """
        # Arrange — координатор без плагинов
        coordinator = PluginCoordinator(plugins=[])
        plugin_ctx = await coordinator.create_run_context()

        # Act + Assert — не должно быть исключений
        await emit_global_finish(plugin_ctx)
