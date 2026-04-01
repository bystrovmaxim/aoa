# tests/core/test_machine_plugins.py
"""
Тесты событий плагинов в ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ActionProductMachine эмитирует события плагинам на каждом этапе конвейера
через PluginRunContext.emit_event(). Плагины подписываются на события
через @on и получают PluginEvent с данными о действии, параметрах,
состоянии, результате и длительности.

Жизненный цикл событий для действия с N regular-аспектами:

    global_start           → 1 событие (перед конвейером)
    before:{aspect_1}      → 1 событие
    after:{aspect_1}       → 1 событие
    ...
    before:{aspect_N}      → 1 событие
    after:{aspect_N}       → 1 событие
    global_finish          → 1 событие (после summary)
    ─────────────────────────────────
    Итого: 2 + 2*N событий

Для PingAction (0 regular, 1 summary): 2 события (global_start + global_finish).
Для SimpleAction (1 regular, 1 summary): 4 события.
Для FullAction (2 regular, 1 summary): 6 событий.

Машина передаёт в emit_event() дополнительные kwargs:
- log_coordinator — координатор логирования для создания ScopedLogger.
- machine_name — имя класса машины (для scope плагина).
- mode — режим выполнения (для scope плагина).

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Количество событий:
    - PingAction (0 regular) → 2 события.
    - SimpleAction (1 regular) → 4 события.
    - FullAction (2 regular) → 6 событий.

Имена событий:
    - global_start первым, global_finish последним.
    - before/after для каждого regular-аспекта в порядке объявления.

Данные в emit_event:
    - log_coordinator передаётся в каждый emit_event.
    - machine_name и mode передаются в каждый emit_event.
    - action и params передаются в каждый emit_event.
    - nest_level передаётся в каждый emit_event.

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
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from tests.domain import (
    FullAction,
    NotificationService,
    PaymentService,
    PingAction,
    SimpleAction,
    TestDbManager,
)

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
    """Количество emit_event вызовов зависит от числа regular-аспектов."""

    @pytest.mark.asyncio
    async def test_ping_action_emits_two_events(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        PingAction (0 regular, 1 summary) → 2 события: global_start + global_finish.

        PingAction содержит только summary-аспект. Нет regular-аспектов →
        нет before/after событий. Только обрамляющие global_start и global_finish.
        """
        # Arrange — PingAction без regular-аспектов
        action = PingAction()
        params = PingAction.Params()

        # Act — полный конвейер
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — ровно 2 события
        assert mock_plugin_ctx.emit_event.await_count == 2

    @pytest.mark.asyncio
    async def test_simple_action_emits_four_events(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        SimpleAction (1 regular, 1 summary) → 4 события:
        global_start, before:validate_name, after:validate_name, global_finish.

        Формула: 2 + 2*N, где N=1 → 4.
        """
        # Arrange — SimpleAction с одним regular-аспектом
        action = SimpleAction()
        params = SimpleAction.Params(name="Alice")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — 4 события
        assert mock_plugin_ctx.emit_event.await_count == 4

    @pytest.mark.asyncio
    async def test_full_action_emits_six_events(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        FullAction (2 regular, 1 summary) → 6 событий:
        global_start, before:process_payment, after:process_payment,
        before:calc_total, after:calc_total, global_finish.

        Формула: 2 + 2*N, где N=2 → 6.
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

        # Assert — 6 событий
        assert mock_plugin_ctx.emit_event.await_count == 6


# ═════════════════════════════════════════════════════════════════════════════
# Имена событий и порядок
# ═════════════════════════════════════════════════════════════════════════════


class TestEventNames:
    """Имена событий и их порядок."""

    @pytest.mark.asyncio
    async def test_ping_event_names(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        PingAction: первое событие — global_start, последнее — global_finish.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — извлекаем event_name из каждого вызова emit_event
        calls = mock_plugin_ctx.emit_event.call_args_list
        event_names = [call.kwargs["event_name"] for call in calls]

        # Assert — global_start первый, global_finish последний
        assert event_names[0] == "global_start"
        assert event_names[-1] == "global_finish"

    @pytest.mark.asyncio
    async def test_simple_action_event_order(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        SimpleAction: global_start → before:validate_name →
        after:validate_name → global_finish.
        """
        # Arrange
        action = SimpleAction()
        params = SimpleAction.Params(name="Bob")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — порядок событий
        calls = mock_plugin_ctx.emit_event.call_args_list
        event_names = [call.kwargs["event_name"] for call in calls]

        assert event_names == [
            "global_start",
            "before:validate_name",
            "after:validate_name",
            "global_finish",
        ]

    @pytest.mark.asyncio
    async def test_full_action_event_order(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        FullAction: global_start → before/after process_payment →
        before/after calc_total → global_finish.

        Порядок before/after соответствует порядку объявления
        regular-аспектов в классе.
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

        # Assert — порядок шести событий
        calls = mock_plugin_ctx.emit_event.call_args_list
        event_names = [call.kwargs["event_name"] for call in calls]

        assert event_names == [
            "global_start",
            "before:process_payment",
            "after:process_payment",
            "before:calc_total",
            "after:calc_total",
            "global_finish",
        ]


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
        log_coordinator передаётся в каждый emit_event.

        PluginRunContext использует log_coordinator для создания
        ScopedLogger обработчикам плагинов. Без него log=None
        в обработчике, и любой вызов log.info() упадёт.
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
        machine_name и mode передаются в каждый emit_event.

        Используются PluginRunContext для создания ScopedLogger с scope:
        LogScope(machine=machine_name, mode=mode, plugin=..., action=...,
        event=..., nest_level=...).
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — machine_name и mode в первом вызове
        first_call = mock_plugin_ctx.emit_event.call_args_list[0]
        assert first_call.kwargs["machine_name"] == "ActionProductMachine"
        assert first_call.kwargs["mode"] == "test"

    @pytest.mark.asyncio
    async def test_action_and_params_passed(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        action и params передаются в каждый emit_event.

        Плагины используют action для получения имени класса
        (action.get_full_class_name()) и params для чтения
        входных параметров.
        """
        # Arrange
        action = SimpleAction()
        params = SimpleAction.Params(name="Charlie")

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — action и params в первом вызове (global_start)
        first_call = mock_plugin_ctx.emit_event.call_args_list[0]
        assert first_call.kwargs["action"] is action
        assert first_call.kwargs["params"] is params

    @pytest.mark.asyncio
    async def test_nest_level_passed(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        nest_level передаётся в каждый emit_event.

        Для корневого вызова run() nested_level=0, машина увеличивает
        на 1 → current_nest=1 → передаётся в emit_event.
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — nest_level=1 (0+1) в первом вызове
        first_call = mock_plugin_ctx.emit_event.call_args_list[0]
        assert first_call.kwargs["nest_level"] == 1

    @pytest.mark.asyncio
    async def test_global_finish_contains_result_and_duration(
        self, machine_with_mock_plugins, mock_plugin_ctx, context,
    ) -> None:
        """
        global_finish содержит result (Result действия) и duration (секунды).

        result — объект, возвращённый summary-аспектом.
        duration — общее время выполнения действия (float, секунды).
        """
        # Arrange
        action = PingAction()
        params = PingAction.Params()

        # Act
        await machine_with_mock_plugins.run(context, action, params)

        # Assert — последний вызов = global_finish
        last_call = mock_plugin_ctx.emit_event.call_args_list[-1]
        assert last_call.kwargs["event_name"] == "global_finish"

        # Assert — result не None (это PingAction.Result)
        assert last_call.kwargs["result"] is not None

        # Assert — duration — положительное число (время выполнения)
        assert last_call.kwargs["duration"] is not None
        assert last_call.kwargs["duration"] >= 0


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
        Каждый контекст изолирован: состояния плагинов одного run()
        не влияют на другой, даже при параллельном выполнении.
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

        # Assert — каждый контекст получил свои события
        assert ctx1.emit_event.await_count == 2  # global_start + global_finish
        assert ctx2.emit_event.await_count == 2  # global_start + global_finish
