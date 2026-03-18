"""
Реализация продуктовой машины действий с поддержкой плагинов и вложенности.
Полностью асинхронная версия. Использует PluginEvent для передачи данных в плагины.

Архитектурные решения:
    - Логика управления плагинами (инициализация состояний, кеширование
      обработчиков, асинхронный запуск с семафором) вынесена в отдельный
      класс PluginCoordinator (action_machine/Plugins/PluginCoordinator.py).
    - ActionProductMachine делегирует все вызовы плагинов через
      self._plugin_coordinator.emit_event(...).
    - Метод _check_connections разбит на 4 приватных валидатора,
      каждый из которых проверяет одно конкретное правило соответствия
      переданных connections объявленным через @connection.

Публичный API класса:
    - Конструктор принимает context, mode (обязательно), plugins, max_concurrent_handlers, log_coordinator.
    - Асинхронный метод run(...) запускает действие.
"""

import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Context.context import Context
from action_machine.Core.AspectMethod import AspectMethod
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseActionMachine import BaseActionMachine
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Core.Exceptions import AuthorizationError, ConnectionValidationError, ValidationFieldError
from action_machine.Logging.action_bound_logger import ActionBoundLogger
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginCoordinator import PluginCoordinator
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)

DEFAULT_MAX_CONCURRENT_HANDLERS = 10


class ActionProductMachine(BaseActionMachine):
    """
    Продуктовая реализация машины действий (асинхронная).

    Содержит логику кэширования аспектов и фабрик зависимостей,
    выполняет проверку ролей, валидацию результатов аспектов через чекеры,
    проверку соответствия connections объявленным через @connection.

    Управление плагинами делегировано PluginCoordinator —
    отдельному классу, который отвечает за инициализацию состояний,
    кеширование обработчиков и асинхронный запуск с семафором.

    Новое: поддержка сквозного логирования. Конструктор принимает:
        mode (str) – режим выполнения (например, "production", "test", "staging").
        log_coordinator (LogCoordinator | None) – координатор логирования.
            Если не передан, создаётся координатор с ConsoleLogger(use_colors=True).
    """

    def __init__(
        self,
        context: Context,
        mode: str,
        plugins: list[Plugin] | None = None,
        max_concurrent_handlers: int = DEFAULT_MAX_CONCURRENT_HANDLERS,
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Инициализирует машину действий.

        Аргументы:
            context: глобальный контекст выполнения (содержит информацию
                     о пользователе, запросе и окружении).
            mode: режим выполнения (обязательный, непустой). Примеры: "production", "test", "staging".
            plugins: список экземпляров плагинов (по умолчанию пустой).
            max_concurrent_handlers: максимальное количество одновременно
                                     выполняющихся обработчиков плагинов
                                     для одного события (по умолчанию 10).
            log_coordinator: координатор логирования. Если не указан, создаётся
                             экземпляр с единственным логером ConsoleLogger(use_colors=True).

        Исключения:
            ValueError: если mode пустая строка.
        """
        if not mode:
            raise ValueError("mode must be non-empty")
        self._mode = mode
        self._context = context

        # Координатор плагинов
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
            max_concurrent_handlers=max_concurrent_handlers,
        )

        # Координатор логирования
        if log_coordinator is None:
            log_coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
        self._log_coordinator = log_coordinator

        # Кеш аспектов
        self._aspect_cache: dict[type[Any], tuple[list[tuple[AspectMethod, str]], AspectMethod]] = {}

        # Кеш фабрик зависимостей
        self._factory_cache: dict[type[Any], DependencyFactory] = {}

        # Уровень вложенности
        self._nest_level: int = 0

    # ---------- Вспомогательные методы для аспектов ----------

    def _get_aspects(self, action_class: type[Any]) -> tuple[list[tuple[AspectMethod, str]], AspectMethod]:
        """Возвращает (список обычных аспектов, summary-аспект) для класса действия. Использует кэш."""
        if action_class not in self._aspect_cache:
            aspects, summary = self._collect_aspects(action_class)
            self._aspect_cache[action_class] = (aspects, summary)
        return self._aspect_cache[action_class]

    def _process_method_for_aspect(
        self, method: Any, aspects: list[tuple[AspectMethod, str]], summary_method: AspectMethod | None
    ) -> tuple[list[tuple[AspectMethod, str]], AspectMethod | None]:
        """Обрабатывает один метод класса: если это аспект, добавляет его в соответствующий список."""
        if not hasattr(method, "_is_aspect") or not method._is_aspect:
            return aspects, summary_method

        asp_method = cast(AspectMethod, method)
        if asp_method._aspect_type == "regular":
            aspects.append((asp_method, asp_method._aspect_description))
        elif asp_method._aspect_type == "summary":
            if summary_method is not None:
                raise TypeError("Класс имеет более одного summary_aspect")
            summary_method = asp_method
        else:
            raise TypeError(f"Неизвестный тип аспекта: {asp_method._aspect_type}")
        return aspects, summary_method

    def _collect_aspects(self, action_class: type[Any]) -> tuple[list[tuple[AspectMethod, str]], AspectMethod]:
        """Собирает аспекты из класса действия (только определённые непосредственно в классе)."""
        aspects: list[tuple[AspectMethod, str]] = []
        summary_method: AspectMethod | None = None

        for _, method in inspect.getmembers(action_class, predicate=inspect.isfunction):
            if method.__qualname__.split(".")[0] != action_class.__name__:
                continue
            aspects, summary_method = self._process_method_for_aspect(method, aspects, summary_method)

        if summary_method is None:
            raise TypeError(f"Класс {action_class.__name__} не имеет summary_aspect")

        aspects.sort(key=lambda item: item[0].__code__.co_firstlineno)
        return aspects, summary_method

    def _get_factory(
        self, action_class: type[Any], external_resources: dict[type[Any], Any] | None = None
    ) -> DependencyFactory:
        """Возвращает (и кэширует) фабрику зависимостей для класса действия."""
        if external_resources is not None:
            deps_info = getattr(action_class, "_dependencies", [])
            return DependencyFactory(self, deps_info, external_resources)
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, "_dependencies", [])
            self._factory_cache[action_class] = DependencyFactory(self, deps_info, external_resources=None)
        return self._factory_cache[action_class]

    def _apply_checkers(
        self,
        method: Callable[..., Any],
        result: dict[str, Any],
    ) -> None:
        """Применяет чекеры, привязанные к методу, к словарю result."""
        checkers = getattr(method, "_result_checkers", [])
        for checker in checkers:
            checker.check(result)

    # ---------- Проверка ролей ----------

    def _check_none_role(self, user_roles: list[str]) -> bool:
        """Проверка для CheckRoles.NONE (всегда разрешено)."""
        return True

    def _check_any_role(self, user_roles: list[str]) -> bool:
        """Проверка для CheckRoles.ANY (требуется хотя бы одна роль)."""
        if not user_roles:
            raise AuthorizationError("Требуется аутентификация: пользователь должен иметь хотя бы одну роль")
        return True

    def _check_list_role(self, spec: list[str], user_roles: list[str]) -> bool:
        """Проверка для списка ролей (пересечение)."""
        if any(role in user_roles for role in spec):
            return True
        raise AuthorizationError(
            f"Доступ запрещён. Требуется одна из ролей: {spec}, роли пользователя: {user_roles}"
        )

    def _check_single_role(self, spec: str, user_roles: list[str]) -> bool:
        """Проверка для одной конкретной роли."""
        if spec in user_roles:
            return True
        raise AuthorizationError(f"Доступ запрещён. Требуется роль: '{spec}', роли пользователя: {user_roles}")

    def _check_action_roles(self, action: BaseAction[P, R]) -> None:
        """
        Проверяет, что действие имеет ролевую спецификацию (декоратор CheckRoles)
        и что текущий пользователь из контекста её удовлетворяет.

        Исключения:
            TypeError: если у действия нет атрибута _role_spec.
            AuthorizationException: если роли пользователя не соответствуют требованиям.
        """
        role_spec = getattr(action.__class__, "_role_spec", None)
        if role_spec is None:
            raise TypeError(
                f"Действие {action.__class__.__name__} не имеет декоратора "
                "CheckRoles. Укажите явно CheckRoles.NONE если действие "
                "доступно без аутентификации."
            )
        user_roles = self._context.user.roles

        if role_spec == CheckRoles.NONE:
            self._check_none_role(user_roles)
        elif role_spec == CheckRoles.ANY:
            self._check_any_role(user_roles)
        elif isinstance(role_spec, list):
            self._check_list_role(role_spec, user_roles)
        else:
            self._check_single_role(role_spec, user_roles)

    # ---------- Проверка connections ----------
    # (без изменений, опущена для краткости, но в итоговом файле должна присутствовать полностью)
    # Здесь необходимо вставить полные методы _get_declared_connection_keys и четыре валидатора.
    # В целях экономии места я покажу их кратко, но в реальном ответе нужно дать полный код.

    @staticmethod
    def _get_declared_connection_keys(action: BaseAction[P, R]) -> set[str]:
        declared: list[dict[str, Any]] = getattr(action.__class__, "_connections", [])
        return {info["key"] for info in declared}

    @staticmethod
    def _validate_no_declarations_but_got_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        if not declared_keys and actual_keys:
            return (f"Действие {action_name} не объявляет @connection, "
                    f"но получило connections с ключами: {actual_keys}. "
                    f"Уберите connections из вызова или добавьте декоратор @connection.")
        return None

    @staticmethod
    def _validate_has_declarations_but_no_connections(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        if declared_keys and not actual_keys:
            return (f"Действие {action_name} объявляет connections: {declared_keys}, "
                    f"но connections не переданы (None или пустой словарь). "
                    f"Передайте connections с ключами: {declared_keys}.")
        return None

    @staticmethod
    def _validate_extra_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        extra = actual_keys - declared_keys
        if extra:
            return (f"Действие {action_name} получило лишние connections: {extra}. "
                    f"Объявлены только: {declared_keys}. Уберите лишние ключи.")
        return None

    @staticmethod
    def _validate_missing_connection_keys(
        action_name: str, declared_keys: set[str], actual_keys: set[str]
    ) -> str | None:
        missing = declared_keys - actual_keys
        if missing:
            return (f"Действие {action_name} не получило connections: {missing}. "
                    f"Объявлены: {declared_keys}, переданы: {actual_keys}.")
        return None

    def _check_connections(
        self, action: BaseAction[P, R], connections: dict[str, BaseResourceManager] | None
    ) -> dict[str, BaseResourceManager]:
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

    # ---------- Основной асинхронный метод run ----------

    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Асинхронно запускает выполнение действия с учётом плагинов и вложенности.

        Последовательность выполнения:
            1. Увеличение уровня вложенности.
            2. Проверка ролей (декоратор CheckRoles).
            3. Проверка connections (декоратор @connection).
            4. Событие global_start (плагины через PluginCoordinator).
            5. Выполнение регулярных аспектов (с вызовом before/after).
            6. Выполнение summary-аспекта.
            7. Событие global_finish с общей длительностью.
            8. Уменьшение уровня вложенности.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            resources: словарь внешних ресурсов (передаётся в фабрику).
            connections: словарь ресурсных менеджеров (соединений).
        """
        self._nest_level += 1
        start_time = time.time()

        try:
            self._check_action_roles(action)
            conns = self._check_connections(action, connections)
            factory = self._get_factory(action.__class__, external_resources=resources)

            await self._plugin_coordinator.emit_event(
                event_name="global_start",
                action=action,
                params=params,
                state_aspect=None,
                is_summary=False,
                result=None,
                duration=None,
                factory=factory,
                context=self._context,
                nest_level=self._nest_level,
            )

            state = await self._execute_regular_aspects(action, params, factory, conns)

            _, summary_method = self._get_aspects(action.__class__)
            result = await self._call_aspect(summary_method, action, params, state, factory, conns)

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
                context=self._context,
                nest_level=self._nest_level,
            )

            return cast(R, result)
        finally:
            self._nest_level -= 1

    async def _call_aspect(
        self,
        method: AspectMethod,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        factory: DependencyFactory,
        connections: dict[str, BaseResourceManager],
    ) -> Any:
        """
        Вызывает аспект (метод). Все аспекты асинхронны.
        Все аспекты обязаны принимать параметр `log` (шестой).
        Создаёт привязанный логер ActionBoundLogger и передаёт его.

        Параметр connections передаётся в каждый аспект как последний
        аргумент, позволяя аспектам выполнять запросы через ресурсные
        менеджеры и решать, какие соединения передать в дочерние действия.

        Возвращает результат выполнения аспекта.
        """
        log = ActionBoundLogger(
            coordinator=self._log_coordinator,
            nest_level=self._nest_level,
            machine_name=self.__class__.__name__,
            mode=self._mode,
            action_name=action.get_full_class_name(),
            aspect_name=method.__name__,
            context=self._context,
        )
        return await method(action, params, state, factory, connections, log)

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        factory: DependencyFactory,
        connections: dict[str, BaseResourceManager],
    ) -> BaseState:
        """
        Асинхронно выполняет цепочку регулярных аспектов, вызывая
        для каждого before и after события плагинов через координатор.

        Для каждого аспекта:
            - вызывается before-событие плагинов,
            - выполняется сам аспект,
            - проверяется результат через чекеры,
            - вызывается after-событие плагинов с длительностью.

        Параметр connections прокидывается в каждый аспект.
        """
        action_class = action.__class__
        aspects, _ = self._get_aspects(action_class)
        state = BaseState()

        for method, description in aspects:
            aspect_name = method.__name__

            await self._plugin_coordinator.emit_event(
                event_name=f"before:{aspect_name}",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=method._aspect_type == "summary",
                result=None,
                duration=None,
                factory=factory,
                context=self._context,
                nest_level=self._nest_level,
            )

            aspect_start = time.time()
            new_state_dict = await self._call_aspect(method, action, params, state, factory, connections)
            if not isinstance(new_state_dict, dict):
                raise TypeError(
                    f"Аспект {method.__qualname__} должен возвращать dict, получен {type(new_state_dict).__name__}"
                )

            checkers = getattr(method, "_result_checkers", [])

            if not checkers and new_state_dict:
                raise ValidationFieldError(
                    f"Аспект {method.__qualname__} не имеет чекеров, "
                    f"но вернул непустой state: {new_state_dict}. "
                    f"Либо добавьте чекеры для всех полей, либо возвращайте пустой словарь."
                )

            if checkers:
                allowed_fields = {ch.field_name for ch in checkers}
                extra_fields = set(new_state_dict.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldError(
                        f"Аспект {method.__qualname__} вернул лишние поля: "
                        f"{extra_fields}. Разрешены только: {allowed_fields}"
                    )
                self._apply_checkers(method, new_state_dict)

            state = BaseState(new_state_dict)

            aspect_duration = time.time() - aspect_start

            await self._plugin_coordinator.emit_event(
                event_name=f"after:{aspect_name}",
                action=action,
                params=params,
                state_aspect=state.to_dict(),
                is_summary=method._aspect_type == "summary",
                result=None,
                duration=aspect_duration,
                factory=factory,
                context=self._context,
                nest_level=self._nest_level,
            )

        return state