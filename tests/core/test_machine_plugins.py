# tests/core/test_machine_plugins.py
"""
Тесты событий плагинов в ActionProductMachine.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
ActionProductMachine эмитирует типизированные события плагинам на каждом
этапе конвейера через PluginRunContext.emit_event(event, **kwargs) [1].
Машина создаёт конкретные объекты событий из иерархии BasePluginEvent
и передаёт их как первый позиционный аргумент в emit_event().

Жизненный цикл событий для действия с N regular-аспектами:

    GlobalStartEvent              → 1 событие (перед конвейером)
    BeforeRegularAspectEvent      → N событий
    AfterRegularAspectEvent       → N событий
    BeforeSummaryAspectEvent      → 1 событие
    AfterSummaryAspectEvent       → 1 событие
    GlobalFinishEvent             → 1 событие (после summary)
    ─────────────────────────────────
    Итого: 4 + 2*N событий

Для PingAction (0 regular, 1 summary): 4 события.
Для SimpleAction (1 regular, 1 summary): 6 событий.
Для FullAction (2 regular, 1 summary): 8 событий.

Дополнительные kwargs передаются в emit_event():
- log_coordinator — координатор логирования для создания ScopedLogger.
- machine_name — имя класса машины (для scope плагина).
- mode — режим выполнения (для scope плагина).
- GateCoordinator больше не передаётся в kwargs (domain-фильтр плагинов пропускается).

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════
Количество событий:
    - PingAction (0 regular) → 4 события.
    - SimpleAction (1 regular) → 6 событий.
    - FullAction (2 regular) → 8 событий.
Типы событий и порядок:
    - GlobalStartEvent первым, GlobalFinishEvent последним.
    - BeforeRegularAspectEvent/AfterRegularAspectEvent для каждого regular.
    - BeforeSummaryAspectEvent/AfterSummaryAspectEvent для summary.
Данные в emit_event:
    - Первый позиционный аргумент — объект события из иерархии BasePluginEvent.
    - log_coordinator, machine_name, mode в kwargs.
    - Поля события: action_class, action_name, nest_level, params, context.
    - GlobalFinishEvent содержит result и duration_ms.
Изоляция между запросами:
    - Каждый run() создаёт свой PluginRunContext.
    - Состояния плагинов одного run() не влияют на другой.
"""
from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.events import (
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BasePluginEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from tests.domain_model import (
    FullAction,
    NotificationService,
    PaymentService,
    PingAction,
    SimpleAction,
    TestDbManager,
)

# ═════════════════════════════════════════════════════════════════════════════
# Хелпер для извлечения типов событий из mock-вызовов
# ═════════════════════════════════════════════════════════════════════════════

def _extract_event_types(mock_plugin_ctx: AsyncMock) -> list[str]:
    """
    Извлекает имена классов событий из записанных вызовов emit_event().

    Машина передаёт объект события как первый позиционный аргумент:
        await plugin_ctx.emit_event(GlobalStartEvent(...), **kwargs)

    Возвращает список строк: ["GlobalStartEvent", "BeforeRegularAspectEvent", ...].
    """
    event_types = []
    for call in mock_plugin_ctx.emit_event.call_args_list:
        event = call.args[0] if call.args else None
        if event is not None:
            event_types.append(type(event).__name__)
    return event_types


def _extract_event(mock_plugin_ctx: AsyncMock, index: int) -> BasePluginEvent:
    """Извлекает объект события из записанного вызова emit_event() по индексу."""
    return mock_plugin_ctx.emit_event.call_args_list[index].args[0]


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def log_coordinator() -> LogCoordinator:
    """Тихий LogCoordinator — без вывода в stdout."""
    return LogCoordinator(loggers=[])


@pytest.fixture()
def mock_plugin_ctx() -> AsyncMock:
    """
    Мок PluginRunContext для отслеживания вызовов emit_event().
    Все вызовы emit_event записываются в call_args_list.
    """
    return AsyncMock(spec=PluginRunContext)


@pytest.fixture()
def machine_with_mock_plugins(log_coordinator, mock_plugin_ctx) -> ActionProductMachine:
    """
    ActionProductMachine с замоканным PluginCoordinator.

    PluginCoordinator.create_run_context() возвращает mock_plugin_ctx,
    все emit_event вызовы записываются для проверки в тестах.
    """
    mock_coordinator = AsyncMock(spec=PluginCoordinator)
    mock_coordinator.create_run_context = AsyncMock(return_value=mock_plugin_ctx)

    machine = ActionProductMachine(
        mode="test",
        log_coordinator=log_coordinator,
    )
    machine._plugin_coordinator = mock_coordinator
    return machine


@pytest.fixture()
def context() -> Context:
    """Контекст с ролями для прохождения любых проверок ролей."""
    return Context(user=UserInfo(user_id="tester", roles=["manager", "admin"]))


# ═════════════════════════════════════════════════════════════════════════════
# Количество событий
# ═════════════════════════════════════════════════════════════════════════════

class TestEventCount:
    """
    Количество emit_event вызовов зависит от числа regular-аспектов.

    Формула: 4 + 2*N, где N — число regular-аспектов.
    4 = GlobalStartEvent + BeforeSummaryAspectEvent +
        AfterSummaryAspectEvent + GlobalFinishEvent.
    2*N = BeforeRegularAspectEvent + AfterRegularAspectEvent для каждого regular.
    """

    @pytest.mark.asyncio
    async def test_ping_action_emits_four_events(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        PingAction (0 regular, 1 summary) → 4 события:
        GlobalStartEvent, BeforeSummaryAspectEvent,
        AfterSummaryAspectEvent, GlobalFinishEvent.
        """
        # Arrange — PingAction без regular-аспектов
        action = PingAction()
        params = PingAction.Params()

        # Act — полный конвейер
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — ровно 4 события
        assert mock_plugin_ctx.emit_event.await_count == 4

    @pytest.mark.asyncio
    async def test_simple_action_emits_six_events(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        SimpleAction (1 regular, 1 summary) → 6 событий:
        GlobalStartEvent, BeforeRegularAspectEvent, AfterRegularAspectEvent,
        BeforeSummaryAspectEvent, AfterSummaryAspectEvent, GlobalFinishEvent.
        Формула: 4 + 2*1 = 6.
        """
        # Arrange — SimpleAction с одним regular-аспектом
        action = SimpleAction()
        params = SimpleAction.Params(name="Alice")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — 6 событий
        assert mock_plugin_ctx.emit_event.await_count == 6

    @pytest.mark.asyncio
    async def test_full_action_emits_eight_events(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        FullAction (2 regular, 1 summary) → 8 событий:
        GlobalStartEvent,
        BeforeRegularAspectEvent, AfterRegularAspectEvent (×2),
        BeforeSummaryAspectEvent, AfterSummaryAspectEvent,
        GlobalFinishEvent.
        Формула: 4 + 2*2 = 8.
        """
        # Arrange — FullAction с моками зависимостей и connections
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-EVT"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        # Act — run через _run_internal с моками в resources
        await machine_with_mock_plugins._run_internal(
            context=context,
            action=action,
            params=params,
            resources={PaymentService: mock_payment, NotificationService: mock_notification},
            connections={"db": mock_db},
            nested_level=0,
            rollup=False,
        )

        # Assert — 8 событий
        assert mock_plugin_ctx.emit_event.await_count == 8


# ═════════════════════════════════════════════════════════════════════════════
# Типы событий и порядок
# ═════════════════════════════════════════════════════════════════════════════

class TestEventTypes:
    """Типы событий и их порядок."""

    @pytest.mark.asyncio
    async def test_ping_event_types(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        PingAction: GlobalStartEvent первый, GlobalFinishEvent последний.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — извлекаем типы событий из каждого вызова emit_event
        event_types = _extract_event_types(mock_plugin_ctx)

        # Assert — GlobalStartEvent первый, GlobalFinishEvent последний
        assert event_types[0] == "GlobalStartEvent"
        assert event_types[-1] == "GlobalFinishEvent"

    @pytest.mark.asyncio
    async def test_simple_action_event_order(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        SimpleAction: GlobalStartEvent → BeforeRegularAspectEvent →
        AfterRegularAspectEvent → BeforeSummaryAspectEvent →
        AfterSummaryAspectEvent → GlobalFinishEvent.
        """
        # Arrange
        action = SimpleAction()
        params = SimpleAction.Params(name="Bob")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — порядок типов событий
        event_types = _extract_event_types(mock_plugin_ctx)
        assert event_types == [
            "GlobalStartEvent",
            "BeforeRegularAspectEvent",
            "AfterRegularAspectEvent",
            "BeforeSummaryAspectEvent",
            "AfterSummaryAspectEvent",
            "GlobalFinishEvent",
        ]

    @pytest.mark.asyncio
    async def test_full_action_event_order(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        FullAction: GlobalStartEvent → before/after process_payment_aspect →
        before/after calc_total_aspect → before/after summary →
        GlobalFinishEvent.
        """
        # Arrange
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-ORD"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=200.0)

        # Act
        await machine_with_mock_plugins._run_internal(
            context=context,
            action=action,
            params=params,
            resources={PaymentService: mock_payment, NotificationService: mock_notification},
            connections={"db": mock_db},
            nested_level=0,
            rollup=False,
        )

        # Assert — порядок восьми типов событий
        event_types = _extract_event_types(mock_plugin_ctx)
        assert event_types == [
            "GlobalStartEvent",
            "BeforeRegularAspectEvent",
            "AfterRegularAspectEvent",
            "BeforeRegularAspectEvent",
            "AfterRegularAspectEvent",
            "BeforeSummaryAspectEvent",
            "AfterSummaryAspectEvent",
            "GlobalFinishEvent",
        ]

    @pytest.mark.asyncio
    async def test_events_are_correct_isinstance(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        Каждый объект события является экземпляром соответствующего класса
        из иерархии BasePluginEvent [1].
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — проверяем isinstance для каждого события
        calls = mock_plugin_ctx.emit_event.call_args_list
        assert isinstance(calls[0].args[0], GlobalStartEvent)
        assert isinstance(calls[1].args[0], BeforeSummaryAspectEvent)
        assert isinstance(calls[2].args[0], AfterSummaryAspectEvent)
        assert isinstance(calls[3].args[0], GlobalFinishEvent)


# ═════════════════════════════════════════════════════════════════════════════
# Данные в emit_event
# ═════════════════════════════════════════════════════════════════════════════

class TestEventData:
    """Данные, передаваемые в каждый emit_event."""

    @pytest.mark.asyncio
    async def test_log_coordinator_passed(
        self, machine_with_mock_plugins, mock_plugin_ctx, context, log_coordinator,
    ) -> None:
        """
        log_coordinator передаётся в каждый emit_event через kwargs.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — log_coordinator присутствует в каждом вызове emit_event
        for call in mock_plugin_ctx.emit_event.call_args_list:
            assert "log_coordinator" in call.kwargs
            assert call.kwargs["log_coordinator"] is log_coordinator

    @pytest.mark.asyncio
    async def test_machine_name_and_mode_passed(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        machine_name и mode передаются в каждый emit_event через kwargs.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — machine_name и mode в каждом вызове
        for call in mock_plugin_ctx.emit_event.call_args_list:
            assert call.kwargs["machine_name"] == "ActionProductMachine"
            assert call.kwargs["mode"] == "test"

    @pytest.mark.asyncio
    async def test_coordinator_not_passed(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        GateCoordinator не передаётся в emit_event: scratch-исполнение без графа.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — ключ coordinator отсутствует (плагины без domain-фильтра)
        for call in mock_plugin_ctx.emit_event.call_args_list:
            assert "coordinator" not in call.kwargs

    @pytest.mark.asyncio
    async def test_event_contains_action_class_and_name(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        Каждый объект события содержит action_class и action_name [1].
        action_class — type для isinstance-фильтрации.
        action_name — строка для regex-фильтрации и логирования.
        """
        # Arrange
        action = SimpleAction()
        params = SimpleAction.Params(name="Charlie")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — первое событие (GlobalStartEvent) содержит поля действия
        event = _extract_event(mock_plugin_ctx, 0)
        assert event.action_class is SimpleAction
        assert "SimpleAction" in event.action_name
        assert event.params is params

    @pytest.mark.asyncio
    async def test_nest_level_in_event(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        nest_level содержится в объекте события.
        Для корневого вызова run() nested_level=0, машина увеличивает
        на 1 → current_nest=1 → записывается в event.nest_level.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — nest_level=1 (0+1) в первом событии
        event = _extract_event(mock_plugin_ctx, 0)
        assert event.nest_level == 1

    @pytest.mark.asyncio
    async def test_global_finish_contains_result_and_duration(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        GlobalFinishEvent содержит result и duration_ms [1].
        result — объект, возвращённый summary-аспектом.
        duration_ms — общее время выполнения в миллисекундах.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — последнее событие — GlobalFinishEvent
        event = _extract_event(mock_plugin_ctx, -1)
        assert isinstance(event, GlobalFinishEvent)

        # Assert — result не None (это PingAction.Result)
        assert event.result is not None

        # Assert — duration_ms — неотрицательное число (миллисекунды)
        assert event.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_regular_aspect_event_contains_aspect_name(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        BeforeRegularAspectEvent и AfterRegularAspectEvent содержат
        aspect_name — имя метода-аспекта [1].
        """
        # Arrange
        action = SimpleAction()
        params = SimpleAction.Params(name="Test")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — BeforeRegularAspectEvent содержит aspect_name
        event_types = _extract_event_types(mock_plugin_ctx)
        before_idx = event_types.index("BeforeRegularAspectEvent")
        before_event = _extract_event(mock_plugin_ctx, before_idx)
        assert isinstance(before_event, BeforeRegularAspectEvent)
        assert isinstance(before_event.aspect_name, str)
        assert len(before_event.aspect_name) > 0

    @pytest.mark.asyncio
    async def test_after_regular_aspect_contains_result_and_duration(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        AfterRegularAspectEvent содержит aspect_result и duration_ms [1].
        """
        # Arrange
        action = SimpleAction()
        params = SimpleAction.Params(name="Test")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — AfterRegularAspectEvent содержит aspect_result
        event_types = _extract_event_types(mock_plugin_ctx)
        after_idx = event_types.index("AfterRegularAspectEvent")
        after_event = _extract_event(mock_plugin_ctx, after_idx)
        assert isinstance(after_event, AfterRegularAspectEvent)
        assert isinstance(after_event.aspect_result, dict)
        assert after_event.duration_ms >= 0


# ═════════════════════════════════════════════════════════════════════════════
# Изоляция между запросами
# ═════════════════════════════════════════════════════════════════════════════

class TestPluginIsolation:
    """Каждый run() создаёт свой PluginRunContext."""

    @pytest.mark.asyncio
    async def test_separate_contexts_per_run(self, log_coordinator, context) -> None:
        """
        Два вызова run() создают два разных PluginRunContext.
        create_run_context() вызывается в начале каждого _run_internal().
        Каждый контекст изолирован [1].
        """
        # Arrange — машина с замоканным PluginCoordinator, который
        # возвращает новый mock PluginRunContext на каждый вызов
        ctx1 = AsyncMock(spec=PluginRunContext)
        ctx2 = AsyncMock(spec=PluginRunContext)
        mock_coordinator = AsyncMock(spec=PluginCoordinator)
        mock_coordinator.create_run_context = AsyncMock(side_effect=[ctx1, ctx2])

        machine = ActionProductMachine(
            mode="test",
            log_coordinator=log_coordinator,
        )
        machine._plugin_coordinator = mock_coordinator

        action = PingAction()
        params = PingAction.Params()

        # Act — два отдельных run()
        await machine.run(context, action, params)
        await machine.run(context, PingAction(), PingAction.Params())

        # Assert — create_run_context вызван дважды
        assert mock_coordinator.create_run_context.await_count == 2

        # Assert — каждый контекст получил свои события (4 на PingAction)
        assert ctx1.emit_event.await_count == 4
        assert ctx2.emit_event.await_count == 4
