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
- Подписка на события компенсации (Saga): CompensateFailedEvent,
  SagaRollbackCompletedEvent — обработчики вызываются корректно.
"""
import pytest

from action_machine.intents.context.context import Context
from action_machine.intents.logging.scoped_logger import ScopedLogger
from action_machine.intents.plugins.events import (
    CompensateFailedEvent,
    SagaRollbackCompletedEvent,
)
from action_machine.intents.plugins.on_decorator import on
from action_machine.intents.plugins.plugin import Plugin
from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator
from action_machine.model.base_params import BaseParams

from .conftest import (
    RecordingPlugin,
    SelectivePlugin,
    emit_global_finish,
    emit_global_start,
)

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные плагины для событий компенсации
# ═════════════════════════════════════════════════════════════════════════════


class CompensateFailedRecorderPlugin(Plugin):
    """
    Плагин, подписанный на CompensateFailedEvent.
    Записывает каждое событие сбоя компенсатора в state["failed_events"].
    Используется для проверки, что подписка на CompensateFailedEvent
    работает корректно через PluginRunContext.emit_event().
    """

    async def get_initial_state(self) -> dict:
        return {"failed_events": []}

    @on(CompensateFailedEvent)
    async def on_compensate_failed(
        self,
        state: dict,
        event: CompensateFailedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        state["failed_events"].append({
            "compensator_name": event.compensator_name,
            "failed_for_aspect": event.failed_for_aspect,
            "original_error_type": type(event.original_error).__name__,
            "compensator_error_type": type(event.compensator_error).__name__,
        })
        return state


class SagaCompletedRecorderPlugin(Plugin):
    """
    Плагин, подписанный на SagaRollbackCompletedEvent.
    Записывает итоги размотки стека в state["completed_events"].
    Используется для проверки, что подписка на SagaRollbackCompletedEvent
    работает корректно через PluginRunContext.emit_event().
    """

    async def get_initial_state(self) -> dict:
        return {"completed_events": []}

    @on(SagaRollbackCompletedEvent)
    async def on_saga_completed(
        self,
        state: dict,
        event: SagaRollbackCompletedEvent,
        log: ScopedLogger | None,
    ) -> dict:
        state["completed_events"].append({
            "total_frames": event.total_frames,
            "succeeded": event.succeeded,
            "failed": event.failed,
            "skipped": event.skipped,
        })
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции для эмиссии Saga-событий
# ═════════════════════════════════════════════════════════════════════════════


def _make_base_event_kwargs() -> dict:
    """Формирует общие kwargs для создания Saga-событий."""
    from tests.scenarios.domain_model import PingAction
    return {
        "action_class": PingAction,
        "action_name": "tests.domain.ping_action.PingAction",
        "nest_level": 1,
        "context": Context(),
        "params": BaseParams(),
    }


async def emit_compensate_failed(plugin_ctx) -> None:
    """Эмитирует тестовый CompensateFailedEvent."""
    event = CompensateFailedEvent(
        **_make_base_event_kwargs(),
        aspect_name="charge_aspect",
        state_snapshot=None,
        original_error=ValueError("Ошибка аспекта"),
        compensator_error=RuntimeError("Ошибка компенсатора"),
        compensator_name="rollback_charge_compensate",
        failed_for_aspect="charge_aspect",
    )
    await plugin_ctx.emit_event(event)


async def emit_saga_rollback_completed(plugin_ctx) -> None:
    """Эмитирует тестовый SagaRollbackCompletedEvent."""
    event = SagaRollbackCompletedEvent(
        **_make_base_event_kwargs(),
        error=ValueError("Ошибка аспекта"),
        total_frames=3,
        succeeded=2,
        failed=1,
        skipped=0,
        duration_ms=15.5,
        failed_aspects=("charge_aspect",),
    )
    await plugin_ctx.emit_event(event)


# ═════════════════════════════════════════════════════════════════════════════
# Тесты доставки событий
# ═════════════════════════════════════════════════════════════════════════════


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


# ═════════════════════════════════════════════════════════════════════════════
# Подписка на события компенсации (Saga)
# ═════════════════════════════════════════════════════════════════════════════


class TestEmitCompensationEvents:
    """
    Тесты подписки на типизированные события компенсации через emit_event().

    Добавлено как часть реализации механизма компенсации (Saga).
    Проверяет, что плагины могут подписаться на CompensateFailedEvent
    и SagaRollbackCompletedEvent и получать корректные данные из
    объектов событий [1].
    """

    @pytest.mark.anyio
    async def test_compensate_failed_event_delivered(self):
        """
        CompensateFailedRecorderPlugin подписан на CompensateFailedEvent.
        При эмиссии CompensateFailedEvent обработчик вызывается и записывает
        данные о сбое компенсатора в state["failed_events"].
        """
        # Arrange — плагин, записывающий сбои компенсаторов
        plugin = CompensateFailedRecorderPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — эмитируем CompensateFailedEvent
        await emit_compensate_failed(plugin_ctx)

        # Assert — событие записано с корректными полями
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["failed_events"]) == 1
        failed = state["failed_events"][0]
        assert failed["compensator_name"] == "rollback_charge_compensate"
        assert failed["failed_for_aspect"] == "charge_aspect"
        assert failed["original_error_type"] == "ValueError"
        assert failed["compensator_error_type"] == "RuntimeError"

    @pytest.mark.anyio
    async def test_saga_rollback_completed_event_delivered(self):
        """
        SagaCompletedRecorderPlugin подписан на SagaRollbackCompletedEvent.
        При эмиссии SagaRollbackCompletedEvent обработчик вызывается
        и записывает итоги размотки в state["completed_events"].
        """
        # Arrange — плагин, записывающий итоги размотки
        plugin = SagaCompletedRecorderPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — эмитируем SagaRollbackCompletedEvent
        await emit_saga_rollback_completed(plugin_ctx)

        # Assert — событие записано с корректными итогами
        state = plugin_ctx.get_plugin_state(plugin)
        assert len(state["completed_events"]) == 1
        completed = state["completed_events"][0]
        assert completed["total_frames"] == 3
        assert completed["succeeded"] == 2
        assert completed["failed"] == 1
        assert completed["skipped"] == 0
