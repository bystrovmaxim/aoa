# src/action_machine/core/action_product_machine.py
"""
ActionProductMachine — асинхронная production-реализация машины действий.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ActionProductMachine — центральный асинхронный исполнитель действий (Action)
в системе. Получает экземпляр действия, входные параметры и context,
после чего:

1. Checks ролевые ограничения (@check_roles) по scratch-атрибуту ``_role_info``.
2. Валидирует соединения (@connection) по scratch-списку ``_connection_info``.
3. Получает stateless-фабрику зависимостей из ``DependencyFactory`` по ``_depends_info``.
4. Создаёт изолированный PluginRunContext для текущего запроса.
5. Последовательно выполняет regular-аспекты, проверяя результаты checkerами.
   Для аспектов с @context_requires создаёт ContextView и передаёт как ctx.
   Для каждого успешного аспекта добавляет SagaFrame в локальный стек
   компенсации (если rollup=False).
6. Выполняет summary-аспект, формирующий итоговый Result.
7. При исключении в аспекте:
   a. Размотка стека компенсации (_rollback_saga) в обратном порядке —
      вызов compensatorов уже выполненных аспектов.
   b. Эмитирует типизированные события плагинам (Saga-события,
      BeforeOnErrorAspectEvent / AfterOnErrorAspectEvent или
      UnhandledErrorEvent).
   c. Ищет подходящий обработчик @on_error.
   Для обработчиков с @context_requires создаёт отдельный ContextView.
8. Уведомляет плагины о событиях через PluginRunContext.emit_event(),
   передавая объекты событий из иерархии BasePluginEvent.

Исполнение **не** обходит конвейер через чтение facet-снимков координатора:
все нужные для run() данные читаются **напрямую** с класса действия из scratch,
который записали декораторы (``_role_info``, ``_connection_info``,
``_depends_info``, ``_new_aspect_meta``, ``_checker_meta``, ``_on_error_meta``,
``_compensate_meta``, …). Типы snapshot-элементов аспектов/checkerов/обработчиков
из runtime metadata только как базовый снимок полей, не как снимок координатора.

═══════════════════════════════════════════════════════════════════════════════
ТИПИЗИРОВАННЫЕ СОБЫТИЯ ПЛАГИНОВ
═══════════════════════════════════════════════════════════════════════════════

Машина создаёт конкретные объекты событий из иерархии BasePluginEvent
в ключевых точках конвейера и передаёт их в plugin_ctx.emit_event():

    GlobalStartEvent              — перед первым аспектом
    BeforeRegularAspectEvent      — перед каждым regular-аспектом
    AfterRegularAspectEvent       — после каждого regular-аспекта
    BeforeSummaryAspectEvent      — перед summary-аспектом
    AfterSummaryAspectEvent       — после summary-аспекта
    SagaRollbackStartedEvent      — начало размотки стека компенсации
    BeforeCompensateAspectEvent   — перед каждым compensatorом
    AfterCompensateAspectEvent    — после успешного compensatorа
    CompensateFailedEvent         — сбой compensatorа
    SagaRollbackCompletedEvent    — конец размотки стека (с итогами)
    BeforeOnErrorAspectEvent      — перед вызовом @on_error обработчика
    AfterOnErrorAspectEvent       — после успешного @on_error обработчика
    UnhandledErrorEvent           — error без подходящего @on_error
    GlobalFinishEvent             — после успешного завершения конвейера

Каждый класс события содержит РОВНО те поля, которые имеют смысл для
данного типа. Обработчики плагинов подписываются через @on(EventClass)
и получают типизированный объект без Optional-полей.

═══════════════════════════════════════════════════════════════════════════════
КОМПЕНСАЦИЯ (SAGA)
═══════════════════════════════════════════════════════════════════════════════

При выполнении regular-аспектов машина накапливает локальный стек
SagaFrame. Каждый фрейм содержит:
    - compensator: CompensatorMeta (или None если не определён)
    - aspect_name: имя аспекта для диагностики
    - state_before: state ДО аспекта
    - state_after: state ПОСЛЕ аспекта (None если checker отклонил)

При ошибке в любом аспекте стек разматывается в обратном порядке
methodом _rollback_saga(). Каждый фрейм с непустым compensator
вызывает method-compensator.

Ключевые правила:
    - Стек ЛОКАЛЬНЫЙ для каждого _run_internal. Глобального стека нет.
    - При rollup=True стек НЕ создаётся, compensatorы НЕ вызываются.
    - Ошибки compensatorов МОЛЧАЛИВЫЕ — не прерывают размотку,
      не пробрасываются в @on_error. Информация о сбоях доступна
      ТОЛЬКО через CompensateFailedEvent.
    - Размотка выполняется ДО вызова @on_error — сначала откат,
      потом обработка бизнес-логики.

Порядок обработки ошибки:
    1. Аспект бросает исключение.
    2. Фрейм для упавшего аспекта НЕ добавляется в стек.
    3. _rollback_saga() — размотка в обратном порядке.
    4. _handle_aspect_error() — поиск @on_error обработчика.

═══════════════════════════════════════════════════════════════════════════════
УПРАВЛЯЕМЫЙ ДОСТУП К КОНТЕКСТУ
═══════════════════════════════════════════════════════════════════════════════

Аспекты, обработчики ошибок и compensatorы НЕ имеют прямого доступа
к contextу. Публичное свойство context удалено из ToolsBox. Единственный
путь к данным contextа — через ContextView, который машина создаёт для
methodов с @context_requires.

При вызове аспекта машина проверяет aspect_meta.context_keys:
    - Если непустой → создаёт ContextView(context, context_keys),
      передаёт как 6-й аргумент (ctx).
    - Если пустой → вызывает с 5 аргументами (без ctx).

Аналогично для обработчиков ошибок (6 или 7 parameters)
и compensatorов (7 или 8 parameters).

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК АСПЕКТОВ (@on_error)
═══════════════════════════════════════════════════════════════════════════════

Когда regular- или summary-аспект бросает исключение, машина:

1. Останавливает выполнение конвейера аспектов.
2. Если rollup=False и стек компенсации непуст:
   → _rollback_saga() — размотка стека в обратном порядке.
3. Checks наличие подходящего @on_error обработчика.
4. Если обработчик найден:
   a. Эмитирует BeforeOnErrorAspectEvent плагинам.
   b. Вызывает обработчик (с ContextView если context_keys).
   c. Эмитирует AfterOnErrorAspectEvent плагинам.
   d. Returns Result от обработчика.
5. Если обработчик не найден:
   a. Эмитирует UnhandledErrorEvent плагинам.
   b. Пробрасывает исходное исключение наружу.
6. Если обработчик сам бросает исключение — OnErrorHandlerError.

═══════════════════════════════════════════════════════════════════════════════
ПУБЛИЧНЫЙ API
═══════════════════════════════════════════════════════════════════════════════

    await machine.run(context, action, params, connections)

Метод run() — асинхронный. Для синхронного использования существует
отдельный класс SyncActionProductMachine.
Production-машины всегда передают rollup=False в _run_internal().

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW ВЫПОЛНЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

    machine.run(context, action, params, connections)
        │
        ├── 1. _role_checker.check(action, context, runtime)
        ├── 2. _connection_validator.validate(action, connections, runtime)
        ├── 3. _dependency_factory_for(action.__class__)
        ├── 4. plugin_ctx = plugin_coordinator.create_run_context()
        ├── 5. plugin_ctx.emit_event(GlobalStartEvent(...))
        ├── 6. _execute_aspects_with_error_handling(...)
        │       ├── _execute_regular_aspects(...)
        │       │       └── для каждого regular aspect snapshot:
        │       │           ├── emit_event(BeforeRegularAspectEvent(...))
        │       │           ├── _call_aspect (с ContextView если context_keys)
        │       │           ├── _apply_checkers(...)
        │       │           ├── saga_stack.append(SagaFrame(...))
        │       │           └── emit_event(AfterRegularAspectEvent(...))
        │       ├── emit_event(BeforeSummaryAspectEvent(...))
        │       ├── _call_aspect(summary, ...)
        │       ├── emit_event(AfterSummaryAspectEvent(...))
        │       └── при исключении:
        │               ├── _rollback_saga(saga_stack, error, ...)
        │               │       ├── emit_event(SagaRollbackStartedEvent(...))
        │               │       ├── для каждого фрейма (в обратном порядке):
        │               │       │   ├── emit_event(BeforeCompensateAspectEvent)
        │               │       │   ├── вызвать compensator
        │               │       │   └── emit_event(After... или CompensateFailed...)
        │               │       └── emit_event(SagaRollbackCompletedEvent(...))
        │               ├── _handle_aspect_error(...)
        │               │       ├── ищет обработчик по isinstance
        │               │       ├── emit_event(BeforeOnErrorAspectEvent(...))
        │               │       ├── вызывает handler → Result
        │               │       ├── emit_event(AfterOnErrorAspectEvent(...))
        │               │       └── или emit_event(UnhandledErrorEvent(...))
        │               └── возвращает Result от обработчика
        ├── 7. plugin_ctx.emit_event(GlobalFinishEvent(...))
        └── 8. return Result
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from action_machine.aspects.aspect_gate_host_inspector import AspectGateHostInspector
from action_machine.auth.constants import ROLE_ANY, ROLE_NONE
from action_machine.checkers.checker_gate_host_inspector import CheckerGateHostInspector
from action_machine.compensate.compensate_gate_host_inspector import (
    CompensateGateHostInspector,
)
from action_machine.context.context import Context
from action_machine.context.context_view import ContextView
from action_machine.core.components.aspect_executor import AspectExecutor
from action_machine.core.components.connection_validator import ConnectionValidator
from action_machine.core.components.error_handler_executor import ErrorHandlerExecutor
from action_machine.core.components.role_checker import RoleChecker
from action_machine.core.components.saga_coordinator import SagaCoordinator
from action_machine.core.components.tools_box_factory import ToolsBoxFactory
from action_machine.core.base_action import BaseAction
from action_machine.core.base_action_machine import BaseActionMachine
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.core.exceptions import (
    AuthorizationError,
    ConnectionValidationError,
    OnErrorHandlerError,
    ValidationFieldError,
)
from action_machine.core.saga_frame import SagaFrame
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.on_error.on_error_gate_host_inspector import OnErrorGateHostInspector
from action_machine.plugins.events import (
    AfterCompensateAspectEvent,
    AfterOnErrorAspectEvent,
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BeforeCompensateAspectEvent,
    BeforeOnErrorAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    CompensateFailedEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
    SagaRollbackCompletedEvent,
    SagaRollbackStartedEvent,
    UnhandledErrorEvent,
)
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


def _scratch_aspects(
    cls: type[BaseAction],
) -> list[AspectGateHostInspector.Snapshot.Aspect]:
    return list(cls.scratch_aspects())


def _scratch_checkers_for_aspect(
    cls: type[BaseAction],
    aspect_name: str,
    func: Any,
) -> tuple[CheckerGateHostInspector.Snapshot.Checker, ...]:
    return tuple(cls.scratch_checkers_for_aspect(aspect_name, method_ref=func))


def _scratch_error_handlers(
    cls: type[BaseAction],
) -> tuple[OnErrorGateHostInspector.Snapshot.ErrorHandler, ...]:
    return tuple(cls.scratch_error_handlers())


def _scratch_compensators(
    cls: type[BaseAction],
) -> tuple[CompensateGateHostInspector.Snapshot.Compensator, ...]:
    return tuple(cls.scratch_compensators())


def _scratch_connection_keys(cls: type[BaseAction]) -> tuple[str, ...]:
    return tuple(cls.scratch_connection_keys())


def _role_spec_from_coordinator(action_cls: type, coordinator: GateCoordinator) -> Any:
    """
    Спецификация @check_roles из кеша снимка ``role`` координатора.

    Единый источник с узлом графа (``RoleGateHostInspector.Snapshot``).
    """
    snap = coordinator.get_snapshot(action_cls, "role")
    return getattr(snap, "spec", None) if snap is not None else None


@dataclass(frozen=True)
class _ActionExecutionCache:
    """Per-run snapshot from class scratch attributes (roles, connections, pipeline)."""

    role_spec: Any
    connection_keys: tuple[str, ...]
    regular_aspects: tuple[AspectGateHostInspector.Snapshot.Aspect, ...]
    checkers_by_aspect: dict[str, tuple[CheckerGateHostInspector.Snapshot.Checker, ...]]
    has_compensators: bool
    error_handlers: tuple[OnErrorGateHostInspector.Snapshot.ErrorHandler, ...]
    summary_aspect: AspectGateHostInspector.Snapshot.Aspect | None
    compensators_by_aspect: dict[
        str,
        CompensateGateHostInspector.Snapshot.Compensator | None,
    ]

    @classmethod
    def from_action_class(
        cls,
        action_cls: type,
        *,
        gate_coordinator: GateCoordinator,
    ) -> _ActionExecutionCache:
        aspects = _scratch_aspects(action_cls)
        regular = tuple(a for a in aspects if a.aspect_type == "regular")
        summary = next((a for a in aspects if a.aspect_type == "summary"), None)
        checkers_by_aspect = {
            a.method_name: _scratch_checkers_for_aspect(action_cls, a.method_name, a.method_ref)
            for a in regular
        }
        compensators = _scratch_compensators(action_cls)
        compensators_by_aspect: dict[
            str,
            CompensateGateHostInspector.Snapshot.Compensator | None,
        ] = {}
        for aspect in regular:
            compensators_by_aspect[aspect.method_name] = next(
                (c for c in compensators if c.target_aspect_name == aspect.method_name),
                None,
            )
        return cls(
            role_spec=_role_spec_from_coordinator(action_cls, gate_coordinator),
            connection_keys=_scratch_connection_keys(action_cls),
            regular_aspects=regular,
            checkers_by_aspect=checkers_by_aspect,
            has_compensators=len(compensators) > 0,
            error_handlers=_scratch_error_handlers(action_cls),
            summary_aspect=summary,
            compensators_by_aspect=compensators_by_aspect,
        )

    @classmethod
    def from_coordinator_facets(
        cls,
        action_cls: type,
        *,
        gate_coordinator: GateCoordinator,
    ) -> _ActionExecutionCache:
        """
        Same pipeline layout as ``from_action_class``, but aspects/checkers/
        compensators/error-handlers/connections come from facet snapshots
        (``get_snapshot``) instead of ``BaseAction.scratch_*`` helpers.
        """
        asp_snap = gate_coordinator.get_snapshot(action_cls, "aspect")
        aspects = getattr(asp_snap, "aspects", ()) if asp_snap is not None else ()
        regular = tuple(a for a in aspects if a.aspect_type == "regular")
        summary = next((a for a in aspects if a.aspect_type == "summary"), None)

        ch_snap = gate_coordinator.get_snapshot(action_cls, "checker")
        all_checkers = getattr(ch_snap, "checkers", ()) if ch_snap is not None else ()
        checkers_by_aspect: dict[str, tuple[CheckerGateHostInspector.Snapshot.Checker, ...]] = {}
        for a in regular:
            checkers_by_aspect[a.method_name] = tuple(
                c for c in all_checkers if c.method_name == a.method_name
            )

        comp_snap = gate_coordinator.get_snapshot(action_cls, "compensator")
        compensators = getattr(comp_snap, "compensators", ()) if comp_snap is not None else ()
        compensators_by_aspect: dict[
            str,
            CompensateGateHostInspector.Snapshot.Compensator | None,
        ] = {}
        for aspect in regular:
            compensators_by_aspect[aspect.method_name] = next(
                (c for c in compensators if c.target_aspect_name == aspect.method_name),
                None,
            )

        eh_snap = gate_coordinator.get_snapshot(action_cls, "error_handler")
        error_handlers = getattr(eh_snap, "error_handlers", ()) if eh_snap is not None else ()

        conn_snap = gate_coordinator.get_snapshot(action_cls, "connections")
        if conn_snap is not None:
            connection_keys = tuple(c.key for c in conn_snap.connections)
        else:
            connection_keys = ()

        return cls(
            role_spec=_role_spec_from_coordinator(action_cls, gate_coordinator),
            connection_keys=connection_keys,
            regular_aspects=regular,
            checkers_by_aspect=checkers_by_aspect,
            has_compensators=len(compensators) > 0,
            error_handlers=error_handlers,
            summary_aspect=summary,
            compensators_by_aspect=compensators_by_aspect,
        )


class ActionProductMachine(BaseActionMachine):
    """
    Асинхронная production-реализация машины действий.

    Выполняет действие по конвейеру аспектов, проверяет роли и соединения,
    применяет checkerы к resultм аспектов, создаёт ContextView для
    аспектов с @context_requires, накапливает стек компенсации (SagaFrame),
    при ошибке разматывает стек компенсации в обратном порядке, эмитирует
    типизированные события плагинам, обрабатывает ошибки через @on_error
    и уведомляет плагины о событиях жизненного цикла.

    Метаданные конвейера (аспекты, checkerы, compensatorы и т.д.) читаются
    со scratch класса. Спецификация ролей (@check_roles) берётся из
    ``GateCoordinator.get_snapshot(action_cls, \"role\")`` (снимок
    ``RoleGateHostInspector``), тот же источник, что и граф.

    Атрибуты:
        _mode : str
            Режим выполнения ("production", "test", "staging" и т.д.).
        _plugin_coordinator : PluginCoordinator
            Stateless-координатор плагинов.
        _log_coordinator : LogCoordinator
            Координатор логирования.
        _coordinator : GateCoordinator
            Граф, кеш снимков фасетов и runtime metadata; для ролей исполнения
            используется снимок ``role``.

    Снимок конвейера и фабрика зависимостей на каждый запуск строятся заново
    из scratch класса действия (без кэша).
    """

    @staticmethod
    def create_default_coordinator() -> GateCoordinator:
        """Create and build coordinator with full default inspector set."""
        return CoreActionMachine.create_coordinator()

    def __init__(
        self,
        mode: str,
        *,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
        coordinator: GateCoordinator | None = None,
        role_checker: RoleChecker | None = None,
        connection_validator: ConnectionValidator | None = None,
        tools_box_factory: ToolsBoxFactory | None = None,
        aspect_executor: AspectExecutor | None = None,
        error_handler_executor: ErrorHandlerExecutor | None = None,
        saga_coordinator: SagaCoordinator | None = None,
    ) -> None:
        """
        Инициализирует машину действий.

        Args:
            mode: режим выполнения (required, не пустой).
            plugins: список экземпляров плагинов (по умолчанию пустой).
            log_coordinator: координатор логирования. Если не указан, создаётся
                             координатор с одним ConsoleLogger(use_colors=True).
            coordinator: ``GateCoordinator`` для графа; если None — создаётся
                         и сразу строится default coordinator.
            role_checker: опциональный компонент проверки ролей.
            connection_validator: опциональный компонент валидации connections.
            tools_box_factory: опциональная фабрика ToolsBox.
            aspect_executor: опциональный исполнитель одного аспекта.
            error_handler_executor: опциональный исполнитель @on_error.
            saga_coordinator: опциональный координатор rollback/Saga.

        Raises:
            ValueError: если mode — пустая строка.
        """
        if not mode:
            raise ValueError("mode must be non-empty")

        self._mode: str = mode
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
        )

        if log_coordinator is None:
            log_coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
        self._log_coordinator: LogCoordinator = log_coordinator
        self._coordinator = (
            coordinator if coordinator is not None else self.create_default_coordinator()
        )
        if not self._coordinator.is_built:
            raise RuntimeError(
                "ActionProductMachine requires a built GateCoordinator. "
                "Call register(...).build() before passing custom coordinator.",
            )

        # Step 1 wiring: extension points and deterministic component order.
        self._role_checker = (
            role_checker if role_checker is not None else RoleChecker(self._coordinator)
        )
        self._connection_validator = (
            connection_validator
            if connection_validator is not None
            else ConnectionValidator(self._coordinator)
        )
        self._tools_box_factory = (
            tools_box_factory
            if tools_box_factory is not None
            else ToolsBoxFactory(self._log_coordinator, self._coordinator)
        )
        self._aspect_executor = (
            aspect_executor if aspect_executor is not None else AspectExecutor()
        )
        self._error_handler_executor = (
            error_handler_executor
            if error_handler_executor is not None
            else ErrorHandlerExecutor()
        )
        self._saga_coordinator = (
            saga_coordinator
            if saga_coordinator is not None
            else SagaCoordinator(
                self._aspect_executor,
                self._error_handler_executor,
                self._plugin_coordinator,
                self._log_coordinator,
            )
        )

    def _get_execution_cache(self, action_cls: type) -> _ActionExecutionCache:
        return _ActionExecutionCache.from_action_class(
            action_cls,
            gate_coordinator=self._coordinator,
        )

    def _dependency_factory_for(self, action_cls: type) -> DependencyFactory:
        return DependencyFactory(tuple(getattr(action_cls, "_depends_info", ()) or ()))

    # ─────────────────────────────────────────────────────────────────────
    # Проверка checkerов
    # ─────────────────────────────────────────────────────────────────────

    def _apply_checkers(
        self,
        checkers: tuple[CheckerGateHostInspector.Snapshot.Checker, ...],
        result: dict[str, Any],
    ) -> None:
        """Применяет все checkerы к словарю result аспекта."""
        for checker_meta in checkers:
            checker_instance = checker_meta.checker_class(
                checker_meta.field_name,
                required=checker_meta.required,
                **checker_meta.extra_params,
            )
            checker_instance.check(result)

    # ─────────────────────────────────────────────────────────────────────
    # Проверка ролей
    # ─────────────────────────────────────────────────────────────────────

    def _check_none_role(self, user_roles: list[str]) -> bool:
        """Проверка для ROLE_NONE — доступ без аутентификации. Всегда True."""
        return True

    def _check_any_role(self, user_roles: list[str]) -> bool:
        """Проверка для ROLE_ANY — требуется хотя бы одна роль."""
        if not user_roles:
            raise AuthorizationError(
                "Authentication required: user must have at least one role"
            )
        return True

    def _check_list_role(self, spec: list[str], user_roles: list[str]) -> bool:
        """Проверка для списка ролей — у пользователя должна быть хотя бы одна."""
        if any(role in user_roles for role in spec):
            return True
        raise AuthorizationError(
            f"Access denied. Required one of the roles: {spec}, "
            f"user roles: {user_roles}"
        )

    def _check_single_role(self, spec: str, user_roles: list[str]) -> bool:
        """Проверка для одной конкретной роли."""
        if spec in user_roles:
            return True
        raise AuthorizationError(
            f"Access denied. Required role: '{spec}', user roles: {user_roles}"
        )

    def _check_action_roles(
        self,
        action: BaseAction[P, R],
        context: Context,
        runtime: _ActionExecutionCache | None = None,
    ) -> None:
        """Checks ролевые ограничения действия (кэш scratch / runtime)."""
        role_spec = (
            runtime.role_spec
            if runtime is not None
            else self._get_execution_cache(action.__class__).role_spec
        )
        if role_spec is None:
            raise TypeError(
                f"Action {action.__class__.__name__} does not have a @check_roles "
                f"decorator. Specify @check_roles(ROLE_NONE) explicitly if "
                f"the action is accessible without authentication."
            )
        user_roles = context.user.roles

        if role_spec == ROLE_NONE:
            self._check_none_role(user_roles)
        elif role_spec == ROLE_ANY:
            self._check_any_role(user_roles)
        elif isinstance(role_spec, list):
            self._check_list_role(role_spec, user_roles)
        else:
            self._check_single_role(role_spec, user_roles)

    # ─────────────────────────────────────────────────────────────────────
    # Проверка соединений
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_no_declarations_but_got_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str],
    ) -> str | None:
        """Ошибка: нет @connection, но переданы соединения."""
        if not declared_keys and actual_keys:
            return (
                f"Action {action_name} does not declare any @connection, "
                f"but received connections with keys: {actual_keys}. "
                f"Remove the connections or add @connection decorators."
            )
        return None

    @staticmethod
    def _validate_has_declarations_but_no_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str],
    ) -> str | None:
        """Ошибка: есть @connection, но соединения не переданы."""
        if declared_keys and not actual_keys:
            return (
                f"Action {action_name} declares connections: {declared_keys}, "
                f"but no connections were passed (None or empty dict). "
                f"Pass connections with keys: {declared_keys}."
            )
        return None

    @staticmethod
    def _validate_extra_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str],
    ) -> str | None:
        """Ошибка: переданы лишние ключи соединений."""
        extra = actual_keys - declared_keys
        if extra:
            return (
                f"Action {action_name} received extra connections: {extra}. "
                f"Only declared: {declared_keys}. Remove the extra keys."
            )
        return None

    @staticmethod
    def _validate_missing_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str],
    ) -> str | None:
        """Ошибка: не хватает обязательных ключей соединений."""
        missing = declared_keys - actual_keys
        if missing:
            return (
                f"Action {action_name} is missing required connections: {missing}. "
                f"Declared: {declared_keys}, received: {actual_keys}."
            )
        return None

    @staticmethod
    def _validate_connection_value_types(
        action_name: str, connections: dict[str, Any],
    ) -> str | None:
        """Checks, что каждое значение — экземпляр BaseResourceManager."""
        for key, value in connections.items():
            if not isinstance(value, BaseResourceManager):
                return (
                    f"Connection '{key}' for action {action_name} must be an instance "
                    f"of BaseResourceManager, got {type(value).__name__}: {value!r}."
                )
        return None

    def _check_connections(
        self,
        action: BaseAction[P, R],
        connections: dict[str, BaseResourceManager] | None,
        runtime: _ActionExecutionCache | None = None,
    ) -> dict[str, BaseResourceManager]:
        """Checks соответствие переданных connections объявленным через @connection."""
        keys = (
            runtime.connection_keys
            if runtime is not None
            else self._get_execution_cache(action.__class__).connection_keys
        )
        declared_keys: set[str] = set(keys)
        actual_keys: set[str] = set(connections.keys()) if connections else set()
        action_name: str = action.__class__.__name__

        key_validators = [
            self._validate_no_declarations_but_got_connections,
            self._validate_has_declarations_but_no_connections,
            self._validate_extra_connection_keys,
            self._validate_missing_connection_keys,
        ]

        for validator in key_validators:
            error = validator(action_name, declared_keys, actual_keys)
            if error:
                raise ConnectionValidationError(error)

        if connections:
            type_error = self._validate_connection_value_types(action_name, connections)
            if type_error:
                raise ConnectionValidationError(type_error)

        return connections or {}

    # ─────────────────────────────────────────────────────────────────────
    # Вызов аспекта
    # ─────────────────────────────────────────────────────────────────────

    async def _call_aspect(
        self,
        aspect_meta: AspectGateHostInspector.Snapshot.Aspect | None,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
    ) -> Any:
        """
        Вызывает method-аспект, описанный snapshot-метаданными.

        Если aspect_meta.context_keys непустой — создаёт ContextView
        с разрешёнными ключами и передаёт как последний аргумент (ctx).
        Если пустой — вызывает с 5 аргументами (без ctx).

        Args:
            aspect_meta: метаданные аспекта (или None для пустого result).
            action: экземпляр действия.
            params: входные параметры.
            state: текущее state конвейера.
            box: ToolsBox текущего уровня.
            connections: словарь ресурсных менеджеров.
            context: context выполнения (для ScopedLogger и ContextView).

        Returns:
            Результат вызова аспекта (dict для regular, BaseResult для summary).
        """
        if aspect_meta is None:
            return BaseResult()

        aspect_log = ScopedLogger(
            coordinator=self._log_coordinator,
            nest_level=box.nested_level,
            machine_name=self.__class__.__name__,
            mode=self._mode,
            action_name=action.get_full_class_name(),
            aspect_name=aspect_meta.method_name,
            context=context,
            state=state,
            params=params,
        )

        aspect_box = ToolsBox(
            run_child=box.run_child,
            factory=box.factory,
            resources=box.resources,
            context=context,
            log=aspect_log,
            nested_level=box.nested_level,
            rollup=box.rollup,
        )

        # ── Вызов с ContextView или без ───────────────────────────────
        if aspect_meta.context_keys:
            ctx_view = ContextView(context, aspect_meta.context_keys)
            return await aspect_meta.method_ref(
                action, params, state, aspect_box, connections, ctx_view,
            )

        return await aspect_meta.method_ref(
            action, params, state, aspect_box, connections,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Общие поля для создания событий
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _base_event_fields(
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
    ) -> dict[str, Any]:
        """
        Returns словарь общих полей BasePluginEvent.

        Используется всеми methodами _emit_* для формирования базовых
        аргументов конструктора события. Избавляет от дублирования
        четырёх одинаковых полей в каждой точке эмиссии.
        """
        return {
            "action_class": type(action),
            "action_name": action.get_full_class_name(),
            "nest_level": nest_level,
            "context": context,
            "params": params,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Формирование kwargs для emit_event
    # ─────────────────────────────────────────────────────────────────────

    def _build_plugin_emit_kwargs(self, nest_level: int) -> dict[str, Any]:
        """
        Формирует дополнительные kwargs для передачи в
        plugin_ctx.emit_event().
        """
        return {
            "log_coordinator": self._log_coordinator,
            "machine_name": self.__class__.__name__,
            "mode": self._mode,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Размотка стека компенсации (Saga)
    # ─────────────────────────────────────────────────────────────────────

    async def _rollback_saga(
        self,
        saga_stack: list[SagaFrame],
        error: Exception,
        action: BaseAction[Any, Any],
        params: BaseParams,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        plugin_ctx: PluginRunContext,
    ) -> None:
        """
        Размотка стека компенсации в обратном порядке.

        Метод НИКОГДА не бросает исключение. Ошибки compensatorов
        подавляются и эмитируются как CompensateFailedEvent. Это
        гарантирует, что:

        1. Все compensatorы в стеке получат шанс выполниться.
        2. После размотки управление вернётся к @on_error.
        3. @on_error получит ОРИГИНАЛЬНУЮ ошибку аспекта, а не ошибку
           compensatorа.

        Ошибки compensatorов молчаливые, потому что:
        - Если error compensatorа пробрасывается, следующие
          compensatorы в стеке НИКОГДА не вызовутся — система
          окажется в неконсистентном состоянии.
        - @on_error спроектирован для бизнес-ошибок аспектов, а не
          для ошибок инфраструктуры отката. Смешивание нарушает
          контракт @on_error.

        Вместо проброса используется типизированное событие
        CompensateFailedEvent, на которое плагин мониторинга
        может подписаться.

        Args:
            saga_stack: список фреймов компенсации (в порядке добавления).
            error: исключение, вызвавшее размотку.
            action: экземпляр действия.
            params: входные параметры (frozen).
            box: ToolsBox текущего уровня.
            connections: словарь ресурсных менеджеров.
            context: context выполнения.
            plugin_ctx: context плагинов для эмиссии событий.
        """
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

        # ── Подсчёт compensatorов в стеке ────────────────────────────
        compensator_count = sum(1 for f in saga_stack if f.compensator is not None)
        aspect_names_reversed = tuple(f.aspect_name for f in reversed(saga_stack))

        # ── SagaRollbackStartedEvent ─────────────────────────────────
        await plugin_ctx.emit_event(
            SagaRollbackStartedEvent(
                **base_fields,
                error=error,
                stack_depth=len(saga_stack),
                compensator_count=compensator_count,
                aspect_names=aspect_names_reversed,
            ),
            **plugin_kwargs,
        )

        # ── Счётчики итогов ──────────────────────────────────────────
        succeeded = 0
        failed = 0
        skipped = 0
        failed_aspects: list[str] = []
        rollback_start = time.time()

        # ── Обход стека в обратном порядке ────────────────────────────
        for frame in reversed(saga_stack):
            if frame.compensator is None:
                skipped += 1
                continue

            comp_meta: CompensateGateHostInspector.Snapshot.Compensator = frame.compensator

            # ── BeforeCompensateAspectEvent ───────────────────────────
            await plugin_ctx.emit_event(
                BeforeCompensateAspectEvent(
                    **base_fields,
                    aspect_name=frame.aspect_name,
                    state_snapshot=None,
                    error=error,
                    compensator_name=comp_meta.method_name,
                    compensator_state_before=frame.state_before,
                    compensator_state_after=frame.state_after,
                ),
                **plugin_kwargs,
            )

            comp_start = time.time()

            try:
                # ── Создать ScopedLogger для compensatorа ─────────────
                comp_log = ScopedLogger(
                    coordinator=self._log_coordinator,
                    nest_level=box.nested_level,
                    machine_name=self.__class__.__name__,
                    mode=self._mode,
                    action_name=action.get_full_class_name(),
                    aspect_name=comp_meta.method_name,
                    context=context,
                    state=frame.state_before if isinstance(frame.state_before, BaseState) else BaseState(),
                    params=params,
                )

                comp_box = ToolsBox(
                    run_child=box.run_child,
                    factory=box.factory,
                    resources=box.resources,
                    context=context,
                    log=comp_log,
                    nested_level=box.nested_level,
                    rollup=box.rollup,
                )

                # ── Вызов compensatorа с ContextView или без ──────────
                if comp_meta.context_keys:
                    ctx_view = ContextView(context, comp_meta.context_keys)
                    await comp_meta.method_ref(
                        action, params, frame.state_before, frame.state_after,
                        comp_box, connections, error, ctx_view,
                    )
                else:
                    await comp_meta.method_ref(
                        action, params, frame.state_before, frame.state_after,
                        comp_box, connections, error,
                    )

                comp_duration = time.time() - comp_start

                # ── AfterCompensateAspectEvent ────────────────────────
                await plugin_ctx.emit_event(
                    AfterCompensateAspectEvent(
                        **base_fields,
                        aspect_name=frame.aspect_name,
                        state_snapshot=None,
                        error=error,
                        compensator_name=comp_meta.method_name,
                        duration_ms=comp_duration * 1000,
                    ),
                    **plugin_kwargs,
                )
                succeeded += 1

            except Exception as comp_error:
                # ── CompensateFailedEvent ─────────────────────────────
                # Ошибка compensatorа полностью подавляется.
                # Размотка ПРОДОЛЖАЕТСЯ.
                await plugin_ctx.emit_event(
                    CompensateFailedEvent(
                        **base_fields,
                        aspect_name=frame.aspect_name,
                        state_snapshot=None,
                        original_error=error,
                        compensator_error=comp_error,
                        compensator_name=comp_meta.method_name,
                        failed_for_aspect=frame.aspect_name,
                    ),
                    **plugin_kwargs,
                )
                failed += 1
                failed_aspects.append(frame.aspect_name)

        rollback_duration = time.time() - rollback_start

        # ── SagaRollbackCompletedEvent ────────────────────────────────
        await plugin_ctx.emit_event(
            SagaRollbackCompletedEvent(
                **base_fields,
                error=error,
                total_frames=len(saga_stack),
                succeeded=succeeded,
                failed=failed,
                skipped=skipped,
                duration_ms=rollback_duration * 1000,
                failed_aspects=tuple(failed_aspects),
            ),
            **plugin_kwargs,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Обработка ошибок аспектов (@on_error)
    # ─────────────────────────────────────────────────────────────────────

    async def _handle_aspect_error(
        self,
        error: Exception,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        runtime: _ActionExecutionCache,
        context: Context,
        plugin_ctx: PluginRunContext,
        failed_aspect_name: str | None,
    ) -> BaseResult:
        """
        Ищет подходящий обработчик @on_error и вызывает его.

        Проходит по обработчикам из графа в порядке объявления (сверху вниз).
        Первый обработчик, чей exception_types совпадает с типом исключения
        через isinstance, вызывается.

        Если обработчик найден:
        1. Эмитирует BeforeOnErrorAspectEvent плагинам.
        2. Вызывает обработчик (с ContextView если context_keys).
        3. Эмитирует AfterOnErrorAspectEvent плагинам.
        4. Returns Result от обработчика.

        Если обработчик не найден:
        1. Эмитирует UnhandledErrorEvent плагинам.
        2. Пробрасывает исходное исключение.

        Вызывается ПОСЛЕ _rollback_saga() — к моменту вызова все
        compensatorы уже отработали (или упали). @on_error работает
        с консистентными данными.

        Args:
            error: исключение, возникшее в аспекте.
            action: экземпляр действия.
            params: входные параметры (frozen, read-only).
            state: state конвейера на момент ошибки (read-only).
            box: ToolsBox для доступа к зависимостям и логированию.
            connections: словарь ресурсных менеджеров.
            runtime: снимок исполнения для класса действия.
            context: context выполнения (для создания ContextView).
            plugin_ctx: context плагинов для эмиссии событий.
            failed_aspect_name: имя аспекта, в котором произошла error
                (или None если error вне аспекта).

        Returns:
            BaseResult — результат, возвращённый обработчиком.

        Raises:
            OnErrorHandlerError: если обработчик сам бросил исключение.
            (исходное исключение): если ни один обработчик не подошёл.
        """
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

        handler_meta: OnErrorGateHostInspector.Snapshot.ErrorHandler | None = None
        for candidate in runtime.error_handlers:
            if isinstance(error, candidate.exception_types):
                handler_meta = candidate
                break

        if handler_meta is None:
            # ── Нет подходящего обработчика → UnhandledErrorEvent ──────
            await plugin_ctx.emit_event(
                UnhandledErrorEvent(
                    **base_fields,
                    error=error,
                    failed_aspect_name=failed_aspect_name,
                ),
                **plugin_kwargs,
            )
            raise error

        # ── Обработчик найден → BeforeOnErrorAspectEvent ──────────────
        await plugin_ctx.emit_event(
            BeforeOnErrorAspectEvent(
                **base_fields,
                aspect_name=handler_meta.method_name,
                state_snapshot=state.to_dict(),
                error=error,
                handler_name=handler_meta.method_name,
            ),
            **plugin_kwargs,
        )

        handler_start = time.time()

        try:
            # ── Вызов с ContextView или без ───────────────────────────
            if handler_meta.context_keys:
                ctx_view = ContextView(context, handler_meta.context_keys)
                result = await handler_meta.method_ref(
                    action, params, state, box, connections, error, ctx_view,
                )
            else:
                result = await handler_meta.method_ref(
                    action, params, state, box, connections, error,
                )

            handler_duration = time.time() - handler_start

            # ── AfterOnErrorAspectEvent ────────────────────────────────
            await plugin_ctx.emit_event(
                AfterOnErrorAspectEvent(
                    **base_fields,
                    aspect_name=handler_meta.method_name,
                    state_snapshot=state.to_dict(),
                    error=error,
                    handler_name=handler_meta.method_name,
                    handler_result=cast("BaseResult", result),
                    duration_ms=handler_duration * 1000,
                ),
                **plugin_kwargs,
            )
            return cast("BaseResult", result)

        except Exception as handler_error:
            raise OnErrorHandlerError(
                f"Обработчик ошибок '{handler_meta.method_name}' в "
                f"{action.__class__.__name__} бросил исключение при обработке "
                f"{type(error).__name__}: {handler_error}",
                handler_name=handler_meta.method_name,
                original_error=error,
            ) from handler_error

    # ─────────────────────────────────────────────────────────────────────
    # Выполнение regular-аспектов
    # ─────────────────────────────────────────────────────────────────────

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        runtime: _ActionExecutionCache,
        plugin_ctx: PluginRunContext,
        saga_stack: list[SagaFrame],
    ) -> BaseState:
        """
        Последовательно выполняет regular-аспекты действия.

        Для каждого аспекта:
        1. Эмитирует BeforeRegularAspectEvent.
        2. Вызывает аспект (с ContextView если context_keys).
        3. Валидирует результат checkerами.
        4. Обновляет state.
        5. Добавляет SagaFrame в переданный saga_stack (если build_saga=True).
        6. Эмитирует AfterRegularAspectEvent.

        Raises аспектов НЕ перехватываются здесь — они пробрасываются
        наверх в _execute_aspects_with_error_handling().

        Заполняет переданный saga_stack фреймами SagaFrame для каждого
        успешного аспекта (если build_saga=True). При исключении на N-м
        аспекте saga_stack содержит фреймы первых (N-1) успешных аспектов,
        доступные вызывающему коду в блоке except — потому что saga_stack
        передаётся как мутабельный список, а не возвращается через return.

        При rollup=True стек НЕ заполняется — компенсация предназначена
        для нетранзакционных побочных эффектов в production-режиме.
        В rollup-режиме транзакционный откат выполняется на уровне
        connections через WrapperConnectionManager.

        Когда фрейм добавляется:
            - Аспект вернул dict, checkerы пройдены → state_after = новый state.
            - Аспект вернул dict, checker отклонил → state_after = None.
              Побочный эффект МОГ произойти (HTTP-запрос уже отправлен).

        Когда фрейм НЕ добавляется:
            - Аспект бросил исключение до возврата dict.

        Args:
            action: экземпляр действия.
            params: входные параметры (frozen).
            box: ToolsBox текущего уровня.
            connections: словарь ресурсных менеджеров.
            context: context выполнения.
            runtime: снимок исполнения для класса действия.
            plugin_ctx: context плагинов для эмиссии событий.
            saga_stack: мутабельный список, заполняемый фреймами компенсации.
                Создаётся в _execute_aspects_with_error_handling() и передаётся
                сюда для заполнения. При исключении список доступен в except-блоке
                вызывающего methodа — это решает проблему потери стека при ошибке.

        Returns:
            BaseState — итоговое state после всех regular-аспектов.
        """
        state = BaseState()
        regular_aspects = runtime.regular_aspects
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

        # Стек компенсации — локальный для этого конвейера.
        # Не создаётся при rollup=True.
        build_saga = runtime.has_compensators

        for aspect_meta in regular_aspects:
            # ── BeforeRegularAspectEvent ──────────────────────────────
            await plugin_ctx.emit_event(
                BeforeRegularAspectEvent(
                    **base_fields,
                    aspect_name=aspect_meta.method_name,
                    state_snapshot=state.to_dict(),
                ),
                **plugin_kwargs,
            )

            # Запомнить state ДО аспекта для SagaFrame
            state_before = state

            aspect_start = time.time()

            new_state_dict = await self._call_aspect(
                aspect_meta, action, params, state, box, connections, context,
            )

            if not isinstance(new_state_dict, dict):
                raise TypeError(
                    f"Aspect {aspect_meta.method_name} must return a dict, "
                    f"got {type(new_state_dict).__name__}"
                )

            checkers = runtime.checkers_by_aspect.get(
                aspect_meta.method_name, (),
            )

            if not checkers and new_state_dict:
                raise ValidationFieldError(
                    f"Aspect {aspect_meta.method_name} has no checkers, "
                    f"but returned non-empty state: {new_state_dict}. "
                    f"Either add checkers for all fields, or return an empty dict."
                )

            if checkers:
                allowed_fields = {c.field_name for c in checkers}
                extra_fields = set(new_state_dict.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldError(
                        f"Aspect {aspect_meta.method_name} returned extra fields: "
                        f"{extra_fields}. Allowed only: {allowed_fields}"
                    )
                self._apply_checkers(checkers, new_state_dict)

            # Создаём новый state, объединяя старый с новыми данными
            state = BaseState(**{**state.to_dict(), **new_state_dict})

            # ── Добавить SagaFrame в стек компенсации ─────────────────
            if build_saga:
                compensator = runtime.compensators_by_aspect.get(
                    aspect_meta.method_name,
                )
                saga_stack.append(SagaFrame(
                    compensator=compensator,
                    aspect_name=aspect_meta.method_name,
                    state_before=state_before,
                    state_after=state,
                ))

            aspect_duration = time.time() - aspect_start

            # ── AfterRegularAspectEvent ───────────────────────────────
            await plugin_ctx.emit_event(
                AfterRegularAspectEvent(
                    **base_fields,
                    aspect_name=aspect_meta.method_name,
                    state_snapshot=state.to_dict(),
                    aspect_result=new_state_dict,
                    duration_ms=aspect_duration * 1000,
                ),
                **plugin_kwargs,
            )

        return state

    # ─────────────────────────────────────────────────────────────────────
    # Выполнение конвейера с обработкой ошибок
    # ─────────────────────────────────────────────────────────────────────

    async def _execute_aspects_with_error_handling(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        runtime: _ActionExecutionCache,
        plugin_ctx: PluginRunContext,
    ) -> R:
        """
        Выполняет полный конвейер аспектов с перехватом ошибок через @on_error.

        Выполняет regular-аспекты, затем summary-аспект. Эмитирует
        BeforeSummaryAspectEvent и AfterSummaryAspectEvent вокруг summary.

        При исключении:
        1. Размотка стека компенсации (_rollback_saga) — если rollup=False
           и стек непуст.
        2. Делегирование обработки в _handle_aspect_error(), который
           эмитирует BeforeOnErrorAspectEvent / AfterOnErrorAspectEvent
           или UnhandledErrorEvent.

        saga_stack объявляется ДО try-блока, чтобы быть доступным в except.
        Если _execute_regular_aspects бросит исключение на N-м аспекте,
        saga_stack будет содержать фреймы первых (N-1) успешных аспектов.
        """
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

        saga_stack: list[SagaFrame] = []
        failed_aspect_name: str | None = None

        try:
            state = await self._execute_regular_aspects(
                action, params, box, connections, context, runtime, plugin_ctx,
                saga_stack,
            )

            summary_meta = runtime.summary_aspect
            summary_name = summary_meta.method_name if summary_meta else "summary"

            # ── BeforeSummaryAspectEvent ──────────────────────────────
            await plugin_ctx.emit_event(
                BeforeSummaryAspectEvent(
                    **base_fields,
                    aspect_name=summary_name,
                    state_snapshot=state.to_dict(),
                ),
                **plugin_kwargs,
            )

            failed_aspect_name = summary_name
            summary_start = time.time()

            result = await self._call_aspect(
                summary_meta, action, params, state, box, connections, context,
            )

            summary_duration = time.time() - summary_start

            # ── AfterSummaryAspectEvent ───────────────────────────────
            await plugin_ctx.emit_event(
                AfterSummaryAspectEvent(
                    **base_fields,
                    aspect_name=summary_name,
                    state_snapshot=state.to_dict(),
                    result=cast("BaseResult", result),
                    duration_ms=summary_duration * 1000,
                ),
                **plugin_kwargs,
            )

            return cast("R", result)

        except Exception as aspect_error:
            # ── Размотка стека компенсации (Saga) ─────────────────────
            # Выполняется ДО @on_error: сначала откат побочных эффектов,
            # потом обработка бизнес-логики. Иначе @on_error работает
            # с неконсистентными данными.
            if saga_stack:
                await self._rollback_saga(
                    saga_stack=saga_stack,
                    error=aspect_error,
                    action=action,
                    params=params,
                    box=box,
                    connections=connections,
                    context=context,
                    plugin_ctx=plugin_ctx,
                )

            # ── Делегируем обработку ошибки ────────────────────────────
            error_state = BaseState()
            handled_result = await self._handle_aspect_error(
                error=aspect_error,
                action=action,
                params=params,
                state=error_state,
                box=box,
                connections=connections,
                runtime=runtime,
                context=context,
                plugin_ctx=plugin_ctx,
                failed_aspect_name=failed_aspect_name,
            )
            return cast("R", handled_result)

    # ─────────────────────────────────────────────────────────────────────
    # Публичный API: run (асинхронный)
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Асинхронно выполняет действие с поддержкой плагинов и вложенности.

        Production-машина всегда передаёт rollup=False в _run_internal().
        Каждый вызов полностью изолирован от предыдущих.
        """
        # pylint: disable=invalid-overridden-method
        return await self._run_internal(
            context=context,
            action=action,
            params=params,
            resources=None,
            connections=connections,
            nested_level=0,
            rollup=False,
        )

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type, Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
        rollup: bool,
    ) -> R:
        """
        Внутренний method выполнения с поддержкой вложенности и rollup.

        Вызывается из run() (nested_level=0, rollup=False) и из ToolsBox.run()
        (nested_level > 0). Rollup прокидывается в ToolsBox и через замыкание
        run_child в дочерние вызовы _run_internal().

        Каждый _run_internal создаёт СВОЙ локальный стек компенсации.
        Глобального стека нет. При вложенных вызовах (box.run(ChildAction))
        дочерний Action имеет собственный стек, который разматывается
        независимо от родительского. Это гарантирует корректное поведение
        при перехвате исключений дочернего Action через try/except
        в аспекте родителя.

        Создаёт типизированные события GlobalStartEvent и GlobalFinishEvent
        и передаёт их в plugin_ctx.emit_event() вместо строковых имён.
        """
        current_nest = nested_level + 1
        start_time = time.time()
        plugin_kwargs = self._build_plugin_emit_kwargs(current_nest)

        try:
            action_cls = action.__class__
            runtime = self._get_execution_cache(action_cls)
            self._role_checker.check(action, context, runtime)
            conns = self._connection_validator.validate(action, connections, runtime)
            plugin_ctx = await self._plugin_coordinator.create_run_context()

            async def run_child(
                action: BaseAction[Any, Any],
                params: BaseParams,
                connections: dict[str, BaseResourceManager] | None = None,
            ) -> BaseResult:
                return await self._run_internal(
                    context=context,
                    action=action,
                    params=params,
                    resources=resources,
                    connections=connections,
                    nested_level=current_nest,
                    rollup=rollup,
                )

            box = self._tools_box_factory.create(
                self,
                nest_level=current_nest,
                context=context,
                action_cls=action.__class__,
                params=params,
                resources=resources,
                rollup=rollup,
                run_child=run_child,
            )

            base_fields = self._base_event_fields(action, context, params, current_nest)

            # ── GlobalStartEvent ──────────────────────────────────────
            await plugin_ctx.emit_event(
                GlobalStartEvent(**base_fields),
                **plugin_kwargs,
            )

            result = await self._execute_aspects_with_error_handling(
                action, params, box, conns, context, runtime, plugin_ctx,
            )

            total_duration = time.time() - start_time

            # ── GlobalFinishEvent ─────────────────────────────────────
            await plugin_ctx.emit_event(
                GlobalFinishEvent(
                    **base_fields,
                    result=cast("BaseResult", result),
                    duration_ms=total_duration * 1000,
                ),
                **plugin_kwargs,
            )

            return result
        finally:
            pass
