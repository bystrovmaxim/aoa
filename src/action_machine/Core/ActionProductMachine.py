"""
Product action machine implementation with plugin support and nesting.
Fully asynchronous version. Uses PluginEvent to pass data to plugins.

Управление метаданными действий (роли, зависимости, чекеры) осуществляется
через шлюзы (gates). Машина получает доступ к этим данным через методы
действия: get_role_gate(), get_dependency_gate(), get_checker_gate().

Все обращения к устаревшим атрибутам (_role_spec, _dependencies,
_field_checkers, _result_checkers) заменены на вызовы соответствующих шлюзов.
"""

import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from action_machine.aspects.aspect_method_protocol import AspectMethodProtocol
from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseActionMachine import BaseActionMachine
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.Exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
from action_machine.Core.ToolsBox import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory
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
    Production реализация машины действий (асинхронная).

    Содержит логику кэширования фабрик зависимостей,
    выполняет проверку ролей, валидацию результатов аспектов через чекеры,
    и проверяет соответствие переданных connections объявленным с @connection.

    Управление плагинами делегируется PluginCoordinator.

    Машина **не** хранит контекст запроса; контекст должен передаваться
    в метод `run()` для каждого выполнения.
    """

    def __init__(
        self,
        mode: str,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Инициализирует машину действий.

        Аргументы:
            mode: режим выполнения (обязательный, не пустой). Примеры: "production", "test", "staging".
            plugins: список экземпляров плагинов (по умолчанию пустой).
            log_coordinator: координатор логирования. Если не указан, создаётся
                             координатор с одним ConsoleLogger(use_colors=True).

        Исключения:
            ValueError: если mode — пустая строка.
        """
        if not mode:
            raise ValueError("mode must be non-empty")
        self._mode = mode

        # Координатор плагинов
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
        )

        # Координатор логирования
        if log_coordinator is None:
            log_coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
        self._log_coordinator = log_coordinator

        # Кэш фабрик зависимостей по классу действия
        self._factory_cache: dict[type[Any], DependencyFactory] = {}

    def _get_factory(self, action: BaseAction[Any, Any]) -> DependencyFactory:
        """
        Возвращает (и кэширует) фабрику зависимостей для действия.

        Использует шлюз зависимостей действия для создания фабрики.
        """
        action_class = action.__class__
        if action_class not in self._factory_cache:
            gate = action.get_dependency_gate()
            self._factory_cache[action_class] = DependencyFactory(gate)
        return self._factory_cache[action_class]

    def _apply_checkers(
        self,
        action: BaseAction[Any, Any],
        method: Callable[..., Any],
        result: dict[str, Any],
    ) -> None:
        """
        Применяет все чекеры, прикреплённые к методу, к словарю результата.

        Аргументы:
            action: экземпляр действия.
            method: метод, для которого зарегистрированы чекеры.
            result: словарь с результатом аспекта.

        Исключения:
            ValidationFieldError: если какая-либо проверка не пройдена.
        """
        gate = action.get_checker_gate()
        checkers = gate.get_method_checkers(method)
        for checker in checkers:
            checker.check(result)

    # ---------- Проверка ролей ----------

    def _check_none_role(self, user_roles: list[str]) -> bool:
        """Проверка для CheckRoles.NONE (всегда разрешено)."""
        return True

    def _check_any_role(self, user_roles: list[str]) -> bool:
        """Проверка для CheckRoles.ANY (требуется хотя бы одна роль)."""
        if not user_roles:
            raise AuthorizationError("Authentication required: user must have at least one role")
        return True

    def _check_list_role(self, spec: list[str], user_roles: list[str]) -> bool:
        """Проверка для списка ролей (пересечение)."""
        if any(role in user_roles for role in spec):
            return True
        raise AuthorizationError(
            f"Access denied. Required one of the roles: {spec}, user roles: {user_roles}"
        )

    def _check_single_role(self, spec: str, user_roles: list[str]) -> bool:
        """Проверка для одной конкретной роли."""
        if spec in user_roles:
            return True
        raise AuthorizationError(f"Access denied. Required role: '{spec}', user roles: {user_roles}")

    def _check_action_roles(self, action: BaseAction[P, R], context: Context) -> None:
        """
        Проверяет, что действие имеет спецификацию ролей (декоратор CheckRoles)
        и что текущий пользователь из контекста удовлетворяет ей.

        Аргументы:
            action: экземпляр действия.
            context: контекст выполнения, содержащий информацию о пользователе.

        Исключения:
            TypeError: если действие не имеет спецификации ролей.
            AuthorizationError: если роли пользователя не соответствуют требованиям.
        """
        gate = action.get_role_gate()
        role_spec = gate.get_role_spec()

        if role_spec is None:
            raise TypeError(
                f"Action {action.__class__.__name__} does not have a CheckRoles decorator. "
                "Specify CheckRoles.NONE explicitly if the action is accessible without authentication."
            )

        user_roles = context.user.roles

        if role_spec == CheckRoles.NONE:
            self._check_none_role(user_roles)
        elif role_spec == CheckRoles.ANY:
            self._check_any_role(user_roles)
        elif isinstance(role_spec, list):
            self._check_list_role(role_spec, user_roles)
        else:
            self._check_single_role(role_spec, user_roles)

    # ---------- Проверка соединений ----------

    @staticmethod
    def _get_declared_connection_keys(action: BaseAction[P, R]) -> set[str]:
        """Возвращает множество ключей соединений, объявленных через @connection."""
        # Пока используем старый атрибут _connections, так как миграция ConnectionGate ещё не завершена.
        declared: list[dict[str, Any]] = getattr(action.__class__, "_connections", [])
        return {info["key"] for info in declared}

    @staticmethod
    def _validate_no_declarations_but_got_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        if not declared_keys and actual_keys:
            return (f"Action {action_name} does not declare any @connection, "
                    f"but received connections with keys: {actual_keys}. "
                    f"Remove the connections from the call or add the @connection decorator.")
        return None

    @staticmethod
    def _validate_has_declarations_but_no_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        if declared_keys and not actual_keys:
            return (f"Action {action_name} declares connections: {declared_keys}, "
                    f"but no connections were passed (None or empty dict). "
                    f"Pass connections with keys: {declared_keys}.")
        return None

    @staticmethod
    def _validate_extra_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        extra = actual_keys - declared_keys
        if extra:
            return (f"Action {action_name} received extra connections: {extra}. "
                    f"Only declared: {declared_keys}. Remove the extra keys.")
        return None

    @staticmethod
    def _validate_missing_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        missing = declared_keys - actual_keys
        if missing:
            return (f"Action {action_name} is missing required connections: {missing}. "
                    f"Declared: {declared_keys}, received: {actual_keys}.")
        return None

    def _check_connections(
        self, action: BaseAction[P, R], connections: dict[str, BaseResourceManager] | None
    ) -> dict[str, BaseResourceManager]:
        """
        Проверяет, что переданные connections соответствуют объявленным с @connection.

        Аргументы:
            action: экземпляр действия.
            connections: словарь соединений (или None).

        Возвращает:
            Проверенные connections (пустой словарь, если None и нет объявлений).

        Исключения:
            ConnectionValidationError: при несоответствии.
        """
        declared_keys = self._get_declared_connection_keys(action)
        actual_keys = set(connections.keys()) if connections else set()
        action_name = action.__class__.__name__

        for validator in [
            self._validate_no_declarations_but_got_connections,
            self._validate_has_declarations_but_no_connections,
            self._validate_extra_connection_keys,
            self._validate_missing_connection_keys,
        ]:
            error = validator(action_name, declared_keys, actual_keys)
            if error:
                raise ConnectionValidationError(error)
        return connections or {}

    # ---------- Основные асинхронные методы run ----------

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Асинхронно выполняет действие с поддержкой плагинов и вложенности.

        Это публичная точка входа. Ресурсы не принимаются здесь;
        они передаются неявно через зависимости действия.

        Последовательность выполнения:
            1. Увеличить уровень вложенности.
            2. Проверить роли (декоратор CheckRoles) с использованием переданного контекста.
            3. Проверить соединения (декоратор @connection).
            4. Событие global_start (плагины через PluginCoordinator).
            5. Выполнить обычные аспекты (с вызовами before/after).
            6. Выполнить summary-аспект.
            7. Событие global_finish с общей длительностью.
            8. Уменьшить уровень вложенности.

        Аргументы:
            context: контекст выполнения для этого запроса (пользователь, запрос, окружение).
            action: экземпляр действия.
            params: входные параметры.
            connections: словарь менеджеров ресурсов (соединений).

        Возвращает:
            Результат выполнения действия.
        """
        return await self._run_internal(context, action, params, resources=None, connections=connections, nested_level=0)

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
        Внутренний метод выполнения, обрабатывающий вложенность и передачу ресурсов.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы для зависимостей (приоритет над фабрикой).
            connections: менеджеры ресурсов.
            nested_level: текущий уровень вложенности (0 для корня).

        Возвращает:
            Результат действия.
        """
        current_nest = nested_level + 1
        start_time = time.time()

        try:
            self._check_action_roles(action, context)
            conns = self._check_connections(action, connections)
            factory = self._get_factory(action)

            # Создаём логер для этого уровня
            log = ActionBoundLogger(
                coordinator=self._log_coordinator,
                nest_level=current_nest,
                machine_name=self.__class__.__name__,
                mode=self._mode,
                action_name=action.get_full_class_name(),
                aspect_name="",  # будет установлен для каждого аспекта
                context=context,
            )

            # Создаём замыкание для запуска дочерних действий
            async def run_child(
                action: BaseAction[Any, Any],
                params: BaseParams,
                connections: dict[str, BaseResourceManager] | None,
            ) -> BaseResult:
                return await self._run_internal(
                    context=context,
                    action=action,
                    params=params,
                    resources=resources,
                    connections=connections,
                    nested_level=current_nest,
                )

            # Создаём ToolsBox для этого уровня
            box = ToolsBox(
                run_child=run_child,
                factory=factory,
                resources=resources,
                context=context,
                log=log,
                nested_level=current_nest,
            )

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

            # Получаем аспекты непосредственно из действия (кэшируются внутри AspectGateHost)
            regular_aspects, summary_method = action.get_aspects()
            state = await self._execute_regular_aspects(
                action, params, box, conns, context, regular_aspects
            )

            result = await self._call_aspect(
                summary_method[0] if summary_method else None,
                action, params, state, box, conns, context
            )

            total_duration = time.time() - start_time

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

    async def _call_aspect(
        self,
        method: AspectMethodProtocol | None,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
    ) -> Any:
        """
        Вызывает метод-аспект.

        Аспект получает `box` в качестве пятого аргумента (после connections)
        и использует его для разрешения зависимостей, логирования и запуска дочерних действий.

        Аргументы:
            method: метод-аспект для вызова (None означает отсутствие summary-аспекта).
            action: экземпляр действия.
            params: входные параметры.
            state: текущее состояние конвейера.
            box: экземпляр ToolsBox для этого уровня.
            connections: словарь менеджеров ресурсов.
            context: контекст выполнения (используется для логирования).

        Возвращает:
            Результат аспекта (или пустой BaseResult, если summary отсутствует).
        """
        if method is None:
            return BaseResult()

        # Создаём логер с именем аспекта для этого конкретного вызова
        aspect_log = ActionBoundLogger(
            coordinator=self._log_coordinator,
            nest_level=box.nested_level,
            machine_name=self.__class__.__name__,
            mode=self._mode,
            action_name=action.get_full_class_name(),
            aspect_name=method.__name__,
            context=context,
        )
        # Создаём новый box с логером для аспекта
        aspect_box = ToolsBox(
            run_child=box.run_child,
            factory=box.factory,
            resources=box.resources,
            context=box.context,
            log=aspect_log,
            nested_level=box.nested_level,
        )
        return await method(action, params, state, aspect_box, connections)

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        regular_aspects: list[tuple[AspectMethodProtocol, str]],
    ) -> BaseState:
        """
        Асинхронно выполняет цепочку обычных аспектов, вызывая before/after
        события плагинов для каждого через координатор.

        Для каждого аспекта:
            - вызвать before-событие плагина,
            - выполнить сам аспект,
            - проверить результат через чекеры,
            - вызвать after-событие плагина с длительностью.
        """
        state = BaseState()

        for method, description in regular_aspects:
            aspect_name = method.__name__

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

            aspect_start = time.time()
            # Создаём box для аспекта с правильным именем аспекта в логере
            aspect_log = ActionBoundLogger(
                coordinator=self._log_coordinator,
                nest_level=box.nested_level,
                machine_name=self.__class__.__name__,
                mode=self._mode,
                action_name=action.get_full_class_name(),
                aspect_name=aspect_name,
                context=context,
            )
            aspect_box = ToolsBox(
                run_child=box.run_child,
                factory=box.factory,
                resources=box.resources,
                context=box.context,
                log=aspect_log,
                nested_level=box.nested_level,
            )
            new_state_dict = await self._call_aspect(method, action, params, state, aspect_box, connections, context)
            if not isinstance(new_state_dict, dict):
                raise TypeError(
                    f"Aspect {method.__qualname__} must return a dict, got {type(new_state_dict).__name__}"
                )

            # Получаем чекеры для метода через шлюз действия
            gate = action.get_checker_gate()
            checkers = gate.get_method_checkers(method)

            if not checkers and new_state_dict:
                raise ValidationFieldError(
                    f"Aspect {method.__qualname__} has no checkers, "
                    f"but returned non-empty state: {new_state_dict}. "
                    f"Either add checkers for all fields, or return an empty dict."
                )

            if checkers:
                allowed_fields = {ch.field_name for ch in checkers}
                extra_fields = set(new_state_dict.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldError(
                        f"Aspect {method.__qualname__} returned extra fields: "
                        f"{extra_fields}. Allowed only: {allowed_fields}"
                    )
                self._apply_checkers(action, method, new_state_dict)

            state = BaseState(new_state_dict)

            aspect_duration = time.time() - aspect_start

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