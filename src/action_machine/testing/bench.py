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
ПРОКИДЫВАНИЕ ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Терминальные методы (run, run_aspect, run_summary) принимают обязательный
параметр rollup: bool без значения по умолчанию. Тестировщик явно
выбирает режим.

Rollup прокидывается в machine._run_internal(rollup=rollup), откуда
попадает в ToolsBox(rollup=rollup). ToolsBox использует rollup при:
- resolve() → factory.resolve(cls, rollup=rollup).
- run() → замыкание run_child передаёт rollup рекурсивно.

Connections создаются СНАРУЖИ TestBench вызывающим кодом:

    db = PostgresConnectionManager(params, rollup=True)
    result = await bench.run(
        action, params, rollup=True,
        connections={"db": db},
    )

TestBench НЕ модифицирует connections — ответственность за создание
менеджеров с rollup лежит на тестировщике. Это явное и прозрачное
решение: тестировщик видит, какие ресурсы работают в режиме rollup.

═══════════════════════════════════════════════════════════════════════════════
FLUENT API (IMMUTABLE)
═══════════════════════════════════════════════════════════════════════════════

Каждый fluent-метод возвращает НОВЫЙ экземпляр TestBench:

    bench = TestBench(mocks={PaymentService: mock})
    admin_bench = bench.with_user(user_id="admin", roles=["admin"])
    traced_bench = bench.with_request(trace_id="trace-123")

    # bench, admin_bench, traced_bench — три разных объекта.
    # bench не изменился после вызовов with_user и with_request.

Доступные fluent-методы:
    .with_user(user_id=..., roles=...)     → новый TestBench с изменённым user
    .with_runtime(hostname=..., ...)       → новый TestBench с изменённым runtime
    .with_request(trace_id=..., ...)       → новый TestBench с изменённым request
    .with_mocks({Service: mock, ...})      → новый TestBench с изменёнными моками

═══════════════════════════════════════════════════════════════════════════════
ПОДГОТОВКА МОКОВ
═══════════════════════════════════════════════════════════════════════════════

TestBench подготавливает моки по тем же правилам, что и тестовые машины:
- MockAction         → используется как есть.
- BaseAction         → используется как есть.
- callable           → оборачивается в MockAction(side_effect=...).
- BaseResult         → оборачивается в MockAction(result=...).
- любой другой объект → используется как есть (для resolve()).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing import TestBench, MockAction

    # Базовый bench:
    bench = TestBench(mocks={PaymentService: mock_payment})

    # Fluent — immutable:
    admin_bench = bench.with_user(user_id="admin", roles=["admin"])

    # Полный прогон без rollup:
    result = await admin_bench.run(
        CreateOrderAction(),
        OrderParams(user_id="u1", amount=100.0),
        rollup=False,
    )

    # Полный прогон с rollup на production-базе:
    db = PostgresConnectionManager(prod_params, rollup=True)
    result = await bench.run(
        CreateOrderAction(),
        OrderParams(user_id="u1", amount=100.0),
        rollup=True,
        connections={"db": db},
    )
    # INSERT выполнился, но COMMIT → ROLLBACK
    # Зависимости через resolve() тоже получили rollup=True
    # RedisCache через resolve() → RollupNotSupportedError

    # Тест одного аспекта:
    aspect_result = await bench.run_aspect(
        CreateOrderAction(), "process_payment",
        OrderParams(user_id="u1", amount=100.0),
        state={"validated_user": "u1"},
        rollup=False,
    )

    # Тест summary:
    summary_result = await bench.run_summary(
        CreateOrderAction(),
        OrderParams(user_id="u1", amount=100.0),
        state={"validated_user": "u1", "txn_id": "TXN-1"},
        rollup=False,
    )
"""

from __future__ import annotations

from typing import Any, TypeVar, cast

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


def _prepare_mock(value: Any) -> Any:
    """
    Преобразует mock-значение в объект, пригодный для использования в resources.

    Правила преобразования:
    - MockAction   → используется как есть.
    - BaseAction   → используется как есть.
    - callable     → оборачивается в MockAction(side_effect=value).
    - BaseResult   → оборачивается в MockAction(result=value).
    - любой другой → используется как есть (для resolve()).

    Аргументы:
        value: mock-значение из словаря.

    Возвращает:
        Подготовленный объект.
    """
    if isinstance(value, MockAction):
        return value
    if isinstance(value, BaseAction):
        return value
    if callable(value):
        return MockAction(side_effect=value)
    if isinstance(value, BaseResult):
        return MockAction(result=value)
    return value


def _prepare_all_mocks(mocks: dict[type, Any]) -> dict[type, Any]:
    """
    Подготавливает все моки из словаря.

    Аргументы:
        mocks: исходный словарь {класс_зависимости: mock_значение}.

    Возвращает:
        Новый словарь с подготовленными значениями.
    """
    return {cls: _prepare_mock(val) for cls, val in mocks.items()}


class TestBench:
    """
    Единая immutable точка входа для тестирования действий ActionMachine.

    Каждый fluent-вызов возвращает НОВЫЙ экземпляр — оригинал не мутируется.
    Терминальные методы прогоняют действие на коллекции машин (async + sync)
    и сравнивают результаты. Rollup прокидывается через _run_internal
    в ToolsBox и далее в resolve() и run().

    Атрибуты (все приватные, доступны через свойства):
        _coordinator : GateCoordinator
            Координатор метаданных и фабрик. Общий для всех машин.
        _mocks : dict[type, Any]
            Исходный словарь моков (до подготовки).
        _prepared_mocks : dict[type, Any]
            Подготовленные моки (после _prepare_mock).
        _plugins : list[Plugin]
            Список плагинов для машин.
        _log_coordinator : LogCoordinator | None
            Координатор логирования. None → машины создают дефолтный.
        _user : UserInfo
            Информация о пользователе для контекста.
        _runtime : RuntimeInfo
            Информация об окружении для контекста.
        _request : RequestInfo
            Информация о запросе для контекста.
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
        """
        Создаёт Context из текущих user, request, runtime.

        Возвращает:
            Context — контекст выполнения для машин.
        """
        return Context(
            user=self._user,
            request=self._request,
            runtime=self._runtime,
        )

    def _build_async_machine(self) -> ActionProductMachine:
        """
        Создаёт асинхронную production-машину с текущими настройками.

        Возвращает:
            ActionProductMachine — async-машина.
        """
        kwargs: dict[str, Any] = {
            "mode": "test",
            "coordinator": self._coordinator,
            "plugins": self._plugins,
        }
        if self._log_coordinator is not None:
            kwargs["log_coordinator"] = self._log_coordinator
        return ActionProductMachine(**kwargs)

    def _build_sync_machine(self) -> SyncActionProductMachine:
        """
        Создаёт синхронную production-машину с текущими настройками.

        Возвращает:
            SyncActionProductMachine — sync-машина.
        """
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
        """
        Создаёт копию TestBench с переопределёнными полями.

        Все поля, не указанные в overrides, копируются из текущего экземпляра.

        Аргументы:
            **overrides: поля для переопределения (user, runtime, request, mocks и т.д.).

        Возвращает:
            Новый экземпляр TestBench.
        """
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
        """
        Возвращает новый TestBench с изменённым пользователем.

        Аргументы:
            user_id: идентификатор пользователя.
            roles: список ролей. По умолчанию ["tester"].
            **kwargs: дополнительные поля для UserInfo.extra.

        Возвращает:
            Новый TestBench с обновлённым user.
        """
        return self._clone(user=UserInfoStub(user_id=user_id, roles=roles, **kwargs))

    def with_runtime(
        self,
        hostname: str = "test-host",
        service_name: str = "test-service",
        service_version: str = "0.0.1",
        **kwargs: Any,
    ) -> TestBench:
        """
        Возвращает новый TestBench с изменённым окружением.

        Аргументы:
            hostname: имя хоста.
            service_name: название сервиса.
            service_version: версия сервиса.
            **kwargs: дополнительные поля.

        Возвращает:
            Новый TestBench с обновлённым runtime.
        """
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
        """
        Возвращает новый TestBench с изменённой информацией о запросе.

        Аргументы:
            trace_id: идентификатор трассировки.
            request_path: путь запроса.
            protocol: протокол.
            request_method: HTTP-метод или тип вызова.
            **kwargs: дополнительные поля.

        Возвращает:
            Новый TestBench с обновлённым request.
        """
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
        """
        Возвращает новый TestBench с изменёнными моками.

        Новые моки ЗАМЕНЯЮТ текущие (не мержатся). Для добавления
        моков к существующим используйте {**bench.mocks, NewService: mock}.

        Аргументы:
            mocks: новый словарь моков.

        Возвращает:
            Новый TestBench с обновлёнными моками.
        """
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

        Для MockAction — прямой вызов без конвейера (одна машина, без сравнения).

        Rollup прокидывается в _run_internal(), откуда попадает в ToolsBox.
        ToolsBox передаёт rollup в factory.resolve() и через замыкание
        run_child в дочерние действия.

        Connections создаются вызывающим кодом с нужным rollup:
            db = PostgresConnectionManager(params, rollup=True)
            result = await bench.run(action, params, rollup=True, connections={"db": db})

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            rollup: режим автоотката транзакций. Обязательный параметр
                    без значения по умолчанию.
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            R — результат выполнения действия (от async-машины).

        Исключения:
            ResultMismatchError: если результаты async и sync машин расходятся.
            RollupNotSupportedError: если rollup=True и зависимость через
                resolve() не поддерживает rollup.
        """
        if isinstance(action, MockAction):
            return cast(R, action.run(params))

        context = self._build_context()

        # Async-машина
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

        # Sync-машина (выполняем _run_internal напрямую, т.к. уже в async-контексте)
        sync_machine = self._build_sync_machine()
        sync_result = await sync_machine._run_internal(
            context=context,
            action=action.__class__(),  # новый экземпляр для изоляции
            params=params,
            resources=self._prepared_mocks or None,
            connections=connections,
            nested_level=0,
            rollup=rollup,
        )

        # Сравнение результатов
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

        Перед выполнением проверяет state через validate_state_for_aspect():
        все обязательные поля от предшествующих аспектов должны присутствовать
        и проходить проверку чекерами.

        Rollup прокидывается в ToolsBox, откуда передаётся в resolve()
        и run() дочерних действий.

        Аспект выполняется только на async-машине (аспект — async-метод).
        Sync-прогон не выполняется, сравнение не производится.

        Аргументы:
            action: экземпляр действия.
            aspect_name: имя метода-аспекта для выполнения.
            params: входные параметры действия.
            state: словарь state, передаваемый в аспект. Валидируется
                   по чекерам предшествующих аспектов.
            rollup: режим автоотката транзакций. Обязательный параметр.
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            dict[str, Any] — результат regular-аспекта (словарь новых полей state).

        Исключения:
            StateValidationError: если state не содержит обязательных полей
                или значения не проходят чекеры.
        """
        context = self._build_context()
        metadata = self._coordinator.get(action.__class__)

        # Валидация state
        validate_state_for_aspect(metadata, aspect_name, state)

        # Поиск аспекта
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

        # Создаём инфраструктуру для вызова аспекта
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
            state=BaseState(state),
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

        base_state = BaseState(state)
        conns = connections or {}

        return cast(dict[str, Any], await target_aspect.method_ref(action, params, base_state, box, conns))

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

        Перед выполнением проверяет state через validate_state_for_summary():
        все обязательные поля от ВСЕХ regular-аспектов должны присутствовать.

        Rollup прокидывается в ToolsBox.

        Summary выполняется только на async-машине.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры действия.
            state: словарь state. Валидируется по чекерам всех
                   regular-аспектов.
            rollup: режим автоотката транзакций. Обязательный параметр.
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            BaseResult — результат summary-аспекта.

        Исключения:
            StateValidationError: если state неполный или невалидный.
            ValueError: если действие не содержит summary-аспект.
        """
        context = self._build_context()
        metadata = self._coordinator.get(action.__class__)

        # Валидация state
        validate_state_for_summary(metadata, state)

        # Поиск summary-аспекта
        summary_meta = metadata.get_summary_aspect()
        if summary_meta is None:
            raise ValueError(
                f"Действие {action.__class__.__name__} не содержит summary-аспект."
            )

        # Создаём инфраструктуру
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
            state=BaseState(state),
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

        base_state = BaseState(state)
        conns = connections or {}

        return cast(BaseResult, await summary_meta.method_ref(action, params, base_state, box, conns))

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
        машины с текущими моками и rollup. Rollup прокидывается
        на все уровни вложенности.

        Аргументы:
            machine: машина для выполнения дочерних действий.
            context: контекст выполнения.
            rollup: режим автоотката.

        Возвращает:
            Async callable для передачи в ToolsBox.run_child.
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
