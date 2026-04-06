# src/action_machine/testing/bench.py
"""
TestBench — единая immutable точка входа для тестирования действий ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

TestBench — центральный объект тестовой инфраструктуры. Создаёт внутри
себя коллекцию машин (async + sync), прогоняет действие на каждой
и сравнивает результаты. Если результаты расходятся — ResultMismatchError.

TestBench immutable: каждый fluent-вызов (.with_user, .with_mocks и т.д.)
возвращает НОВЫЙ экземпляр TestBench с изменённым полем. Оригинал
не мутируется. Это делает TestBench безопасным для параллельного
использования и предсказуемым в тестах.

═══════════════════════════════════════════════════════════════════════════════
КОЛЛЕКЦИЯ МАШИН
═══════════════════════════════════════════════════════════════════════════════

По умолчанию TestBench создаёт две машины:
- ActionProductMachine (async) — с моками через resources.
- SyncActionProductMachine (sync) — с моками через resources.

Обе машины получают одинаковый coordinator, plugins и log_coordinator.
Терминальные методы (run, run_aspect, run_summary) прогоняют действие
на КАЖДОЙ машине и сравнивают результаты через compare_results().

═══════════════════════════════════════════════════════════════════════════════
СБРОС МОКОВ МЕЖДУ ПРОГОНАМИ
═══════════════════════════════════════════════════════════════════════════════

Метод run() выполняет действие на двух машинах последовательно. Между
прогонами async и sync машин все Mock-объекты (unittest.mock.Mock,
MagicMock, AsyncMock) сбрасываются через reset_mock(). Это гарантирует,
что:

- Каждая машина работает с чистыми моками.
- Тесты могут использовать assert_called_once_with() без учёта
  второго прогона.
- call_count отражает вызовы только от последней (sync) машины.

После обоих прогонов моки НЕ сбрасываются повторно — тест видит
состояние моков после sync-прогона.

═══════════════════════════════════════════════════════════════════════════════
ПОДГОТОВКА МОКОВ
═══════════════════════════════════════════════════════════════════════════════

TestBench подготавливает моки через _prepare_mock() по следующим правилам
(порядок проверок важен):

1. MockAction         → как есть (мок-действие для подстановки).
2. BaseAction         → как есть (реальное действие).
3. unittest.mock.Mock → как есть (мок-объект для box.resolve()).
   Включает Mock, MagicMock, AsyncMock и все их подклассы.
   Это ключевое правило: AsyncMock(spec=PaymentService) передаётся
   в resources напрямую, чтобы box.resolve(PaymentService) вернул мок.
4. BaseResult         → оборачивается в MockAction(result=value).
5. callable           → оборачивается в MockAction(side_effect=value).
6. любой другой       → как есть (для box.resolve()).

Правило 3 стоит ПЕРЕД правилом 5, потому что AsyncMock является callable,
но не должен оборачиваться в MockAction — он предназначен для resolve().

═══════════════════════════════════════════════════════════════════════════════
ПРОКИДЫВАНИЕ ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Терминальные методы (run, run_aspect, run_summary) принимают обязательный
параметр rollup: bool без значения по умолчанию. Тестировщик явно
выбирает режим.

Rollup прокидывается в machine._run_internal(rollup=rollup), откуда
попадает в ToolsBox(rollup=rollup). ToolsBox использует rollup при:
- resolve() → factory.resolve(cls, rollup=rollup).
- run() → замыкание run_child передаёт rollup рекурсивно.

═══════════════════════════════════════════════════════════════════════════════
FLUENT API (IMMUTABLE)
═══════════════════════════════════════════════════════════════════════════════

Каждый fluent-метод возвращает НОВЫЙ экземпляр TestBench:

    bench = TestBench(mocks={PaymentService: mock})
    admin_bench = bench.with_user(user_id="admin", roles=["admin"])

    # bench и admin_bench — два разных объекта.
    # bench не изменился после вызова with_user.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from unittest.mock import AsyncMock
    from action_machine.testing import TestBench

    mock_payment = AsyncMock(spec=PaymentService)
    mock_payment.charge.return_value = "TXN-001"

    bench = TestBench(mocks={PaymentService: mock_payment})
    admin_bench = bench.with_user(user_id="admin", roles=["admin"])

    result = await admin_bench.run(
        CreateOrderAction(),
        OrderParams(user_id="u1", amount=100.0),
        rollup=False,
    )

    # assert_called_once_with работает корректно —
    # моки сброшены между async и sync прогонами,
    # тест видит состояние только от sync-прогона.
    mock_payment.charge.assert_called_once_with(100.0, "RUB")
"""

from __future__ import annotations

from typing import Any, TypeVar, cast
from unittest.mock import Mock

from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.sync_action_product_machine import SyncActionProductMachine
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.plugin import Plugin
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .comparison import compare_results
from .mock_action import MockAction
from .state_validator import validate_state_for_aspect, validate_state_for_summary
from .stubs import RequestInfoStub, RuntimeInfoStub, UserInfoStub

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции модульного уровня
# ═════════════════════════════════════════════════════════════════════════════


def _prepare_mock(value: Any) -> Any:
    """
    Преобразует mock-значение в объект, пригодный для использования в resources.

    Порядок проверок важен — Mock проверяется ДО callable, потому что
    AsyncMock/MagicMock являются callable, но должны передаваться
    в resources как есть (для box.resolve()), а не оборачиваться
    в MockAction.

    Правила преобразования (в порядке приоритета):
    1. MockAction   → как есть (мок-действие).
    2. BaseAction   → как есть (реальное действие).
    3. Mock         → как есть (unittest.mock: Mock, MagicMock, AsyncMock).
    4. BaseResult   → MockAction(result=value).
    5. callable     → MockAction(side_effect=value).
    6. любой другой → как есть (для box.resolve()).

    Аргументы:
        value: mock-значение из словаря mocks.

    Возвращает:
        Подготовленный объект для словаря resources.
    """
    if isinstance(value, MockAction):
        return value
    if isinstance(value, BaseAction):
        return value
    if isinstance(value, Mock):
        return value
    if isinstance(value, BaseResult):
        return MockAction(result=value)
    if callable(value):
        return MockAction(side_effect=value)
    return value


def _prepare_all_mocks(mocks: dict[type, Any]) -> dict[type, Any]:
    """
    Подготавливает все моки из словаря через _prepare_mock().

    Аргументы:
        mocks: исходный словарь {класс_зависимости: mock_значение}.

    Возвращает:
        Новый словарь с подготовленными значениями.
    """
    return {cls: _prepare_mock(val) for cls, val in mocks.items()}


def _reset_all_mocks(mocks: dict[type, Any]) -> None:
    """
    Сбрасывает состояние всех Mock-объектов в словаре моков.

    Вызывается между прогонами async и sync машин в TestBench.run(),
    чтобы каждая машина работала с чистыми моками. Без сброса
    assert_called_once_with() падает, потому что мок помнит вызовы
    от предыдущей машины.

    Сбрасывает только объекты, являющиеся экземплярами unittest.mock.Mock
    (включая MagicMock, AsyncMock). Остальные объекты в словаре
    (MockAction, реальные Action, любые другие) — не затрагиваются.

    Аргументы:
        mocks: исходный словарь моков {класс: mock_значение}.
    """
    for value in mocks.values():
        if isinstance(value, Mock):
            value.reset_mock()


# ═════════════════════════════════════════════════════════════════════════════
# Класс TestBench
# ═════════════════════════════════════════════════════════════════════════════


class TestBench:
    """
    Единая immutable точка входа для тестирования действий ActionMachine.

    Каждый fluent-вызов возвращает НОВЫЙ экземпляр — оригинал не мутируется.
    Терминальные методы прогоняют действие на коллекции машин (async + sync)
    и сравнивают результаты. Rollup прокидывается через _run_internal
    в ToolsBox и далее в resolve() и run().

    Между прогонами async и sync машин все Mock-объекты сбрасываются
    через _reset_all_mocks(), чтобы тесты могли корректно использовать
    assert_called_once_with() и проверять call_count.

    Атрибуты:
        _coordinator : GateCoordinator — координатор метаданных и фабрик.
        _mocks : dict[type, Any] — исходный словарь моков (до подготовки).
        _prepared_mocks : dict[type, Any] — подготовленные моки (после _prepare_mock).
        _plugins : list[Plugin] — список плагинов для машин.
        _log_coordinator : LogCoordinator | None — координатор логирования.
        _user : UserInfo — информация о пользователе для контекста.
        _runtime : RuntimeInfo — информация об окружении для контекста.
        _request : RequestInfo — информация о запросе для контекста.
    """

    __test__ = False  # pytest: это не тестовый класс

    def __init__(
        self,
        coordinator: GateCoordinator | None = None,
        mocks: dict[type, Any] | None = None,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
        user: Any | None = None,
        runtime: Any | None = None,
        request: Any | None = None,
    ) -> None:
        """
        Инициализирует TestBench.

        Аргументы:
            coordinator: координатор метаданных. По умолчанию новый GateCoordinator().
            mocks: словарь моков {класс: mock_значение}. По умолчанию пустой.
            plugins: список плагинов. По умолчанию пустой.
            log_coordinator: координатор логирования. По умолчанию None
                             (машины создают дефолтный с ConsoleLogger).
            user: информация о пользователе. По умолчанию UserInfoStub().
            runtime: информация об окружении. По умолчанию RuntimeInfoStub().
            request: информация о запросе. По умолчанию RequestInfoStub().
        """
        self._coordinator = coordinator or GateCoordinator()
        self._mocks = dict(mocks) if mocks else {}
        self._prepared_mocks = _prepare_all_mocks(self._mocks)
        self._plugins = list(plugins) if plugins else []
        self._log_coordinator = log_coordinator
        self._user = user if user is not None else UserInfoStub()
        self._runtime = runtime if runtime is not None else RuntimeInfoStub()
        self._request = request if request is not None else RequestInfoStub()

    # ─────────────────────────────────────────────────────────────────────
    # Свойства (только чтение)
    # ─────────────────────────────────────────────────────────────────────

    @property
    def coordinator(self) -> GateCoordinator:
        """Координатор метаданных и фабрик."""
        return self._coordinator

    @property
    def mocks(self) -> dict[type, Any]:
        """Исходный словарь моков."""
        return dict(self._mocks)

    @property
    def plugins(self) -> list[Plugin]:
        """Список плагинов."""
        return list(self._plugins)

    # ─────────────────────────────────────────────────────────────────────
    # Внутренние методы: создание машин и контекста
    # ─────────────────────────────────────────────────────────────────────

    def _build_context(self) -> Context:
        """Создаёт Context из текущих user, request, runtime."""
        return Context(
            user=self._user,
            request=self._request,
            runtime=self._runtime,
        )

    def _build_async_machine(self) -> ActionProductMachine:
        """Создаёт асинхронную production-машину с текущими настройками."""
        kwargs: dict[str, Any] = {
            "mode": "test",
            "coordinator": self._coordinator,
            "plugins": self._plugins,
        }
        if self._log_coordinator is not None:
            kwargs["log_coordinator"] = self._log_coordinator
        return ActionProductMachine(**kwargs)

    def _build_sync_machine(self) -> SyncActionProductMachine:
        """Создаёт синхронную production-машину с текущими настройками."""
        kwargs: dict[str, Any] = {
            "mode": "test",
            "coordinator": self._coordinator,
            "plugins": self._plugins,
        }
        if self._log_coordinator is not None:
            kwargs["log_coordinator"] = self._log_coordinator
        return SyncActionProductMachine(**kwargs)

    # ─────────────────────────────────────────────────────────────────────
    # Fluent API (каждый метод возвращает НОВЫЙ TestBench)
    # ─────────────────────────────────────────────────────────────────────

    def _clone(self, **overrides: Any) -> TestBench:
        """Создаёт копию TestBench с переопределёнными полями."""
        return TestBench(
            coordinator=overrides.get("coordinator", self._coordinator),
            mocks=overrides.get("mocks", self._mocks),
            plugins=overrides.get("plugins", self._plugins),
            log_coordinator=overrides.get("log_coordinator", self._log_coordinator),
            user=overrides.get("user", self._user),
            runtime=overrides.get("runtime", self._runtime),
            request=overrides.get("request", self._request),
        )

    def with_user(
        self,
        user_id: str = "test_user",
        roles: list[str] | None = None,
        **kwargs: Any,
    ) -> TestBench:
        """Возвращает новый TestBench с изменённым пользователем."""
        return self._clone(user=UserInfoStub(user_id=user_id, roles=roles, **kwargs))

    def with_runtime(
        self,
        hostname: str = "test-host",
        service_name: str = "test-service",
        service_version: str = "0.0.1",
        **kwargs: Any,
    ) -> TestBench:
        """Возвращает новый TestBench с изменённым окружением."""
        return self._clone(
            runtime=RuntimeInfoStub(
                hostname=hostname,
                service_name=service_name,
                service_version=service_version,
                **kwargs,
            ),
        )

    def with_request(
        self,
        trace_id: str = "test-trace-000",
        request_path: str = "/test",
        protocol: str = "test",
        request_method: str = "TEST",
        **kwargs: Any,
    ) -> TestBench:
        """Возвращает новый TestBench с изменённой информацией о запросе."""
        return self._clone(
            request=RequestInfoStub(
                trace_id=trace_id,
                request_path=request_path,
                protocol=protocol,
                request_method=request_method,
                **kwargs,
            ),
        )

    def with_mocks(self, mocks: dict[type, Any]) -> TestBench:
        """Возвращает новый TestBench с изменёнными моками (замена, не мерж)."""
        return self._clone(mocks=mocks)

    # ─────────────────────────────────────────────────────────────────────
    # Терминальные методы
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        rollup: bool,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Полный прогон действия на async и sync машинах со сравнением результатов.

        Для MockAction — прямой вызов без конвейера.

        Между прогонами async и sync машин сбрасывает состояние всех
        Mock-объектов через _reset_all_mocks(). Это гарантирует, что
        каждая машина работает с чистыми моками, и тесты могут использовать
        assert_called_once_with() без учёта двойного прогона.

        После обоих прогонов моки НЕ сбрасываются — тест видит состояние
        моков после sync-прогона (последнего).

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            rollup: режим автоотката транзакций (обязательный).
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            R — результат выполнения действия (от async-машины).
        """
        if isinstance(action, MockAction):
            return cast("R", action.run(params))

        context = self._build_context()

        # ── Прогон 1: async-машина ──
        async_machine = self._build_async_machine()
        async_result = await async_machine._run_internal(
            context=context,
            action=action,
            params=params,
            resources=self._prepared_mocks or None,
            connections=connections,
            nested_level=0,
            rollup=rollup,
        )

        # ── Сброс моков между прогонами ──
        # Без сброса sync-машина увидит вызовы от async-машины,
        # и assert_called_once_with() в тестах будет падать.
        _reset_all_mocks(self._mocks)

        # ── Прогон 2: sync-машина ──
        sync_machine = self._build_sync_machine()
        sync_result = await sync_machine._run_internal(
            context=context,
            action=action.__class__(),
            params=params,
            resources=self._prepared_mocks or None,
            connections=connections,
            nested_level=0,
            rollup=rollup,
        )

        compare_results(
            async_result, "AsyncMachine",
            sync_result, "SyncMachine",
        )

        return async_result

    async def run_aspect(
        self,
        action: BaseAction[Any, Any],
        aspect_name: str,
        params: BaseParams,
        state: dict[str, Any],
        rollup: bool,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> dict[str, Any]:
        """
        Выполняет один regular-аспект с валидацией state.

        Аргументы:
            action: экземпляр действия.
            aspect_name: имя метода-аспекта.
            params: входные параметры.
            state: словарь state (валидируется по чекерам предшествующих аспектов).
            rollup: режим автоотката (обязательный).
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            dict[str, Any] — результат regular-аспекта.
        """
        context = self._build_context()
        metadata = self._coordinator.get(action.__class__)

        validate_state_for_aspect(metadata, aspect_name, state)

        target_aspect = None
        for aspect_meta in metadata.aspects:
            if aspect_meta.method_name == aspect_name:
                target_aspect = aspect_meta
                break

        if target_aspect is None:
            available = [a.method_name for a in metadata.aspects]
            raise ValueError(
                f"Аспект '{aspect_name}' не найден в {action.__class__.__name__}. "
                f"Доступные: {available}."
            )

        async_machine = self._build_async_machine()
        factory = self._coordinator.get_factory(action.__class__)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            machine_name="TestBench",
            mode="test",
            action_name=action.get_full_class_name(),
            aspect_name=aspect_name,
            context=context,
            state=BaseState(**state) if state else BaseState(),
            params=params,
        )

        box = ToolsBox(
            run_child=self._make_run_child(async_machine, context, rollup),
            factory=factory,
            resources=self._prepared_mocks or None,
            context=context,
            log=log,
            nested_level=1,
            rollup=rollup,
        )

        base_state = BaseState(**state) if state else BaseState()
        conns = connections or {}

        return cast(
            "dict[str, Any]",
            await target_aspect.method_ref(action, params, base_state, box, conns),
        )

    async def run_summary(
        self,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: dict[str, Any],
        rollup: bool,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> BaseResult:
        """
        Выполняет только summary-аспект с валидацией полноты state.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            state: словарь state (валидируется по чекерам всех regular-аспектов).
            rollup: режим автоотката (обязательный).
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            BaseResult — результат summary-аспекта.
        """
        context = self._build_context()
        metadata = self._coordinator.get(action.__class__)

        validate_state_for_summary(metadata, state)

        summary_meta = metadata.get_summary_aspect()
        if summary_meta is None:
            raise ValueError(
                f"Действие {action.__class__.__name__} не содержит summary-аспект."
            )

        async_machine = self._build_async_machine()
        factory = self._coordinator.get_factory(action.__class__)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            machine_name="TestBench",
            mode="test",
            action_name=action.get_full_class_name(),
            aspect_name=summary_meta.method_name,
            context=context,
            state=BaseState(**state) if state else BaseState(),
            params=params,
        )

        box = ToolsBox(
            run_child=self._make_run_child(async_machine, context, rollup),
            factory=factory,
            resources=self._prepared_mocks or None,
            context=context,
            log=log,
            nested_level=1,
            rollup=rollup,
        )

        base_state = BaseState(**state) if state else BaseState()
        conns = connections or {}

        return cast(
            "BaseResult",
            await summary_meta.method_ref(action, params, base_state, box, conns),
        )

    # ─────────────────────────────────────────────────────────────────────
    # Вспомогательные методы
    # ─────────────────────────────────────────────────────────────────────

    def _make_run_child(
        self,
        machine: ActionProductMachine,
        context: Context,
        rollup: bool,
    ) -> Any:
        """
        Создаёт замыкание run_child для ToolsBox.

        Замыкание делегирует вызов дочерних действий в _run_internal
        машины с текущими моками и rollup.
        """
        prepared = self._prepared_mocks

        async def run_child(
            child_action: BaseAction[Any, Any],
            child_params: BaseParams,
            child_connections: dict[str, BaseResourceManager] | None = None,
        ) -> BaseResult:
            if isinstance(child_action, MockAction):
                return child_action.run(child_params)

            return await machine._run_internal(
                context=context,
                action=child_action,
                params=child_params,
                resources=prepared or None,
                connections=child_connections,
                nested_level=1,
                rollup=rollup,
            )

        return run_child
