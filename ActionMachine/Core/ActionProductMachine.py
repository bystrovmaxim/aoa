# ActionMachine/Core/ActionProductMachine.py

"""
Реализация продуктовой машины действий с поддержкой плагинов и вложенности.
Полностью асинхронная версия. Использует PluginEvent для передачи данных в плагины.

Архитектурные решения:
    - Логика управления плагинами (инициализация состояний, кеширование
      обработчиков, асинхронный запуск с семафором) вынесена в отдельный
      класс PluginCoordinator (ActionMachine/Plugins/PluginCoordinator.py).
    - ActionProductMachine делегирует все вызовы плагинов через
      self._plugin_coordinator.emit_event(...).
    - Метод _check_connections разбит на 4 приватных валидатора,
      каждый из которых проверяет одно конкретное правило соответствия
      переданных connections объявленным через @connection.

Публичный API класса остался неизменным.
"""

import time
import inspect
from typing import TypeVar, Any, Dict, List, Optional, Tuple, Type, cast, Callable

from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.DependencyFactory import DependencyFactory
from ActionMachine.Context.Context import Context
from ActionMachine.Core.AspectMethod import AspectMethod
from ActionMachine.Core.BaseActionMachine import BaseActionMachine
from ActionMachine.Core.Exceptions import (
    ValidationFieldException,
    AuthorizationException,
    ConnectionValidationError,
)
from ActionMachine.Auth.CheckRoles import CheckRoles
from ActionMachine.Plugins.Plugin import Plugin
from ActionMachine.Plugins.PluginCoordinator import PluginCoordinator
from ActionMachine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)

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
    """

    def __init__(
        self,
        context: Context,
        plugins: Optional[List[Plugin]] = None,
        max_concurrent_handlers: int = DEFAULT_MAX_CONCURRENT_HANDLERS,
    ) -> None:
        """
        Инициализирует машину действий.

        Аргументы:
            context: глобальный контекст выполнения (содержит информацию
                     о пользователе, запросе и окружении).
            plugins: список экземпляров плагинов (по умолчанию пустой).
            max_concurrent_handlers: максимальное количество одновременно
                                     выполняющихся обработчиков плагинов
                                     для одного события (по умолчанию 10).
        """
        self._context = context

        # Координатор плагинов — выделенный класс для управления
        # жизненным циклом плагинов (инициализация состояний,
        # кеширование обработчиков, запуск с семафором).
        # Создаётся всегда, даже если список плагинов пуст —
        # emit_event корректно обрабатывает пустой список (ранний возврат).
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
            max_concurrent_handlers=max_concurrent_handlers,
        )

        # Кеш аспектов: класс действия → (regular_aspects, summary_aspect)
        # Заполняется лениво при первом вызове _get_aspects.
        self._aspect_cache: Dict[
            Type[Any],
            Tuple[List[Tuple[AspectMethod, str]], AspectMethod]
        ] = {}

        # Кеш фабрик зависимостей: класс действия → DependencyFactory
        # Используется только для действий без external_resources.
        self._factory_cache: Dict[Type[Any], DependencyFactory] = {}

        # Уровень вложенности вызовов действий.
        # Увеличивается при каждом вызове run(), уменьшается при выходе.
        # Передаётся в PluginEvent для информирования плагинов.
        self._nest_level: int = 0

    # ---------- Вспомогательные методы для аспектов ----------

    def _get_aspects(
        self, action_class: Type[Any]
    ) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        """
        Возвращает (список обычных аспектов, summary-аспект) для класса действия.
        Использует кэш.
        """
        if action_class not in self._aspect_cache:
            aspects, summary = self._collect_aspects(action_class)
            self._aspect_cache[action_class] = (aspects, summary)
        return self._aspect_cache[action_class]

    def _process_method_for_aspect(
        self,
        method: Any,
        aspects: List[Tuple[AspectMethod, str]],
        summary_method: Optional[AspectMethod]
    ) -> Tuple[List[Tuple[AspectMethod, str]], Optional[AspectMethod]]:
        """
        Обрабатывает один метод класса: если это аспект, добавляет его
        в соответствующий список.

        Аргументы:
            method: метод класса.
            aspects: текущий список регулярных аспектов.
            summary_method: текущий summary-аспект (если найден).

        Возвращает:
            Обновлённые (aspects, summary_method).
        """
        if not hasattr(method, '_is_aspect') or not method._is_aspect:
            return aspects, summary_method

        asp_method = cast(AspectMethod, method)
        if asp_method._aspect_type == 'regular':
            aspects.append((asp_method, asp_method._aspect_description))
        elif asp_method._aspect_type == 'summary':
            if summary_method is not None:
                raise TypeError("Класс имеет более одного summary_aspect")
            summary_method = asp_method
        else:
            raise TypeError(
                f"Неизвестный тип аспекта: {asp_method._aspect_type}"
            )
        return aspects, summary_method

    def _collect_aspects(
        self, action_class: Type[Any]
    ) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        """
        Собирает аспекты из класса действия.

        Оставляет только методы, определённые непосредственно в этом классе
        (не унаследованные), и имеющие атрибуты _is_aspect,
        _aspect_description, _aspect_type.

        Возвращает:
            Отсортированный по номеру строки список регулярных аспектов
            и summary-аспект.
        """
        aspects: List[Tuple[AspectMethod, str]] = []
        summary_method: Optional[AspectMethod] = None

        for _, method in inspect.getmembers(
            action_class, predicate=inspect.isfunction
        ):
            # Игнорируем унаследованные методы (сознательное решение)
            if method.__qualname__.split('.')[0] != action_class.__name__:
                continue
            aspects, summary_method = self._process_method_for_aspect(
                method, aspects, summary_method
            )

        if summary_method is None:
            raise TypeError(
                f"Класс {action_class.__name__} не имеет summary_aspect"
            )

        aspects.sort(key=lambda item: item[0].__code__.co_firstlineno)
        return aspects, summary_method

    def _get_factory(
        self,
        action_class: Type[Any],
        external_resources: Optional[Dict[Type[Any], Any]] = None
    ) -> DependencyFactory:
        """
        Возвращает (и кэширует) фабрику зависимостей для класса действия.

        При наличии external_resources создаёт фабрику с ними
        (кэш игнорируется, так как они могут меняться).
        """
        if external_resources is not None:
            deps_info = getattr(action_class, '_dependencies', [])
            return DependencyFactory(
                self, deps_info, external_resources
            )
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, '_dependencies', [])
            self._factory_cache[action_class] = DependencyFactory(
                self, deps_info, external_resources=None
            )
        return self._factory_cache[action_class]

    def _apply_checkers(
        self,
        method: Callable[..., Any],
        result: Dict[str, Any],
    ) -> None:
        """
        Применяет чекеры, привязанные к методу, к словарю result.
        """
        checkers = getattr(method, '_result_checkers', [])
        for checker in checkers:
            checker.check(result)

    # ---------- Проверка ролей ----------

    def _check_none_role(self, user_roles: List[str]) -> bool:
        """Проверка для CheckRoles.NONE (всегда разрешено)."""
        return True

    def _check_any_role(self, user_roles: List[str]) -> bool:
        """Проверка для CheckRoles.ANY (требуется хотя бы одна роль)."""
        if not user_roles:
            raise AuthorizationException(
                "Требуется аутентификация: пользователь должен "
                "иметь хотя бы одну роль"
            )
        return True

    def _check_list_role(
        self, spec: List[str], user_roles: List[str]
    ) -> bool:
        """Проверка для списка ролей (пересечение)."""
        if any(role in user_roles for role in spec):
            return True
        raise AuthorizationException(
            f"Доступ запрещён. Требуется одна из ролей: {spec}, "
            f"роли пользователя: {user_roles}"
        )

    def _check_single_role(
        self, spec: str, user_roles: List[str]
    ) -> bool:
        """Проверка для одной конкретной роли."""
        if spec in user_roles:
            return True
        raise AuthorizationException(
            f"Доступ запрещён. Требуется роль: '{spec}', "
            f"роли пользователя: {user_roles}"
        )

    def _check_action_roles(self, action: BaseAction[P, R]) -> None:
        """
        Проверяет, что действие имеет ролевую спецификацию (декоратор CheckRoles)
        и что текущий пользователь из контекста её удовлетворяет.

        Исключения:
            TypeError: если у действия нет атрибута _role_spec.
            AuthorizationException: если роли пользователя не соответствуют
                                    требованиям.
        """
        role_spec = getattr(action.__class__, '_role_spec', None)
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
    #
    # Метод _check_connections разбит на 4 приватных валидатора,
    # каждый из которых возвращает Optional[str] с сообщением об ошибке.

    @staticmethod
    def _get_declared_connection_keys(
        action: BaseAction[P, R],
    ) -> set[str]:
        """
        Извлекает множество ключей, объявленных через декоратор @connection
        на классе действия.
        """
        declared: List[Dict[str, Any]] = getattr(
            action.__class__, '_connections', []
        )
        return {info['key'] for info in declared}

    @staticmethod
    def _validate_no_declarations_but_got_connections(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> Optional[str]:
        """
        Правило 1: у действия нет @connection, но передали непустой connections.
        """
        if not declared_keys and actual_keys:
            return (
                f"Действие {action_name} не объявляет @connection, "
                f"но получило connections с ключами: {actual_keys}. "
                f"Уберите connections из вызова или добавьте "
                f"декоратор @connection."
            )
        return None

    @staticmethod
    def _validate_has_declarations_but_no_connections(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> Optional[str]:
        """
        Правило 2: у действия есть @connection, но connections не передан.
        """
        if declared_keys and not actual_keys:
            return (
                f"Действие {action_name} объявляет connections: "
                f"{declared_keys}, но connections не переданы "
                f"(None или пустой словарь). "
                f"Передайте connections с ключами: {declared_keys}."
            )
        return None

    @staticmethod
    def _validate_extra_connection_keys(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> Optional[str]:
        """
        Правило 3: в connections есть ключи, не объявленные через @connection.
        """
        extra = actual_keys - declared_keys
        if extra:
            return (
                f"Действие {action_name} получило лишние "
                f"connections: {extra}. "
                f"Объявлены только: {declared_keys}. Уберите лишние ключи."
            )
        return None

    @staticmethod
    def _validate_missing_connection_keys(
        action_name: str,
        declared_keys: set[str],
        actual_keys: set[str],
    ) -> Optional[str]:
        """
        Правило 4: в connections отсутствуют ключи, объявленные через @connection.
        """
        missing = declared_keys - actual_keys
        if missing:
            return (
                f"Действие {action_name} не получило "
                f"connections: {missing}. "
                f"Объявлены: {declared_keys}, переданы: {actual_keys}."
            )
        return None

    def _check_connections(
        self,
        action: BaseAction[P, R],
        connections: Optional[Dict[str, BaseResourceManager]],
    ) -> Dict[str, BaseResourceManager]:
        """
        Проверяет соответствие переданных connections объявленным
        через @connection. Последовательно вызывает 4 валидатора.

        Возвращает:
            Валидный словарь connections (пустой dict если не объявлено
            и не передано).

        Исключения:
            ConnectionValidationError: при несоответствии.
        """
        declared_keys = self._get_declared_connection_keys(action)
        actual_keys = set(connections.keys()) if connections else set()
        action_name = action.__class__.__name__

        validators: List[Optional[str]] = [
            self._validate_no_declarations_but_got_connections(
                action_name, declared_keys, actual_keys,
            ),
            self._validate_has_declarations_but_no_connections(
                action_name, declared_keys, actual_keys,
            ),
            self._validate_extra_connection_keys(
                action_name, declared_keys, actual_keys,
            ),
            self._validate_missing_connection_keys(
                action_name, declared_keys, actual_keys,
            ),
        ]

        for error_message in validators:
            if error_message is not None:
                raise ConnectionValidationError(error_message)

        return connections or {}

    # ---------- Основной асинхронный метод run ----------

    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        resources: Optional[Dict[Type[Any], Any]] = None,
        connections: Optional[Dict[str, BaseResourceManager]] = None,
    ) -> R:
        """
        Асинхронно запускает выполнение действия с учётом плагинов
        и вложенности.

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

            # Проверяем соответствие connections и @connection деклараций
            conns = self._check_connections(action, connections)

            # Создаём фабрику с учётом внешних ресурсов
            factory = self._get_factory(
                action.__class__, external_resources=resources
            )

            # Событие global_start — делегируем координатору плагинов
            await self._plugin_coordinator.emit_event(
                'global_start', action, params, None, False,
                None, None, factory, self._context, self._nest_level,
            )

            state = await self._execute_regular_aspects(
                action, params, factory, conns
            )

            _, summary_method = self._get_aspects(action.__class__)
            result = await self._call_aspect(
                summary_method, action, params, state, factory, conns
            )

            total_duration = time.time() - start_time

            # Событие global_finish — делегируем координатору плагинов
            await self._plugin_coordinator.emit_event(
                'global_finish', action, params, None, False,
                result, total_duration, factory,
                self._context, self._nest_level,
            )

            return cast(R, result)
        finally:
            self._nest_level -= 1

    async def _call_aspect(
        self,
        method: AspectMethod,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: dict[str, object],
        factory: DependencyFactory,
        connections: Dict[str, BaseResourceManager],
    ) -> Any:
        """
        Вызывает аспект (метод). Все аспекты асинхронны
        (гарантируется декораторами), поэтому всегда используем await.

        Параметр connections передаётся в каждый аспект как последний
        аргумент, позволяя аспектам выполнять запросы через ресурсные
        менеджеры и решать, какие соединения передать в дочерние действия.

        Возвращает результат выполнения аспекта.
        """
        return await method(action, params, state, factory, connections)

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        factory: DependencyFactory,
        connections: Dict[str, BaseResourceManager],
    ) -> dict[str, object]:
        """
        Асинхронно выполняет цепочку регулярных аспектов, вызывая
        для каждого before и after события плагинов через координатор.

        Для каждого аспекта:
            - вызывается before-событие плагинов (через PluginCoordinator),
            - выполняется сам аспект,
            - проверяется результат через чекеры,
            - вызывается after-событие плагинов с длительностью.

        Параметр connections прокидывается в каждый аспект.
        """
        action_class = action.__class__
        aspects, _ = self._get_aspects(action_class)
        state: dict[str, object] = {}

        for method, description in aspects:
            aspect_name = method.__name__

            # before-событие — делегируем координатору плагинов
            await self._plugin_coordinator.emit_event(
                f'before:{aspect_name}', action, params, state,
                method._aspect_type == 'summary', None, None,
                factory, self._context, self._nest_level,
            )

            aspect_start = time.time()
            new_state = await self._call_aspect(
                method, action, params, state, factory, connections
            )
            if not isinstance(new_state, dict):
                raise TypeError(
                    f"Аспект {method.__qualname__} должен возвращать dict, "
                    f"получен {type(new_state).__name__}"
                )

            checkers = getattr(method, '_result_checkers', [])

            if not checkers and new_state:
                raise ValidationFieldException(
                    f"Аспект {method.__qualname__} не имеет чекеров, "
                    f"но вернул непустой state: {new_state}. "
                    f"Либо добавьте чекеры для всех полей, "
                    f"либо возвращайте пустой словарь."
                )

            if checkers:
                allowed_fields = {ch.field_name for ch in checkers}
                extra_fields = set(new_state.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldException(
                        f"Аспект {method.__qualname__} вернул лишние поля: "
                        f"{extra_fields}. "
                        f"Разрешены только: {allowed_fields}"
                    )
                self._apply_checkers(method, new_state)

            aspect_duration = time.time() - aspect_start

            # after-событие — делегируем координатору плагинов
            await self._plugin_coordinator.emit_event(
                f'after:{aspect_name}', action, params, new_state,
                method._aspect_type == 'summary', None, aspect_duration,
                factory, self._context, self._nest_level,
            )

            state = new_state

        return state
