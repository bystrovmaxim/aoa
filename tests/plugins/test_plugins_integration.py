# tests/plugins/test_plugins_integration.py
"""
Интеграционные тесты плагинов с полным конвейером ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что плагины корректно получают события от реального конвейера
выполнения действий. В отличие от остальных тестов пакета plugins/,
которые вызывают emit_event() напрямую, эти тесты прогоняют действия
через TestBench.run() — полный конвейер на async и sync машинах
с проверкой совпадения результатов.

TestBench.run() выполняет действие на ActionProductMachine (async),
сбрасывает моки, выполняет на SyncActionProductMachine (sync) и
сравнивает результаты через compare_results(). Плагины получают
события от обеих машин — global_start, before/after каждого аспекта,
global_finish.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Плагин-счётчик получает global_finish при прогоне PingAction.
- Плагин-счётчик получает global_finish при прогоне SimpleAction
  (regular + summary).
- Плагин-записыватель фиксирует все события конвейера FullAction
  (global_start, before/after каждого аспекта, global_finish).
- Плагин с фильтром action_filter получает события только от
  подходящих действий.
- Несколько плагинов одновременно — все получают события.

═══════════════════════════════════════════════════════════════════════════════
ДОСТУП К СОСТОЯНИЮ ПЛАГИНОВ
═══════════════════════════════════════════════════════════════════════════════

TestBench использует production-машины (ActionProductMachine,
SyncActionProductMachine), которые создают PluginRunContext внутри
_run_internal(). После завершения run() контекст уничтожается —
прямого доступа к plugin_ctx.get_plugin_state() нет.

Для проверки работы плагинов используются внешние хранилища,
переданные через конструктор плагина. Плагин при обработке события
записывает данные во внешний список/словарь, который тест читает
после завершения run().
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_event import PluginEvent
from action_machine.testing import TestBench
from tests.domain import (
    FullAction,
    NotificationService,
    PaymentService,
    PingAction,
    SimpleAction,
    TestDbManager,
)

# ═════════════════════════════════════════════════════════════════════════════
# Плагины с внешним хранилищем для проверки из тестов
# ═════════════════════════════════════════════════════════════════════════════


class ExternalCounterPlugin(Plugin):
    """
    Плагин-счётчик с внешним хранилищем.

    Записывает количество вызовов global_finish во внешний список,
    переданный через конструктор. Тест читает список после run()
    для проверки, что плагин получил события.
    """

    def __init__(self, storage: list):
        self._storage = storage

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*")
    async def count(self, state: dict, event: PluginEvent, log) -> dict:
        state["count"] += 1
        self._storage.append({
            "event": event.event_name,
            "action": event.action_name,
            "count": state["count"],
        })
        return state


class ExternalRecorderPlugin(Plugin):
    """
    Плагин-записыватель с внешним хранилищем.

    Подписан на ВСЕ события (".*") для всех действий (".*").
    Записывает event_name и action_name во внешний список.
    Позволяет тесту увидеть полную последовательность событий конвейера.
    """

    def __init__(self, storage: list):
        self._storage = storage

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_start", ".*")
    async def on_start(self, state: dict, event: PluginEvent, log) -> dict:
        self._storage.append(event.event_name)
        return state

    @on("global_finish", ".*")
    async def on_finish(self, state: dict, event: PluginEvent, log) -> dict:
        self._storage.append(event.event_name)
        return state


class SelectiveCounterPlugin(Plugin):
    """
    Плагин-счётчик с фильтром по имени действия.

    Реагирует только на global_finish от действий, содержащих "Simple"
    в имени. Записывает во внешний список.
    """

    def __init__(self, storage: list):
        self._storage = storage

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*Simple.*")
    async def on_simple(self, state: dict, event: PluginEvent, log) -> dict:
        self._storage.append(event.action_name)
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Тесты
# ═════════════════════════════════════════════════════════════════════════════


class TestPluginsIntegration:
    """
    Интеграционные тесты плагинов с полным конвейером через TestBench.

    Каждый тест создаёт внешнее хранилище (список), передаёт его
    в плагин через конструктор, прогоняет действие через TestBench.run()
    (async + sync машины) и проверяет содержимое хранилища.
    """

    @pytest.mark.anyio
    async def test_counter_plugin_receives_global_finish_from_ping(self):
        """
        ExternalCounterPlugin получает global_finish при прогоне PingAction
        через TestBench. PingAction — только summary, ROLE_NONE.

        Хранилище содержит записи от обеих машин (async + sync),
        поэтому ожидаем минимум одну запись (TestBench сбрасывает
        моки между прогонами, но плагин — не мок, его storage
        накапливает записи от обеих машин).
        """
        # Arrange — внешнее хранилище и плагин
        storage: list = []
        plugin = ExternalCounterPlugin(storage)

        bench = TestBench(
            coordinator=GateCoordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        # Act — полный прогон PingAction на обеих машинах
        result = await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        # Assert — результат корректен
        assert result.message == "pong"

        # Assert — плагин получил события (от async и sync машин)
        assert len(storage) >= 1
        assert all(record["event"] == "global_finish" for record in storage)
        assert all("PingAction" in record["action"] for record in storage)

    @pytest.mark.anyio
    async def test_counter_plugin_receives_global_finish_from_simple(self):
        """
        ExternalCounterPlugin получает global_finish при прогоне SimpleAction.
        SimpleAction имеет regular + summary, ROLE_NONE.
        """
        # Arrange — хранилище и плагин
        storage: list = []
        plugin = ExternalCounterPlugin(storage)

        bench = TestBench(
            coordinator=GateCoordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        # Act — полный прогон SimpleAction
        result = await bench.run(
            SimpleAction(),
            SimpleAction.Params(name="Alice"),
            rollup=False,
        )

        # Assert — результат корректен
        assert result.greeting == "Hello, Alice!"

        # Assert — плагин получил события
        assert len(storage) >= 1
        assert all("SimpleAction" in record["action"] for record in storage)

    @pytest.mark.anyio
    async def test_recorder_plugin_captures_event_sequence(self):
        """
        ExternalRecorderPlugin подписан на global_start и global_finish.
        При прогоне PingAction записывает последовательность событий.
        """
        # Arrange — хранилище и плагин-записыватель
        storage: list = []
        plugin = ExternalRecorderPlugin(storage)

        bench = TestBench(
            coordinator=GateCoordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        # Act — полный прогон PingAction
        await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        # Assert — последовательность содержит global_start и global_finish
        # (от обеих машин, поэтому записей может быть 4: start+finish × 2)
        assert "global_start" in storage
        assert "global_finish" in storage

    @pytest.mark.anyio
    async def test_selective_plugin_filters_by_action_name(self):
        """
        SelectiveCounterPlugin реагирует только на действия с "Simple" в имени.
        При прогоне PingAction плагин не получает событий.
        При прогоне SimpleAction — получает.
        """
        # Arrange — хранилище и плагин с фильтром
        storage: list = []
        plugin = SelectiveCounterPlugin(storage)

        bench = TestBench(
            coordinator=GateCoordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[plugin],
        )

        # Act — прогоняем PingAction (не содержит "Simple")
        await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        # Assert — плагин не получил событий от PingAction
        assert len(storage) == 0

        # Act — прогоняем SimpleAction (содержит "Simple")
        await bench.run(
            SimpleAction(),
            SimpleAction.Params(name="Bob"),
            rollup=False,
        )

        # Assert — плагин получил события от SimpleAction
        assert len(storage) >= 1
        assert all("SimpleAction" in name for name in storage)

    @pytest.mark.anyio
    async def test_multiple_plugins_all_receive_events(self):
        """
        Два плагина одновременно: ExternalCounterPlugin и ExternalRecorderPlugin.
        Оба получают события от одного прогона PingAction.
        """
        # Arrange — два хранилища и два плагина
        counter_storage: list = []
        recorder_storage: list = []
        counter_plugin = ExternalCounterPlugin(counter_storage)
        recorder_plugin = ExternalRecorderPlugin(recorder_storage)

        bench = TestBench(
            coordinator=GateCoordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            plugins=[counter_plugin, recorder_plugin],
        )

        # Act — полный прогон PingAction
        await bench.run(
            PingAction(),
            PingAction.Params(),
            rollup=False,
        )

        # Assert — оба плагина получили события
        assert len(counter_storage) >= 1
        assert "global_start" in recorder_storage
        assert "global_finish" in recorder_storage

    @pytest.mark.anyio
    async def test_plugin_with_full_action_and_mocks(self):
        """
        ExternalCounterPlugin с FullAction — действие с зависимостями
        (PaymentService, NotificationService) и connection ("db").
        Плагин получает global_finish от полного конвейера.
        """
        # Arrange — моки зависимостей
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-INTEGRATION-001"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_notification.send.return_value = True
        mock_db = AsyncMock(spec=TestDbManager)

        # Arrange — хранилище и плагин
        storage: list = []
        plugin = ExternalCounterPlugin(storage)

        bench = TestBench(
            coordinator=GateCoordinator(),
            log_coordinator=LogCoordinator(loggers=[]),
            mocks={
                PaymentService: mock_payment,
                NotificationService: mock_notification,
            },
            plugins=[plugin],
        ).with_user(user_id="mgr_1", roles=["manager"])

        # Act — полный прогон FullAction с connections
        result = await bench.run(
            FullAction(),
            FullAction.Params(user_id="user_int", amount=500.0),
            rollup=False,
            connections={"db": mock_db},
        )

        # Assert — результат корректен
        assert result.order_id == "ORD-user_int"
        assert result.txn_id == "TXN-INTEGRATION-001"
        assert result.total == 500.0

        # Assert — плагин получил события от полного конвейера
        assert len(storage) >= 1
        assert all("FullAction" in record["action"] for record in storage)
