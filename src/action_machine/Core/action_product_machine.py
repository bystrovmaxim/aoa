# src/action_machine/core/action_product_machine.py
"""
ActionProductMachine — асинхронная production-реализация машины действий.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
ActionProductMachine — центральный асинхронный исполнитель действий (Action)
в системе. Получает экземпляр действия, входные параметры и контекст,
после чего:
1. Проверяет ролевые ограничения (@check_roles) через ClassMetadata.
2. Валидирует соединения (@connection) через ClassMetadata.
3. Получает stateless-фабрику зависимостей через координатор.
4. Создаёт изолированный PluginRunContext для текущего запроса.
5. Последовательно выполняет regular-аспекты, проверяя результаты чекерами.
   Для аспектов с @context_requires создаёт ContextView и передаёт как ctx.
6. Выполняет summary-аспект, формирующий итоговый Result.
7. При исключении в аспекте — эмитирует типизированные события плагинам
   (BeforeOnErrorAspectEvent / AfterOnErrorAspectEvent или
   UnhandledErrorEvent), затем ищет подходящий обработчик @on_error.
   Для обработчиков с @context_requires создаёт отдельный ContextView.
8. Уведомляет плагины о событиях через PluginRunContext.emit_event(),
   передавая объекты событий из иерархии BasePluginEvent.
═══════════════════════════════════════════════════════════════════════════════
ТИПИЗИРОВАННЫЕ СОБЫТИЯ ПЛАГИНОВ
═══════════════════════════════════════════════════════════════════════════════
Машина создаёт конкретные объекты событий из иерархии BasePluginEvent
в ключевых точках конвейера и передаёт их в plugin_ctx.emit_event():

    GlobalStartEvent          — перед первым аспектом
    BeforeRegularAspectEvent  — перед каждым regular-аспектом
    AfterRegularAspectEvent   — после каждого regular-аспекта
    BeforeSummaryAspectEvent  — перед summary-аспектом
    AfterSummaryAspectEvent   — после summary-аспекта
    BeforeOnErrorAspectEvent  — перед вызовом @on_error обработчика
    AfterOnErrorAspectEvent   — после успешного @on_error обработчика
    UnhandledErrorEvent       — ошибка без подходящего @on_error
    GlobalFinishEvent         — после успешного завершения конвейера

Каждый класс события содержит РОВНО те поля, которые имеют смысл для
данного типа. Обработчики плагинов подписываются через @on(EventClass)
и получают типизированный объект без Optional-полей.
═══════════════════════════════════════════════════════════════════════════════
УПРАВЛЯЕМЫЙ ДОСТУП К КОНТЕКСТУ
═══════════════════════════════════════════════════════════════════════════════
Аспекты и обработчики ошибок НЕ имеют прямого доступа к контексту.
Публичное свойство context удалено из ToolsBox. Единственный путь
к данным контекста — через ContextView, который машина создаёт для
методов с @context_requires.

При вызове аспекта машина проверяет aspect_meta.context_keys:
    - Если непустой → создаёт ContextView(context, context_keys),
      передаёт как 6-й аргумент (ctx).
    - Если пустой → вызывает с 5 аргументами (без ctx).

Аналогично для обработчиков ошибок:
    - Если context_keys непустой → ContextView как 7-й аргумент.
    - Если пустой → 6 аргументов (без ctx).
═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК АСПЕКТОВ (@on_error)
═══════════════════════════════════════════════════════════════════════════════
Когда regular- или summary-аспект бросает исключение, машина:
1. Останавливает выполнение конвейера аспектов.
2. Проверяет наличие подходящего @on_error обработчика.
3. Если обработчик найден:
   a. Эмитирует BeforeOnErrorAspectEvent плагинам.
   b. Вызывает обработчик (с ContextView если context_keys).
   c. Эмитирует AfterOnErrorAspectEvent плагинам.
   d. Возвращает Result от обработчика.
4. Если обработчик не найден:
   a. Эмитирует UnhandledErrorEvent плагинам.
   b. Пробрасывает исходное исключение наружу.
5. Если обработчик сам бросает исключение — OnErrorHandlerError.
═══════════════════════════════════════════════════════════════════════════════
ПУБЛИЧНЫЙ API
═══════════════════════════════════════════════════════════════════════════════
    await machine.run(context, action, params, connections)

Метод run() — асинхронный. Для синхронного использования существует
отдельный класс SyncActionProductMachine.
Production-машины всегда передают rollup=False в _run_internal().
═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ВЫПОЛНЕНИЯ
═══════════════════════════════════════════════════════════════════════════════
    machine.run(context, action, params, connections)
        │
        ├── 1. _check_action_roles(action, context, metadata)
        ├── 2. _check_connections(action, connections, metadata)
        ├── 3. coordinator.get_factory(action.__class__)
        ├── 4. plugin_ctx = plugin_coordinator.create_run_context()
        ├── 5. plugin_ctx.emit_event(GlobalStartEvent(...))
        ├── 6. _execute_aspects_with_error_handling(...)
        │       ├── _execute_regular_aspects(...)
        │       │       └── для каждого AspectMeta с type=="regular":
        │       │           ├── emit_event(BeforeRegularAspectEvent(...))
        │       │           ├── _call_aspect (с ContextView если context_keys)
        │       │           ├── _apply_checkers(...)
        │       │           └── emit_event(AfterRegularAspectEvent(...))
        │       ├── emit_event(BeforeSummaryAspectEvent(...))
        │       ├── _call_aspect(summary, ...)
        │       ├── emit_event(AfterSummaryAspectEvent(...))
        │       └── при исключении:
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
import time
from typing import Any, TypeVar, cast

from action_machine.auth.constants import ROLE_ANY, ROLE_NONE
from action_machine.context.context import Context
from action_machine.context.context_view import ContextView
from action_machine.core.base_action import BaseAction
from action_machine.core.base_action_machine import BaseActionMachine
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.class_metadata import AspectMeta, CheckerMeta, ClassMetadata, OnErrorMeta
from action_machine.core.exceptions import (
    AuthorizationError,
    ConnectionValidationError,
    OnErrorHandlerError,
    ValidationFieldError,
)
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.events import (
    AfterOnErrorAspectEvent,
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BeforeOnErrorAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
    UnhandledErrorEvent,
)
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionProductMachine(BaseActionMachine):
    """
    Асинхронная production-реализация машины действий.

    Выполняет действие по конвейеру аспектов, проверяет роли и соединения,
    применяет чекеры к результатам аспектов, создаёт ContextView для
    аспектов с @context_requires, эмитирует типизированные события
    плагинам при ошибке аспекта, обрабатывает ошибки через @on_error
    и уведомляет плагины о событиях жизненного цикла.

    Все метаданные получаются через GateCoordinator → ClassMetadata.
    Машина НЕ обращается к внутренним атрибутам классов.
    Машина не хранит никакого мутабельного состояния между вызовами run().

    Атрибуты:
        _mode : str
            Режим выполнения ("production", "test", "staging" и т.д.).
        _coordinator : GateCoordinator
            Координатор метаданных и фабрик.
        _plugin_coordinator : PluginCoordinator
            Stateless-координатор плагинов.
        _log_coordinator : LogCoordinator
            Координатор логирования.
    """

    def __init__(
        self,
        mode: str,
        coordinator: GateCoordinator | None = None,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Инициализирует машину действий.

        Аргументы:
            mode: режим выполнения (обязательный, не пустой).
            coordinator: координатор метаданных и фабрик. Если не указан,
                         создаётся новый GateCoordinator() (strict=False).
            plugins: список экземпляров плагинов (по умолчанию пустой).
            log_coordinator: координатор логирования. Если не указан, создаётся
                             координатор с одним ConsoleLogger(use_colors=True).

        Исключения:
            ValueError: если mode — пустая строка.
        """
        if not mode:
            raise ValueError("mode must be non-empty")

        self._mode: str = mode
        self._coordinator: GateCoordinator = coordinator or GateCoordinator()
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
        )
        if log_coordinator is None:
            log_coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
        self._log_coordinator: LogCoordinator = log_coordinator

    # ─────────────────────────────────────────────────────────────────────
    # Получение метаданных
    # ─────────────────────────────────────────────────────────────────────

    def _get_metadata(self, action: BaseAction[Any, Any]) -> ClassMetadata:
        """Возвращает ClassMetadata для действия через координатор."""
        return self._coordinator.get(action.__class__)

    # ─────────────────────────────────────────────────────────────────────
    # Проверка чекеров
    # ─────────────────────────────────────────────────────────────────────

    def _get_checkers_for_aspect(
        self,
        metadata: ClassMetadata,
        aspect_meta: AspectMeta,
    ) -> tuple[CheckerMeta, ...]:
        """Возвращает чекеры, привязанные к конкретному аспекту."""
        return metadata.get_checkers_for_aspect(aspect_meta.method_name)

    def _apply_checkers(
        self,
        checkers: tuple[CheckerMeta, ...],
        result: dict[str, Any],
    ) -> None:
        """Применяет все чекеры к словарю результата аспекта."""
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
        metadata: ClassMetadata,
    ) -> None:
        """Проверяет ролевые ограничения действия через ClassMetadata."""
        if not metadata.has_role() or metadata.role is None:
            raise TypeError(
                f"Action {action.__class__.__name__} does not have a @check_roles "
                f"decorator. Specify @check_roles(ROLE_NONE) explicitly if "
                f"the action is accessible without authentication."
            )
        role_spec = metadata.role.spec
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
        """Проверяет, что каждое значение — экземпляр BaseResourceManager."""
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
        metadata: ClassMetadata,
    ) -> dict[str, BaseResourceManager]:
        """Проверяет соответствие переданных connections объявленным через @connection."""
        declared_keys: set[str] = set(metadata.get_connection_keys())
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
    # Извлечение аспектов из метаданных
    # ─────────────────────────────────────────────────────────────────────

    def _get_regular_aspects(
        self, metadata: ClassMetadata,
    ) -> tuple[AspectMeta, ...]:
        """Извлекает regular-аспекты из ClassMetadata."""
        return metadata.get_regular_aspects()

    def _get_summary_aspect(
        self, metadata: ClassMetadata,
    ) -> AspectMeta | None:
        """Извлекает summary-аспект из ClassMetadata."""
        return metadata.get_summary_aspect()

    # ─────────────────────────────────────────────────────────────────────
    # Вызов аспекта
    # ─────────────────────────────────────────────────────────────────────

    async def _call_aspect(
        self,
        aspect_meta: AspectMeta | None,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
    ) -> Any:
        """
        Вызывает метод-аспект, обёрнутый в AspectMeta.

        Если aspect_meta.context_keys непустой — создаёт ContextView
        с разрешёнными ключами и передаёт как последний аргумент (ctx).
        Если пустой — вызывает с 5 аргументами (без ctx).

        Аргументы:
            aspect_meta: метаданные аспекта (или None для пустого результата).
            action: экземпляр действия.
            params: входные параметры.
            state: текущее состояние конвейера.
            box: ToolsBox текущего уровня.
            connections: словарь ресурсных менеджеров.
            context: контекст выполнения (для ScopedLogger и ContextView).

        Возвращает:
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
        Возвращает словарь общих полей BasePluginEvent.

        Используется всеми методами _emit_* для формирования базовых
        аргументов конструктора события. Избавляет от дублирования
        четырёх одинаковых полей в каждой точке эмиссии.

        Аргументы:
            action: экземпляр действия.
            context: контекст выполнения.
            params: входные параметры действия.
            nest_level: уровень вложенности.

        Возвращает:
            dict с ключами action_class, action_name, nest_level,
            context, params.
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

        Эти kwargs передаются в PluginRunContext для создания
        ScopedLogger и проверки фильтра domain.
        """
        return {
            "log_coordinator": self._log_coordinator,
            "machine_name": self.__class__.__name__,
            "mode": self._mode,
            "coordinator": self._coordinator,
        }

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
        metadata: ClassMetadata,
        context: Context,
        plugin_ctx: PluginRunContext,
        failed_aspect_name: str | None,
    ) -> BaseResult:
        """
        Ищет подходящий обработчик @on_error и вызывает его.

        Проходит по metadata.error_handlers в порядке объявления (сверху вниз).
        Первый обработчик, чей exception_types совпадает с типом исключения
        через isinstance, вызывается.

        Если обработчик найден:
        1. Эмитирует BeforeOnErrorAspectEvent плагинам.
        2. Вызывает обработчик (с ContextView если context_keys).
        3. Эмитирует AfterOnErrorAspectEvent плагинам.
        4. Возвращает Result от обработчика.

        Если обработчик не найден:
        1. Эмитирует UnhandledErrorEvent плагинам.
        2. Пробрасывает исходное исключение.

        Аргументы:
            error: исключение, возникшее в аспекте.
            action: экземпляр действия.
            params: входные параметры (frozen, read-only).
            state: состояние конвейера на момент ошибки (read-only).
            box: ToolsBox для доступа к зависимостям и логированию.
            connections: словарь ресурсных менеджеров.
            metadata: метаданные класса действия.
            context: контекст выполнения (для создания ContextView).
            plugin_ctx: контекст плагинов для эмиссии событий.
            failed_aspect_name: имя аспекта, в котором произошла ошибка
                (или None если ошибка вне аспекта).

        Возвращает:
            BaseResult — результат, возвращённый обработчиком.

        Исключения:
            OnErrorHandlerError: если обработчик сам бросил исключение.
            (исходное исключение): если ни один обработчик не подошёл.
        """
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

        handler_meta: OnErrorMeta | None = metadata.get_error_handler_for(error)

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
        metadata: ClassMetadata,
        plugin_ctx: PluginRunContext,
    ) -> BaseState:
        """
        Последовательно выполняет regular-аспекты действия.

        Для каждого аспекта:
        1. Эмитирует BeforeRegularAspectEvent.
        2. Вызывает аспект (с ContextView если context_keys).
        3. Валидирует результат чекерами.
        4. Обновляет state.
        5. Эмитирует AfterRegularAspectEvent.

        Исключения аспектов НЕ перехватываются здесь — они пробрасываются
        наверх в _execute_aspects_with_error_handling().
        """
        state = BaseState()
        regular_aspects = self._get_regular_aspects(metadata)
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

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

            aspect_start = time.time()

            new_state_dict = await self._call_aspect(
                aspect_meta, action, params, state, box, connections, context,
            )

            if not isinstance(new_state_dict, dict):
                raise TypeError(
                    f"Aspect {aspect_meta.method_name} must return a dict, "
                    f"got {type(new_state_dict).__name__}"
                )

            checkers = self._get_checkers_for_aspect(metadata, aspect_meta)

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
        metadata: ClassMetadata,
        plugin_ctx: PluginRunContext,
    ) -> R:
        """
        Выполняет полный конвейер аспектов с перехватом ошибок через @on_error.

        Выполняет regular-аспекты, затем summary-аспект. Эмитирует
        BeforeSummaryAspectEvent и AfterSummaryAspectEvent вокруг summary.

        При исключении делегирует обработку в _handle_aspect_error(),
        который эмитирует BeforeOnErrorAspectEvent / AfterOnErrorAspectEvent
        или UnhandledErrorEvent.
        """
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)
        failed_aspect_name: str | None = None

        try:
            state = await self._execute_regular_aspects(
                action, params, box, connections, context, metadata, plugin_ctx,
            )

            summary_meta = self._get_summary_aspect(metadata)
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
            # ── Делегируем обработку ошибки ────────────────────────────
            error_state = BaseState()
            handled_result = await self._handle_aspect_error(
                error=aspect_error,
                action=action,
                params=params,
                state=error_state,
                box=box,
                connections=connections,
                metadata=metadata,
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
        Внутренний метод выполнения с поддержкой вложенности и rollup.

        Вызывается из run() (nested_level=0, rollup=False) и из ToolsBox.run()
        (nested_level > 0). Rollup прокидывается в ToolsBox и через замыкание
        run_child в дочерние вызовы _run_internal().

        Создаёт типизированные события GlobalStartEvent и GlobalFinishEvent
        и передаёт их в plugin_ctx.emit_event() вместо строковых имён.
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
                state=BaseState(),
                params=params,
            )

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

            box = ToolsBox(
                run_child=run_child,
                factory=factory,
                resources=resources,
                context=context,
                log=log,
                nested_level=current_nest,
                rollup=rollup,
            )

            base_fields = self._base_event_fields(action, context, params, current_nest)

            # ── GlobalStartEvent ──────────────────────────────────────
            await plugin_ctx.emit_event(
                GlobalStartEvent(**base_fields),
                **plugin_kwargs,
            )

            result = await self._execute_aspects_with_error_handling(
                action, params, box, conns, context, metadata, plugin_ctx,
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
