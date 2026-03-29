# src/action_machine/core/action_test_machine.py
"""
ActionTestMachine — тестовая машина действий с поддержкой моков.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ActionTestMachine наследует ActionProductMachine и добавляет возможность
подстановки зависимостей через словарь моков. Это позволяет тестировать
действия изолированно, заменяя реальные сервисы на моки.

═══════════════════════════════════════════════════════════════════════════════
STATELESS МЕЖДУ ЗАПРОСАМИ
═══════════════════════════════════════════════════════════════════════════════

Как и родительская машина, ActionTestMachine не хранит мутабельного
состояния между вызовами run(). Моки — это неизменяемая конфигурация,
заданная при создании машины. Моки передаются как resources в _run_internal
и имеют приоритет над фабрикой при resolve().

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИП РАБОТЫ МОКОВ
═══════════════════════════════════════════════════════════════════════════════

Моки передаются как словарь {класс_зависимости: mock_значение}.
Тестовая машина подготавливает моки один раз в конструкторе (_prepare_mock)
и затем передаёт их как resources в _run_internal родителя.

ToolsBox при вызове box.resolve(PaymentService) сначала ищет в resources
(т.е. в моках), и только потом обращается к фабрике.

Поддерживаемые типы mock-значений:
- MockAction         → используется как есть
- BaseAction         → используется как есть (выполняется через конвейер)
- BaseResult         → оборачивается в MockAction(result=...)
- callable           → оборачивается в MockAction(side_effect=...)
- любой другой объект → возвращается как есть через resolve()

═══════════════════════════════════════════════════════════════════════════════
ДОСТУП К СОСТОЯНИЮ ПЛАГИНОВ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

Метод run_with_context() возвращает кортеж (result, plugin_ctx), где
plugin_ctx — PluginRunContext, через который можно получить финальное
состояние любого плагина:

    result, plugin_ctx = await machine.run_with_context(context, action, params)
    state = plugin_ctx.get_plugin_state(counter_plugin)

Обычный метод run() возвращает только результат (обратная совместимость).

═══════════════════════════════════════════════════════════════════════════════
ЛОГИРОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

Тестовая машина наследует всю инфраструктуру логирования от родителя:
- ScopedLogger с nest_level в scope для аспектов.
- ScopedLogger с plugin_name и event_name для плагинов.
- Передача log_coordinator в PluginRunContext для создания логгеров.

По умолчанию log_coordinator создаётся с ConsoleLogger(use_colors=True).
В тестах можно передать мок-координатор для проверки логирования.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    machine = ActionTestMachine(
        mocks={
            PaymentService: mock_payment,
            NotificationService: mock_notifier,
        },
    )

    result = await machine.run(
        context=test_context,
        action=CreateOrderAction(),
        params=OrderParams(user_id="test", amount=100.0),
    )

    # Доступ к состоянию плагинов:
    result, plugin_ctx = await machine.run_with_context(
        context=test_context,
        action=CreateOrderAction(),
        params=OrderParams(user_id="test", amount=100.0),
    )
    counter_state = plugin_ctx.get_plugin_state(counter_plugin)
"""

import time
from typing import Any, TypeVar, cast

from action_machine.context.context import Context
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.mock_action import MockAction
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.plugin_run_context import PluginRunContext
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionTestMachine(ActionProductMachine):
    """
    Тестовая машина действий с удобным API для подстановки зависимостей.

    Полностью асинхронная. Принимает словарь моков в конструкторе и передаёт
    их как resources при выполнении, что даёт мокам приоритет над фабрикой.

    Для MockAction выполнение идёт напрямую через .run() (без конвейера).

    Атрибуты:
        _mocks : dict[type, Any]
            Исходный словарь моков.
        _prepared_mocks : dict[type, Any]
            Подготовленные моки (MockAction, BaseAction или объекты).
    """

    def __init__(
        self,
        mocks: dict[type[Any], Any] | None = None,
        mode: str = "test",
        coordinator: GateCoordinator | None = None,
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Инициализирует тестовую машину.

        Аргументы:
            mocks: словарь подстановок {класс_зависимости: mock_значение}.
            mode: режим выполнения (по умолчанию "test").
            coordinator: координатор метаданных и фабрик.
            log_coordinator: координатор логирования.
        """
        super().__init__(
            mode=mode,
            coordinator=coordinator,
            log_coordinator=log_coordinator,
        )

        self._mocks: dict[type[Any], Any] = mocks or {}
        self._prepared_mocks: dict[type[Any], Any] = {}

        for cls, val in self._mocks.items():
            self._prepared_mocks[cls] = self._prepare_mock(val)

    # ─────────────────────────────────────────────────────────────────────
    # Подготовка моков
    # ─────────────────────────────────────────────────────────────────────

    def _prepare_mock(self, value: Any) -> Any:
        """
        Преобразует переданное значение в объект, пригодный для использования.

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

    # ─────────────────────────────────────────────────────────────────────
    # Публичный API: run
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Выполняет действие с поддержкой моков.

        Для MockAction — прямой вызов action.run(params) без конвейера.
        Для обычных действий — вызов _run_internal с моками как resources.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            R — результат выполнения действия.
        """
        if isinstance(action, MockAction):
            return cast(R, action.run(params))

        return await self._run_internal(
            context=context,
            action=action,
            params=params,
            resources=self._prepared_mocks,
            connections=connections,
            nested_level=0,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Публичный API: run_with_context (для тестов плагинов)
    # ─────────────────────────────────────────────────────────────────────

    async def run_with_context(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> tuple[R, PluginRunContext]:
        """
        Выполняет действие и возвращает результат вместе с PluginRunContext.

        Позволяет тестам получить доступ к финальному состоянию плагинов
        через plugin_ctx.get_plugin_state(plugin).

        Для MockAction — прямой вызов без конвейера; plugin_ctx создаётся
        пустой (без событий).

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            Кортеж (R, PluginRunContext).
        """
        if isinstance(action, MockAction):
            plugin_ctx = await self._plugin_coordinator.create_run_context()
            return cast(R, action.run(params)), plugin_ctx

        return await self._run_internal_with_context(
            context=context,
            action=action,
            params=params,
            resources=self._prepared_mocks,
            connections=connections,
            nested_level=0,
        )

    async def _run_internal_with_context(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
    ) -> tuple[R, PluginRunContext]:
        """
        Внутренний метод, аналогичный _run_internal родителя, но возвращающий
        также PluginRunContext для доступа к состояниям плагинов.

        Дублирует логику _run_internal, чтобы сохранить PluginRunContext.
        Используется только через run_with_context().

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы (моки).
            connections: менеджеры ресурсов.
            nested_level: уровень вложенности.

        Возвращает:
            Кортеж (R, PluginRunContext).
        """
        current_nest = nested_level + 1
        start_time = time.time()
        plugin_kwargs = self._build_plugin_emit_kwargs(current_nest)

        try:
            metadata = self._get_metadata(action)
            self._check_action_roles(action, context, metadata)
            conns = self._check_connections(action, connections, metadata)
            factory = self._coordinator.get_factory(action.__class__)
            plugin_ctx = await self._plugin_coordinator.create_run_context()

            log = ScopedLogger(
                coordinator=self._log_coordinator,
                nest_level=current_nest,
                machine_name=self.__class__.__name__,
                mode=self._mode,
                action_name=action.get_full_class_name(),
                aspect_name="",
                context=context,
            )

            async def run_child(
                child_action: BaseAction[Any, Any],
                child_params: BaseParams,
                child_connections: dict[str, BaseResourceManager] | None = None,
            ) -> BaseResult:
                return await self._run_internal(
                    context=context,
                    action=child_action,
                    params=child_params,
                    resources=resources,
                    connections=child_connections,
                    nested_level=current_nest,
                )

            box = ToolsBox(
                run_child=run_child,
                factory=factory,
                resources=resources,
                context=context,
                log=log,
                nested_level=current_nest,
            )

            await plugin_ctx.emit_event(
                event_name="global_start",
                action=action,
                params=params,
                state_aspect=None,
                is_summary=False,
                result=None,
                duration=None,
                factory=factory,
                context=context,
                nest_level=current_nest,
                **plugin_kwargs,
            )

            state = await self._execute_regular_aspects(
                action, params, box, conns, context, metadata, plugin_ctx
            )

            summary_meta = self._get_summary_aspect(metadata)
            result = await self._call_aspect(
                summary_meta, action, params, state, box, conns, context
            )

            total_duration = time.time() - start_time

            await plugin_ctx.emit_event(
                event_name="global_finish",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=False,
                result=result,
                duration=total_duration,
                factory=factory,
                context=context,
                nest_level=current_nest,
                **plugin_kwargs,
            )

            return cast(R, result), plugin_ctx

        finally:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Внутренний метод выполнения (переопределение)
    # ─────────────────────────────────────────────────────────────────────

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
    ) -> R:
        """
        Внутренний метод выполнения с поддержкой моков.

        Для MockAction — прямой вызов без конвейера.
        Для обычных действий — делегирование родительскому _run_internal.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы (моки).
            connections: менеджеры ресурсов.
            nested_level: текущий уровень вложенности.

        Возвращает:
            R — результат действия.
        """
        if isinstance(action, MockAction):
            return cast(R, action.run(params))

        return await super()._run_internal(
            context=context,
            action=action,
            params=params,
            resources=resources,
            connections=connections,
            nested_level=nested_level,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Утилиты для тестирования
    # ─────────────────────────────────────────────────────────────────────

    def build_factory(
        self, action_class: type[BaseAction[Any, Any]],
    ) -> DependencyFactory:
        """
        Возвращает DependencyFactory для класса действия через координатор.

        Полезно для тестирования отдельных аспектов вне машины.

        Аргументы:
            action_class: класс действия (не экземпляр).

        Возвращает:
            DependencyFactory — stateless-фабрика зависимостей для класса.

        Пример:
            machine = ActionTestMachine(mocks={PaymentService: mock_payment})
            factory = machine.build_factory(CreateOrderAction)
            box = ToolsBox(factory=factory, resources=machine._prepared_mocks, ...)
            payment = box.resolve(PaymentService)  # вернёт mock_payment
        """
        return self._coordinator.get_factory(action_class)
