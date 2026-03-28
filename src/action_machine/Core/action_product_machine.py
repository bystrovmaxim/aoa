# src/action_machine/core/action_product_machine.py
"""
Модуль: ActionProductMachine — production-реализация машины действий.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ActionProductMachine — центральный исполнитель действий (Action) в системе.
Получает экземпляр действия, входные параметры и контекст, после чего:

1. Проверяет ролевые ограничения (@CheckRoles) через ClassMetadata.
2. Валидирует соединения (@connection) через ClassMetadata:
   - Проверяет соответствие ключей (объявленные vs фактические).
   - Проверяет, что каждое значение — экземпляр BaseResourceManager.
3. Получает stateless-фабрику зависимостей через координатор.
4. Создаёт изолированный PluginRunContext для текущего запроса.
5. Последовательно выполняет regular-аспекты, проверяя результаты чекерами.
6. Выполняет summary-аспект, формирующий итоговый Result.
7. Уведомляет плагины о событиях через PluginRunContext.

═══════════════════════════════════════════════════════════════════════════════
STATELESS МЕЖДУ ЗАПРОСАМИ
═══════════════════════════════════════════════════════════════════════════════

Машина не хранит никакого мутабельного состояния между вызовами run().
Каждый вызов полностью изолирован:

- Метаданные получаются из GateCoordinator (кешируются там, не здесь).
- Фабрика зависимостей получается из GateCoordinator (кешируется там).
- Состояние конвейера (BaseState) создаётся заново при каждом вызове.
- Состояния плагинов инкапсулированы в PluginRunContext, который
  создаётся в начале run() и уничтожается по завершении.

═══════════════════════════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ С GATECOORDINATOR
═══════════════════════════════════════════════════════════════════════════════

Машина НЕ обращается к «сырым» атрибутам класса (_role_info, _depends_info
и т.д.). Вместо этого она получает иммутабельный снимок ClassMetadata
через GateCoordinator:

    metadata = self._coordinator.get(action.__class__)

Фабрика зависимостей:

    factory = self._coordinator.get_factory(action.__class__)

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ СОЕДИНЕНИЙ
═══════════════════════════════════════════════════════════════════════════════

Метод _check_connections выполняет двухуровневую валидацию:

1. Проверка ключей: объявленные через @connection ключи должны точно
   совпадать с фактически переданными. Лишние и недостающие ключи —
   ошибка ConnectionValidationError.

2. Проверка типов значений: каждое значение в connections должно быть
   экземпляром BaseResourceManager. Строки, числа, None и другие типы
   отклоняются с понятным сообщением об ошибке. Это позволяет обнаружить
   ошибку конфигурации на входе в машину, а не глубоко внутри аспекта.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ВЫПОЛНЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

    machine.run(context, action, params, connections)
        │
        ├── 1. _check_action_roles(action, context, metadata)
        ├── 2. _check_connections(action, connections, metadata)
        │       ├── проверка ключей (4 валидатора)
        │       └── проверка типов (isinstance BaseResourceManager)
        ├── 3. coordinator.get_factory(action.__class__)
        ├── 4. plugin_ctx = plugin_coordinator.create_run_context()
        ├── 5. plugin_ctx.emit_event("global_start", ...)
        ├── 6. _execute_regular_aspects(...)
        │       └── для каждого AspectMeta с type=="regular":
        │           ├── before-событие плагинам
        │           ├── вызов метода аспекта
        │           ├── _apply_checkers(...)
        │           └── after-событие плагинам
        ├── 7. _call_aspect(summary, ...)
        ├── 8. plugin_ctx.emit_event("global_finish", ...)
        └── 9. return Result
"""

import time
from typing import Any, TypeVar, cast

from action_machine.auth.check_roles import CheckRoles
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_action_machine import BaseActionMachine
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.class_metadata import AspectMeta, CheckerMeta, ClassMetadata
from action_machine.core.exceptions import (
    AuthorizationError,
    ConnectionValidationError,
    ValidationFieldError,
)
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionProductMachine(BaseActionMachine):
    """
    Production-реализация машины действий (полностью асинхронная).

    Выполняет действие по конвейеру аспектов, проверяет роли и соединения,
    применяет чекеры к результатам аспектов, уведомляет плагины о событиях.

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
                         создаётся новый экземпляр.
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
        """
        Возвращает ClassMetadata для действия через координатор.

        Аргументы:
            action: экземпляр действия.

        Возвращает:
            ClassMetadata — иммутабельный снимок метаданных класса.
        """
        return self._coordinator.get(action.__class__)

    # ─────────────────────────────────────────────────────────────────────
    # Проверка чекеров
    # ─────────────────────────────────────────────────────────────────────

    def _get_checkers_for_aspect(
        self,
        metadata: ClassMetadata,
        aspect_meta: AspectMeta,
    ) -> tuple[CheckerMeta, ...]:
        """
        Возвращает чекеры, привязанные к конкретному аспекту.

        Аргументы:
            metadata: метаданные класса действия.
            aspect_meta: метаданные аспекта.

        Возвращает:
            tuple[CheckerMeta, ...] — чекеры для метода аспекта.
        """
        return metadata.get_checkers_for_aspect(aspect_meta.method_name)

    def _apply_checkers(
        self,
        checkers: tuple[CheckerMeta, ...],
        result: dict[str, Any],
    ) -> None:
        """
        Применяет все чекеры к словарю результата аспекта.

        Каждый чекер создаётся из CheckerMeta и вызывается с результатом.

        Аргументы:
            checkers: кортеж метаданных чекеров.
            result: словарь с результатом аспекта.

        Исключения:
            ValidationFieldError: если какая-либо проверка не пройдена.
        """
        for checker_meta in checkers:
            checker_instance = checker_meta.checker_class(
                checker_meta.field_name,
                checker_meta.description,
                required=checker_meta.required,
                **checker_meta.extra_params,
            )
            checker_instance.check(result)

    # ─────────────────────────────────────────────────────────────────────
    # Проверка ролей
    # ─────────────────────────────────────────────────────────────────────

    def _check_none_role(self, user_roles: list[str]) -> bool:
        """Проверка для CheckRoles.NONE — доступ без аутентификации. Всегда True."""
        return True

    def _check_any_role(self, user_roles: list[str]) -> bool:
        """
        Проверка для CheckRoles.ANY — требуется хотя бы одна роль.

        Исключения:
            AuthorizationError: если у пользователя нет ни одной роли.
        """
        if not user_roles:
            raise AuthorizationError(
                "Authentication required: user must have at least one role"
            )
        return True

    def _check_list_role(self, spec: list[str], user_roles: list[str]) -> bool:
        """
        Проверка для списка ролей — у пользователя должна быть хотя бы одна.

        Исключения:
            AuthorizationError: если пересечение пустое.
        """
        if any(role in user_roles for role in spec):
            return True
        raise AuthorizationError(
            f"Access denied. Required one of the roles: {spec}, "
            f"user roles: {user_roles}"
        )

    def _check_single_role(self, spec: str, user_roles: list[str]) -> bool:
        """
        Проверка для одной конкретной роли.

        Исключения:
            AuthorizationError: если роль отсутствует у пользователя.
        """
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
        """
        Проверяет ролевые ограничения действия через ClassMetadata.

        Аргументы:
            action: экземпляр действия.
            context: контекст выполнения.
            metadata: метаданные класса действия.

        Исключения:
            TypeError: если действие не имеет декоратора @CheckRoles.
            AuthorizationError: если роли не соответствуют требованиям.
        """
        if not metadata.has_role() or metadata.role is None:
            raise TypeError(
                f"Action {action.__class__.__name__} does not have a @CheckRoles "
                f"decorator. Specify @CheckRoles(CheckRoles.NONE) explicitly if "
                f"the action is accessible without authentication."
            )

        role_spec = metadata.role.spec
        user_roles = context.user.roles

        if role_spec == CheckRoles.NONE:
            self._check_none_role(user_roles)
        elif role_spec == CheckRoles.ANY:
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
        """
        Проверяет, что каждое значение в connections — экземпляр BaseResourceManager.

        Выполняется после проверки ключей. Обнаруживает ошибки конфигурации
        на входе в машину, а не глубоко внутри аспекта, где сообщение об ошибке
        было бы менее информативным.

        Аргументы:
            action_name: имя действия для сообщения об ошибке.
            connections: словарь соединений для проверки.

        Возвращает:
            Строку с сообщением об ошибке или None если всё корректно.
        """
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
        """
        Проверяет соответствие переданных connections объявленным через @connection.

        Двухуровневая валидация:
        1. Проверка ключей: объявленные ключи должны точно совпадать
           с фактическими. Лишние и недостающие ключи — ошибка.
        2. Проверка типов: каждое значение должно быть экземпляром
           BaseResourceManager. Строки, числа, None — ошибка.

        Аргументы:
            action: экземпляр действия.
            connections: словарь соединений (или None).
            metadata: метаданные класса действия.

        Возвращает:
            dict[str, BaseResourceManager] — проверенные соединения.

        Исключения:
            ConnectionValidationError: при несоответствии ключей или типов.
        """
        declared_keys: set[str] = set(metadata.get_connection_keys())
        actual_keys: set[str] = set(connections.keys()) if connections else set()
        action_name: str = action.__class__.__name__

        # Этап 1: проверка ключей
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

        # Этап 2: проверка типов значений
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

        Создаёт ScopedLogger с именем аспекта, реальными state и params,
        оборачивает в новый ToolsBox и вызывает метод.

        Аргументы:
            aspect_meta: метаданные аспекта (None → возвращает пустой BaseResult).
            action: экземпляр действия.
            params: входные параметры.
            state: текущее состояние конвейера.
            box: базовый ToolsBox.
            connections: словарь менеджеров ресурсов.
            context: контекст выполнения.

        Возвращает:
            Результат аспекта (dict для regular, BaseResult для summary).
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
            context=box.context,
            log=aspect_log,
            nested_level=box.nested_level,
        )

        return await aspect_meta.method_ref(action, params, state, aspect_box, connections)

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

        Для каждого аспекта: before-событие → вызов → валидация чекерами →
        обновление state → after-событие.

        Правила чекеров:
        - Нет чекеров + непустой dict → ошибка.
        - Есть чекеры → лишние поля → ошибка.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            box: ToolsBox для этого уровня.
            connections: словарь менеджеров ресурсов.
            context: контекст выполнения.
            metadata: метаданные класса.
            plugin_ctx: контекст плагинов.

        Возвращает:
            BaseState — итоговое состояние.

        Исключения:
            TypeError: regular-аспект вернул не dict.
            ValidationFieldError: чекер не прошёл или лишние поля.
        """
        state = BaseState()
        regular_aspects = self._get_regular_aspects(metadata)

        for aspect_meta in regular_aspects:
            aspect_name = aspect_meta.method_name

            await plugin_ctx.emit_event(
                event_name=f"before:{aspect_name}",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=False,
                result=None,
                duration=None,
                factory=box.factory,
                context=context,
                nest_level=box.nested_level,
            )

            aspect_start = time.time()

            new_state_dict = await self._call_aspect(
                aspect_meta, action, params, state, box, connections, context
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

            state = BaseState({**state.to_dict(), **new_state_dict})

            aspect_duration = time.time() - aspect_start

            await plugin_ctx.emit_event(
                event_name=f"after:{aspect_name}",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=False,
                result=None,
                duration=aspect_duration,
                factory=box.factory,
                context=context,
                nest_level=box.nested_level,
            )

        return state

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
        Асинхронно выполняет действие с поддержкой плагинов и вложенности.

        Каждый вызов полностью изолирован от предыдущих.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            connections: словарь менеджеров ресурсов (или None).

        Возвращает:
            R — результат выполнения действия.
        """
        return await self._run_internal(
            context=context,
            action=action,
            params=params,
            resources=None,
            connections=connections,
            nested_level=0,
        )

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type, Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
    ) -> R:
        """
        Внутренний метод выполнения с поддержкой вложенности.

        Вызывается из run() (nested_level=0) и из ToolsBox.run()
        (nested_level > 0).

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы (моки в тестах).
            connections: менеджеры ресурсов.
            nested_level: текущий уровень вложенности.

        Возвращает:
            R — результат действия.
        """
        current_nest = nested_level + 1
        start_time = time.time()

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
            )

            return cast(R, result)

        finally:
            pass
