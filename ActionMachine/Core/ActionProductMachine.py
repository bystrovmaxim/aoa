"""
Реализация продуктовой машины действий с поддержкой плагинов и вложенности.
Полностью асинхронная версия. Использует PluginEvent для передачи данных в плагины.
"""

import asyncio
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
from ActionMachine.Plugins.PluginEvent import PluginEvent
from ActionMachine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)

DEFAULT_MAX_CONCURRENT_HANDLERS = 10


class ActionProductMachine(BaseActionMachine):
    """
    Продуктовая реализация машины действий (асинхронная).

    Содержит логику кэширования аспектов и фабрик зависимостей,
    выполняет проверку ролей, валидацию результатов аспектов через чекеры,
    проверку соответствия connections объявленным через @connection,
    а также поддерживает подключение плагинов для расширения функциональности.
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
            context: глобальный контекст выполнения (содержит информацию о пользователе,
                     запросе и окружении).
            plugins: список экземпляров плагинов (по умолчанию пустой).
            max_concurrent_handlers: максимальное количество одновременно выполняющихся
                                     обработчиков плагинов для одного события (по умолчанию 10).
        """
        self._context = context
        self._plugins: List[Plugin] = plugins or []
        self._max_concurrent_handlers = max_concurrent_handlers
        self._aspect_cache: Dict[Type[Any], Tuple[List[Tuple[AspectMethod, str]], AspectMethod]] = {}
        self._factory_cache: Dict[Type[Any], DependencyFactory] = {}
        self._plugin_cache: Dict[Tuple[str, str], List[Tuple[Callable[..., Any], bool]]] = {}
        self._plugin_states: Dict[int, Any] = {}
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
        Обрабатывает один метод класса: если это аспект, добавляет его в соответствующий список.

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
            raise TypeError(f"Неизвестный тип аспекта: {asp_method._aspect_type}")
        return aspects, summary_method

    def _collect_aspects(
        self, action_class: Type[Any]
    ) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        """
        Собирает аспекты из класса действия.

        Оставляет только методы, определённые непосредственно в этом классе (не унаследованные),
        и имеющие атрибуты _is_aspect, _aspect_description, _aspect_type.

        Возвращает:
            Отсортированный по номеру строки список регулярных аспектов и summary-аспект.
        """
        aspects: List[Tuple[AspectMethod, str]] = []
        summary_method: Optional[AspectMethod] = None

        for name, method in inspect.getmembers(action_class, predicate=inspect.isfunction):
            # Игнорируем унаследованные методы (сознательное решение)
            if method.__qualname__.split('.')[0] != action_class.__name__:
                continue
            aspects, summary_method = self._process_method_for_aspect(method, aspects, summary_method)

        if summary_method is None:
            raise TypeError(f"Класс {action_class.__name__} не имеет summary_aspect")

        aspects.sort(key=lambda item: item[0].__code__.co_firstlineno)
        return aspects, summary_method

    def _get_factory(
        self,
        action_class: Type[Any],
        external_resources: Optional[Dict[Type[Any], Any]] = None
    ) -> DependencyFactory:
        """
        Возвращает (и кэширует) фабрику зависимостей для класса действия.
        При наличии external_resources создаёт фабрику с ними (кэш игнорируется, так как они могут меняться).
        """
        if external_resources is not None:
            deps_info = getattr(action_class, '_dependencies', [])
            return DependencyFactory(self, deps_info, external_resources)
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, '_dependencies', [])
            self._factory_cache[action_class] = DependencyFactory(self, deps_info, external_resources=None)
        return self._factory_cache[action_class]

    def _apply_checkers(self, method: Callable[..., Any], result: Dict[str, Any]) -> None:
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
                "Требуется аутентификация: пользователь должен иметь хотя бы одну роль"
            )
        return True

    def _check_list_role(self, spec: List[str], user_roles: List[str]) -> bool:
        """Проверка для списка ролей (пересечение)."""
        if any(role in user_roles for role in spec):
            return True
        raise AuthorizationException(
            f"Доступ запрещён. Требуется одна из ролей: {spec}, роли пользователя: {user_roles}"
        )

    def _check_single_role(self, spec: str, user_roles: List[str]) -> bool:
        """Проверка для одной конкретной роли."""
        if spec in user_roles:
            return True
        raise AuthorizationException(
            f"Доступ запрещён. Требуется роль: '{spec}', роли пользователя: {user_roles}"
        )

    def _check_action_roles(self, action: BaseAction[P, R]) -> None:
        """
        Проверяет, что действие имеет ролевую спецификацию (декоратор CheckRoles)
        и что текущий пользователь из контекста её удовлетворяет.

        Исключения:
            TypeError: если у действия нет атрибута _role_spec.
            AuthorizationException: если роли пользователя не соответствуют требованиям.
        """
        role_spec = getattr(action.__class__, '_role_spec', None)
        if role_spec is None:
            raise TypeError(
                f"Действие {action.__class__.__name__} не имеет декоратора CheckRoles. "
                "Укажите явно CheckRoles.NONE если действие доступно без аутентификации."
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

    def _check_connections(
        self,
        action: BaseAction[P, R],
        connections: Optional[Dict[str, BaseResourceManager]],
    ) -> Dict[str, BaseResourceManager]:
        """
        Проверяет соответствие переданных connections объявленным через @connection.

        Правила:
        1. Если у действия нет @connection — connections должен быть пустым или None.
           Если передали непустой словарь — ошибка: действие не ожидает connections.
        2. Если у действия есть @connection — connections обязателен.
           Ключи в connections должны точно совпадать с объявленными ключами.
           Лишние ключи — ошибка. Недостающие ключи — ошибка.

        Аргументы:
            action: экземпляр действия.
            connections: переданный словарь connections (может быть None).

        Возвращает:
            Валидный словарь connections (пустой dict если не объявлено и не передано).

        Исключения:
            ConnectionValidationError: при несоответствии переданных connections
                                       объявленным через @connection.
        """
        # Получаем список объявленных @connection из класса действия
        declared: List[Dict[str, Any]] = getattr(action.__class__, '_connections', [])
        declared_keys = {info['key'] for info in declared}
        actual_keys = set(connections.keys()) if connections else set()

        # Правило 1: нет деклараций, но передали connections
        if not declared_keys and actual_keys:
            raise ConnectionValidationError(
                f"Действие {action.__class__.__name__} не объявляет @connection, "
                f"но получило connections с ключами: {actual_keys}. "
                f"Уберите connections из вызова или добавьте декоратор @connection."
            )

        # Правило 1 (обратное): есть декларации, но не передали
        if declared_keys and not actual_keys:
            raise ConnectionValidationError(
                f"Действие {action.__class__.__name__} объявляет connections: {declared_keys}, "
                f"но connections не переданы (None или пустой словарь). "
                f"Передайте connections с ключами: {declared_keys}."
            )

        # Правило 2: лишние ключи
        extra = actual_keys - declared_keys
        if extra:
            raise ConnectionValidationError(
                f"Действие {action.__class__.__name__} получило лишние connections: {extra}. "
                f"Объявлены только: {declared_keys}. Уберите лишние ключи."
            )

        # Правило 2: недостающие ключи
        missing = declared_keys - actual_keys
        if missing:
            raise ConnectionValidationError(
                f"Действие {action.__class__.__name__} не получило connections: {missing}. "
                f"Объявлены: {declared_keys}, переданы: {actual_keys}."
            )

        return connections or {}

    # ---------- Вспомогательные методы для запуска плагинов ----------

    async def _init_plugin_states(self) -> None:
        """
        Асинхронно инициализирует состояния всех плагинов для текущего запуска.
        Синхронный метод get_initial_state() выполняется в отдельном потоке,
        чтобы не блокировать event loop.
        """
        loop = asyncio.get_running_loop()
        for plugin in self._plugins:
            plugin_id = id(plugin)
            if plugin_id not in self._plugin_states:
                # Выполняем синхронный метод в executor
                state = await loop.run_in_executor(None, plugin.get_initial_state)
                self._plugin_states[plugin_id] = state

    async def _run_single_handler(
        self,
        handler: Callable[..., Any],
        ignore: bool,
        plugin: Plugin,
        event: PluginEvent,
    ) -> None:
        """
        Запускает один обработчик плагина, передавая ему event и ожидая новое состояние.
        """
        plugin_id = id(plugin)
        state = self._plugin_states[plugin_id]
        try:
            new_state = await handler(state, event)
            self._plugin_states[plugin_id] = new_state
        except Exception as e:
            if ignore:
                print(f"Plugin {plugin.__class__.__name__} ignored error: {e}")
            else:
                raise

    async def _run_plugins_async(
        self,
        event_name: str,
        action: BaseAction[P, R],
        params: P,
        state_aspect: Optional[dict[str, object]],
        is_summary: bool,
        result: Optional[BaseResult],
        duration: Optional[float],
        factory: DependencyFactory,
    ) -> None:
        """
        Асинхронно запускает все подходящие обработчики плагинов для данного события.
        """
        action_name = action.get_full_class_name()
        cache_key = (event_name, action_name)

        if cache_key not in self._plugin_cache:
            handlers: List[Tuple[Callable[..., Any], bool]] = []
            for plugin in self._plugins:
                handlers.extend(plugin.get_handlers(event_name, action_name))
            self._plugin_cache[cache_key] = handlers
        else:
            handlers = self._plugin_cache[cache_key]

        if not handlers:
            return

        # Инициализируем состояния плагинов асинхронно
        await self._init_plugin_states()

        event = PluginEvent(
            event_name=event_name,
            action_name=action_name,
            params=params,
            state_aspect=state_aspect,
            is_summary=is_summary,
            deps=factory,
            context=self._context,
            result=result,
            duration=duration,
            nest_level=self._nest_level,
        )

        semaphore = asyncio.Semaphore(self._max_concurrent_handlers)

        async def run_with_semaphore(
            handler: Callable[..., Any], ignore: bool, plugin: Plugin
        ) -> None:
            async with semaphore:
                await self._run_single_handler(handler, ignore, plugin, event)

        tasks = []
        for handler, ignore in handlers:
            for plugin in self._plugins:
                if hasattr(handler, '__self__') and handler.__self__ is plugin:
                    tasks.append(run_with_semaphore(handler, ignore, plugin))
                    break

        await asyncio.gather(*tasks)

    # ---------- Основной асинхронный метод run ----------

    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        resources: Optional[Dict[Type[Any], Any]] = None,
        connections: Optional[Dict[str, BaseResourceManager]] = None,
    ) -> R:
        """
        Асинхронно запускает выполнение действия с учётом плагинов и вложенности.

        Последовательность выполнения:
        1. Увеличение уровня вложенности.
        2. Проверка ролей (декоратор CheckRoles).
        3. Проверка connections (декоратор @connection).
        4. Событие global_start (плагины).
        5. Выполнение регулярных аспектов (с вызовом before/after для каждого).
        6. Выполнение summary-аспекта.
        7. Событие global_finish с общей длительностью.
        8. Уменьшение уровня вложенности.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            resources: словарь внешних ресурсов (передаётся в фабрику зависимостей).
            connections: словарь ресурсных менеджеров (соединений),
                         ключ — строковое имя (совпадает с именем в @connection),
                         значение — экземпляр BaseResourceManager.
                         Передаётся во все аспекты как есть (без оборачивания).
                         Оборачивание происходит только при передаче в дочерние действия
                         через DependencyFactory.run_action().
        """
        self._nest_level += 1
        start_time = time.time()

        try:
            self._check_action_roles(action)

            # Проверяем соответствие connections и @connection деклараций
            conns = self._check_connections(action, connections)

            # Создаём фабрику с учётом внешних ресурсов
            factory = self._get_factory(action.__class__, external_resources=resources)

            await self._run_plugins_async('global_start', action, params, None, False, None, None, factory)

            state = await self._execute_regular_aspects(action, params, factory, conns)

            _, summary_method = self._get_aspects(action.__class__)
            result = await self._call_aspect(summary_method, action, params, state, factory, conns)

            total_duration = time.time() - start_time
            await self._run_plugins_async('global_finish', action, params, None, False, result, total_duration, factory)

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
        Вызывает аспект (метод). Все аспекты асинхронны (гарантируется декораторами),
        поэтому всегда используем await.

        Параметр connections передаётся в каждый аспект как последний аргумент,
        позволяя аспектам выполнять запросы через ресурсные менеджеры
        и решать, какие соединения передать в дочерние действия.

        Возвращает результат выполнения аспекта (словарь для regular-аспектов, Result для summary).
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
        Асинхронно выполняет цепочку регулярных аспектов, вызывая для каждого
        before и after события плагинов.

        Для каждого аспекта:
        - вызывается before-событие плагинов,
        - выполняется сам аспект (с поддержкой синхронных и асинхронных методов),
        - проверяется результат согласно правилам:
          * если у аспекта есть чекеры, то все поля в возвращённом state
            должны быть описаны чекерами, и каждый чекер применяется;
          * если чекеров нет, то возвращённый state должен быть пустым;
          * в противном случае выбрасывается ValidationFieldException.
        - вызывается after-событие плагинов с длительностью выполнения аспекта.

        Параметр connections прокидывается в каждый аспект.
        """
        action_class = action.__class__
        aspects, _ = self._get_aspects(action_class)
        state: dict[str, object] = {}

        for method, description in aspects:
            aspect_name = method.__name__

            await self._run_plugins_async(
                f'before:{aspect_name}', action, params, state,
                method._aspect_type == 'summary', None, None, factory
            )

            aspect_start = time.time()
            new_state = await self._call_aspect(method, action, params, state, factory, connections)
            if not isinstance(new_state, dict):
                raise TypeError(
                    f"Аспект {method.__qualname__} должен возвращать dict, "
                    f"получен {type(new_state).__name__}"
                )

            checkers = getattr(method, '_result_checkers', [])

            if not checkers and new_state:
                raise ValidationFieldException(
                    f"Аспект {method.__qualname__} не имеет чекеров, но вернул непустой state: {new_state}. "
                    f"Либо добавьте чекеры для всех полей, либо возвращайте пустой словарь."
                )

            if checkers:
                allowed_fields = {ch.field_name for ch in checkers}
                extra_fields = set(new_state.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldException(
                        f"Аспект {method.__qualname__} вернул лишние поля: {extra_fields}. "
                        f"Разрешены только: {allowed_fields}"
                    )
                self._apply_checkers(method, new_state)

            aspect_duration = time.time() - aspect_start

            await self._run_plugins_async(
                f'after:{aspect_name}', action, params, new_state,
                method._aspect_type == 'summary', None, aspect_duration, factory
            )

            state = new_state

        return state