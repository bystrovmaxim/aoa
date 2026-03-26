# src/action_machine/Core/ActionProductMachine.py
"""
Модуль: ActionProductMachine — production-реализация машины действий.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ActionProductMachine — центральный исполнитель действий (Action) в системе.
Получает экземпляр действия, входные параметры и контекст, после чего:

1. Проверяет ролевые ограничения (@CheckRoles) через ClassMetadata.
2. Валидирует соединения (@connection) через ClassMetadata.
3. Создаёт (или берёт из кеша) фабрику зависимостей (@depends).
4. Последовательно выполняет regular-аспекты, проверяя результаты чекерами.
5. Выполняет summary-аспект, формирующий итоговый Result.
6. Уведомляет плагины о событиях (global_start, global_finish, before/after).

═══════════════════════════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ С GATECOORDINATOR
═══════════════════════════════════════════════════════════════════════════════

Машина НЕ обращается к «сырым» атрибутам класса (_role_info, _depends_info,
_connection_info и т.д.). Вместо этого она получает иммутабельный снимок
ClassMetadata через GateCoordinator:

    metadata = self._coordinator.get(action.__class__)
    metadata.role          → RoleMeta | None
    metadata.dependencies  → tuple[DependencyInfo, ...]
    metadata.connections   → tuple[ConnectionInfo, ...]
    metadata.aspects       → tuple[AspectMeta, ...]
    metadata.checkers      → tuple[CheckerMeta, ...]

GateCoordinator передаётся в конструктор машины (dependency injection).
При первом обращении к классу координатор вызывает MetadataBuilder.build(),
кеширует результат и возвращает его при повторных вызовах.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ВЫПОЛНЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

    machine.run(context, action, params, connections)
        │
        ├── 1. _check_action_roles(action, context)
        │       └── metadata.role → RoleMeta → проверка spec
        │
        ├── 2. _check_connections(action, connections)
        │       └── metadata.connections → declared keys vs actual keys
        │
        ├── 3. _get_factory(action)
        │       └── metadata.dependencies → DependencyFactory
        │
        ├── 4. plugin: global_start
        │
        ├── 5. _execute_regular_aspects(...)
        │       └── для каждого AspectMeta с type=="regular":
        │           ├── plugin: before:{aspect_name}
        │           ├── вызов метода
        │           ├── _apply_checkers(action, aspect_meta, result)
        │           └── plugin: after:{aspect_name}
        │
        ├── 6. _call_aspect(summary, ...)
        │
        ├── 7. plugin: global_finish
        │
        └── 8. return Result

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.Core.gate_coordinator import GateCoordinator
    from action_machine.Core.ActionProductMachine import ActionProductMachine

    coordinator = GateCoordinator()
    machine = ActionProductMachine(
        mode="production",
        coordinator=coordinator,
        plugins=[CounterPlugin()],
    )

    result = await machine.run(
        context=context,
        action=CreateOrderAction(),
        params=OrderParams(user_id="max", amount=100.0),
        connections={"db": pg_manager, "cache": redis_manager},
    )
"""

import time
from typing import Any, TypeVar, cast

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseActionMachine import BaseActionMachine
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.class_metadata import AspectMeta, CheckerMeta, ClassMetadata
from action_machine.Core.Exceptions import (
    AuthorizationError,
    ConnectionValidationError,
    ValidationFieldError,
)
from action_machine.Core.gate_coordinator import GateCoordinator
from action_machine.Core.ToolsBox import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.dependencies.dependency_gate import DependencyGate
from action_machine.Logging.action_bound_logger import ActionBoundLogger
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginCoordinator import PluginCoordinator
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionProductMachine(BaseActionMachine):
    """
    Production-реализация машины действий (полностью асинхронная).

    Выполняет действие по конвейеру аспектов, проверяет роли и соединения,
    применяет чекеры к результатам аспектов, уведомляет плагины о событиях.

    Все метаданные о действии (роли, зависимости, аспекты, чекеры, соединения)
    получаются через GateCoordinator → ClassMetadata. Машина НЕ обращается
    к внутренним атрибутам классов (_role_info, _depends_info и т.д.).

    Атрибуты:
        _mode : str
            Режим выполнения ("production", "test", "staging" и т.д.).
        _coordinator : GateCoordinator
            Координатор метаданных. Кеширует ClassMetadata для каждого класса.
        _plugin_coordinator : PluginCoordinator
            Координатор плагинов. Рассылает события плагинам.
        _log_coordinator : LogCoordinator
            Координатор логирования. Рассылает логи по логгерам.
        _factory_cache : dict[type, DependencyFactory]
            Кеш фабрик зависимостей. Ключ — класс действия.
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
                  Примеры: "production", "test", "staging".
            coordinator: координатор метаданных. Если не указан, создаётся
                         новый экземпляр GateCoordinator().
            plugins: список экземпляров плагинов (по умолчанию пустой).
            log_coordinator: координатор логирования. Если не указан, создаётся
                             координатор с одним ConsoleLogger(use_colors=True).

        Исключения:
            ValueError: если mode — пустая строка.
        """
        if not mode:
            raise ValueError("mode must be non-empty")

        self._mode: str = mode

        # Координатор метаданных (DI или создание по умолчанию)
        self._coordinator: GateCoordinator = coordinator or GateCoordinator()

        # Координатор плагинов
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
        )

        # Координатор логирования
        if log_coordinator is None:
            log_coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
        self._log_coordinator: LogCoordinator = log_coordinator

        # Кеш фабрик зависимостей по классу действия
        self._factory_cache: dict[type, DependencyFactory] = {}

    # ─────────────────────────────────────────────────────────────────────
    # Получение метаданных
    # ─────────────────────────────────────────────────────────────────────

    def _get_metadata(self, action: BaseAction[Any, Any]) -> ClassMetadata:
        """
        Возвращает ClassMetadata для действия через координатор.

        Первый вызов для класса собирает метаданные через MetadataBuilder,
        последующие возвращают кешированный объект.

        Аргументы:
            action: экземпляр действия.

        Возвращает:
            ClassMetadata — иммутабельный снимок метаданных класса.
        """
        return self._coordinator.get(action.__class__)

    # ─────────────────────────────────────────────────────────────────────
    # Фабрика зависимостей
    # ─────────────────────────────────────────────────────────────────────

    def _get_factory(self, action: BaseAction[Any, Any]) -> DependencyFactory:
        """
        Возвращает (и кеширует) фабрику зависимостей для действия.

        Создаёт DependencyGate из метаданных действия, замораживает его,
        и оборачивает в DependencyFactory. Фабрика кешируется по классу
        действия — повторные вызовы для того же класса возвращают
        существующую фабрику.

        Аргументы:
            action: экземпляр действия.

        Возвращает:
            DependencyFactory — фабрика для резолва зависимостей через ToolsBox.
        """
        action_class = action.__class__

        if action_class not in self._factory_cache:
            metadata = self._get_metadata(action)

            # Создаём DependencyGate из собранных DependencyInfo
            gate = DependencyGate()
            for dep_info in metadata.dependencies:
                gate.register(dep_info)
            gate.freeze()

            self._factory_cache[action_class] = DependencyFactory(gate)

        return self._factory_cache[action_class]

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
            aspect_meta: метаданные аспекта, для которого ищем чекеры.

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
        Если проверка не пройдена, чекер сам выбрасывает ValidationFieldError.

        Аргументы:
            checkers: кортеж метаданных чекеров.
            result: словарь с результатом аспекта.

        Исключения:
            ValidationFieldError: если какая-либо проверка не пройдена.
        """
        for checker_meta in checkers:
            # Создаём экземпляр чекера из его класса и параметров
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
        """
        Проверка для CheckRoles.NONE — доступ без аутентификации.
        Всегда возвращает True.
        """
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
        Проверка для списка ролей — у пользователя должна быть хотя бы одна
        из перечисленных ролей.

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

        Читает metadata.role (RoleMeta) и сравнивает со списком ролей
        текущего пользователя из контекста.

        Аргументы:
            action: экземпляр действия (для сообщений об ошибках).
            context: контекст выполнения с информацией о пользователе.
            metadata: метаданные класса действия.

        Исключения:
            TypeError: если действие не имеет декоратора @CheckRoles.
            AuthorizationError: если роли пользователя не соответствуют требованиям.
        """
        if not metadata.has_role():
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

    def _check_connections(
        self,
        action: BaseAction[P, R],
        connections: dict[str, BaseResourceManager] | None,
        metadata: ClassMetadata,
    ) -> dict[str, BaseResourceManager]:
        """
        Проверяет соответствие переданных connections объявленным через @connection.

        Читает metadata.connections (tuple[ConnectionInfo, ...]), извлекает
        объявленные ключи и сравнивает с фактическими ключами из аргумента.

        Аргументы:
            action: экземпляр действия (для сообщений об ошибках).
            connections: словарь соединений (или None).
            metadata: метаданные класса действия.

        Возвращает:
            dict[str, BaseResourceManager] — проверенные соединения
            (пустой словарь, если соединения не объявлены и не переданы).

        Исключения:
            ConnectionValidationError: при несоответствии ключей.
        """
        declared_keys: set[str] = set(metadata.get_connection_keys())
        actual_keys: set[str] = set(connections.keys()) if connections else set()
        action_name: str = action.__class__.__name__

        validators = [
            self._validate_no_declarations_but_got_connections,
            self._validate_has_declarations_but_no_connections,
            self._validate_extra_connection_keys,
            self._validate_missing_connection_keys,
        ]

        for validator in validators:
            error = validator(action_name, declared_keys, actual_keys)
            if error:
                raise ConnectionValidationError(error)

        return connections or {}

    # ─────────────────────────────────────────────────────────────────────
    # Извлечение аспектов из метаданных
    # ─────────────────────────────────────────────────────────────────────

    def _get_regular_aspects(
        self, metadata: ClassMetadata,
    ) -> tuple[AspectMeta, ...]:
        """
        Извлекает regular-аспекты из ClassMetadata.

        Возвращает:
            tuple[AspectMeta, ...] — regular-аспекты в порядке объявления.
        """
        return metadata.get_regular_aspects()

    def _get_summary_aspect(
        self, metadata: ClassMetadata,
    ) -> AspectMeta | None:
        """
        Извлекает summary-аспект из ClassMetadata.

        Возвращает:
            AspectMeta | None — summary-аспект или None.
        """
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

        Создаёт ActionBoundLogger с именем аспекта, оборачивает в новый
        ToolsBox (чтобы логи показывали правильный aspect_name) и вызывает
        метод: method(action, params, state, box, connections).

        Аргументы:
            aspect_meta: метаданные аспекта (None → возвращает пустой BaseResult).
            action: экземпляр действия.
            params: входные параметры.
            state: текущее состояние конвейера.
            box: базовый ToolsBox (будет заменён на box с правильным логером).
            connections: словарь менеджеров ресурсов.
            context: контекст выполнения.

        Возвращает:
            Результат аспекта (dict для regular, BaseResult для summary).
        """
        if aspect_meta is None:
            return BaseResult()

        # Создаём логер с именем аспекта
        aspect_log = ActionBoundLogger(
            coordinator=self._log_coordinator,
            nest_level=box.nested_level,
            machine_name=self.__class__.__name__,
            mode=self._mode,
            action_name=action.get_full_class_name(),
            aspect_name=aspect_meta.method_name,
            context=context,
        )

        # Создаём ToolsBox с логером для конкретного аспекта
        aspect_box = ToolsBox(
            run_child=box.run_child,
            factory=box.factory,
            resources=box.resources,
            context=box.context,
            log=aspect_log,
            nested_level=box.nested_level,
        )

        # Вызываем метод через method_ref из AspectMeta
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
    ) -> BaseState:
        """
        Последовательно выполняет regular-аспекты действия.

        Для каждого аспекта:
        1. Уведомляет плагины о событии before:{aspect_name}.
        2. Вызывает метод аспекта.
        3. Валидирует результат: regular-аспект должен вернуть dict.
        4. Проверяет результат чекерами (если есть).
        5. Объединяет результат с текущим состоянием.
        6. Уведомляет плагины о событии after:{aspect_name}.

        Правила чекеров:
        - Если у аспекта нет чекеров и он вернул непустой dict → ошибка.
          Это гарантирует, что каждое поле в state было провалидировано.
        - Если у аспекта есть чекеры, проверяются только объявленные поля.
          Лишние поля (не объявленные в чекерах) → ошибка.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            box: ToolsBox для этого уровня вложенности.
            connections: словарь менеджеров ресурсов.
            context: контекст выполнения.
            metadata: метаданные класса действия.

        Возвращает:
            BaseState — итоговое состояние после всех regular-аспектов.

        Исключения:
            TypeError: если regular-аспект вернул не dict.
            ValidationFieldError: если чекер не прошёл или есть лишние поля.
        """
        state = BaseState()
        regular_aspects = self._get_regular_aspects(metadata)

        for aspect_meta in regular_aspects:
            aspect_name = aspect_meta.method_name

            # ── before-событие ──────────────────────────────────────────
            await self._plugin_coordinator.emit_event(
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

            # ── Выполнение аспекта ──────────────────────────────────────
            aspect_start = time.time()

            new_state_dict = await self._call_aspect(
                aspect_meta, action, params, state, box, connections, context
            )

            if not isinstance(new_state_dict, dict):
                raise TypeError(
                    f"Aspect {aspect_meta.method_name} must return a dict, "
                    f"got {type(new_state_dict).__name__}"
                )

            # ── Валидация чекерами ──────────────────────────────────────
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

            # ── Обновление состояния ────────────────────────────────────
            state = BaseState({**state.to_dict(), **new_state_dict})

            aspect_duration = time.time() - aspect_start

            # ── after-событие ───────────────────────────────────────────
            await self._plugin_coordinator.emit_event(
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

        Это публичная точка входа. Последовательность выполнения:
        1. Получить ClassMetadata через координатор.
        2. Проверить роли (@CheckRoles).
        3. Проверить соединения (@connection).
        4. Создать/получить фабрику зависимостей.
        5. Уведомить плагины: global_start.
        6. Выполнить regular-аспекты с чекерами.
        7. Выполнить summary-аспект.
        8. Уведомить плагины: global_finish.
        9. Вернуть результат.

        Аргументы:
            context: контекст выполнения (пользователь, запрос, окружение).
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

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы для зависимостей (приоритет над фабрикой).
            connections: менеджеры ресурсов.
            nested_level: текущий уровень вложенности (0 для корневого вызова).

        Возвращает:
            R — результат действия.
        """
        current_nest = nested_level + 1
        start_time = time.time()

        try:
            # ── Метаданные ──────────────────────────────────────────────
            metadata = self._get_metadata(action)

            # ── Проверки ────────────────────────────────────────────────
            self._check_action_roles(action, context, metadata)
            conns = self._check_connections(action, connections, metadata)

            # ── Фабрика зависимостей ────────────────────────────────────
            factory = self._get_factory(action)

            # ── Логер для этого уровня ──────────────────────────────────
            log = ActionBoundLogger(
                coordinator=self._log_coordinator,
                nest_level=current_nest,
                machine_name=self.__class__.__name__,
                mode=self._mode,
                action_name=action.get_full_class_name(),
                aspect_name="",
                context=context,
            )

            # ── Замыкание для запуска дочерних действий ─────────────────
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

            # ── ToolsBox ────────────────────────────────────────────────
            box = ToolsBox(
                run_child=run_child,
                factory=factory,
                resources=resources,
                context=context,
                log=log,
                nested_level=current_nest,
            )

            # ── global_start ────────────────────────────────────────────
            await self._plugin_coordinator.emit_event(
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

            # ── Regular-аспекты ─────────────────────────────────────────
            state = await self._execute_regular_aspects(
                action, params, box, conns, context, metadata
            )

            # ── Summary-аспект ──────────────────────────────────────────
            summary_meta = self._get_summary_aspect(metadata)

            result = await self._call_aspect(
                summary_meta, action, params, state, box, conns, context
            )

            total_duration = time.time() - start_time

            # ── global_finish ───────────────────────────────────────────
            await self._plugin_coordinator.emit_event(
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
