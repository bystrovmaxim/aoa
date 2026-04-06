# tests/plugins/test_emit.py
"""
Тесты отправки событий плагинам через PluginRunContext.emit_event().
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет механизм доставки типизированных событий от машины к плагинам.
Машина (ActionProductMachine) создаёт конкретные объекты событий из
иерархии BasePluginEvent (GlobalStartEvent, GlobalFinishEvent,
BeforeRegularAspectEvent и т.д.) в ключевых точках конвейера и передаёт
их в plugin_ctx.emit_event(event) [1].

PluginRunContext находит подписанные обработчики через plugin.get_handlers()
(шаг 1: isinstance по event_class), проверяет остальные фильтры
(шаги 2–7) и вызывает каждый обработчик с текущим состоянием
и типизированным объектом события [1].

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════
- Обработчик вызывается при совпадении event_class с подпиской.
- Объект события содержит корректные поля (event_type, action_name,
  nest_level, duration_ms).
- Повторные вызовы emit_event() корректно накапливают данные в state.
- Событие другого типа (GlobalStartEvent вместо GlobalFinishEvent)
  не доставляется обработчику, подписанному на GlobalFinishEvent.
- action_name_pattern корректно фильтрует по имени действия.
- Пустой список плагинов — emit_event() завершается без ошибок.
"""
import pytest

from action_machine.plugins.plugin_coordinator import PluginCoordinator

from .conftest import (
    RecordingPlugin,
    SelectivePlugin,
    emit_global_finish,
    emit_global_start,
)


class TestEmitEvent:
    """Тесты доставки типизированных событий через PluginRunContext.emit_event()."""

    @pytest.mark.anyio
    async def test_handler_called_on_matching_event(self):
        """
        RecordingPlugin подписан на GlobalFinishEvent.
        При отправке GlobalFinishEvent обработчик вызывается и записывает
        событие в state["events"].
        """
        # Arrange — плагин, записывающий все события
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем GlobalFinishEvent
        await emit_global_finish(plugin_ctx)

        # Assert — одно событие записано с правильным типом
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["events"]) == 1
        assert state["events"][0]["event_type"] == "GlobalFinishEvent"

    @pytest.mark.anyio
    async def test_event_contains_correct_fields(self):
        """
        Типизированный объект GlobalFinishEvent, передаваемый в обработчик,
        содержит корректные значения action_name, nest_level и duration_ms
        из аргументов конструктора события.
        """
        # Arrange — плагин, записывающий поля события
        plugin = RecordingPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем событие с nest_level=3 и duration_ms=42.5
        await emit_global_finish(plugin_ctx, nest_level=3, duration_ms=42.5)

        # Assert — поля события корректны
        state = plugin_ctx.get_plugin_state(plugin)
        event_record = state["events"][0]
        assert event_record["nest_level"] == 3
        assert event_record["duration_ms"] == 42.5
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
        SelectivePlugin подписан на GlobalFinishEvent с action_name_pattern.
        Отправка GlobalStartEvent не доставляется — isinstance(event,
        GlobalFinishEvent) возвращает False на шаге 1 цепочки фильтров.
        state["order_events"] остаётся пустым.
        """
        # Arrange — плагин, реагирующий только на GlobalFinishEvent
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем GlobalStartEvent (плагин подписан на GlobalFinishEvent)
        await emit_global_start(plugin_ctx)

        # Assert — обработчик не вызван (event_class не совпадает)
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["order_events"] == []

    @pytest.mark.anyio
    async def test_action_name_pattern_filters_matching_action(self):
        """
        SelectivePlugin подписан на GlobalFinishEvent с
        action_name_pattern=".*Order.*". Событие с action_name
        содержащим "Order" доставляется обработчику.
        """
        # Arrange — плагин с фильтром ".*Order.*"
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем GlobalFinishEvent с "Order" в action_name
        await emit_global_finish(
            plugin_ctx,
            action_name="app.actions.CreateOrderAction",
        )

        # Assert — обработчик вызван (action_name совпадает с паттерном)
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["order_events"]) == 1
        assert state["order_events"][0] == "app.actions.CreateOrderAction"

    @pytest.mark.anyio
    async def test_action_name_pattern_blocks_non_matching_action(self):
        """
        SelectivePlugin подписан на GlobalFinishEvent с
        action_name_pattern=".*Order.*". Событие с action_name
        НЕ содержащим "Order" не доставляется обработчику.
        """
        # Arrange — плагин с фильтром ".*Order.*"
        plugin = SelectivePlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем GlobalFinishEvent без "Order" в action_name
        await emit_global_finish(
            plugin_ctx,
            action_name="app.actions.PingAction",
        )

        # Assert — обработчик не вызван (action_name не совпадает)
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["order_events"] == []

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
