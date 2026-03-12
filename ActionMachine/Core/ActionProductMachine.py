# ActionMachine/Core/ActionProductMachine.py
"""
Реализация продуктовой машины действий с поддержкой плагинов и вложенности.
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
from ActionMachine.Core.Exceptions import ValidationFieldException, AuthorizationException
from ActionMachine.Auth.CheckRoles import CheckRoles
from ActionMachine.Plugins.Plugin import Plugin

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)

DEFAULT_MAX_CONCURRENT_HANDLERS = 10


class ActionProductMachine(BaseActionMachine):
    """
    Продуктовая реализация машины действий.

    Содержит логику кэширования аспектов и фабрик зависимостей,
    выполняет проверку ролей, валидацию результатов аспектов через чекеры,
    а также поддерживает подключение плагинов для расширения функциональности.

    Атрибуты:
        _context: глобальный контекст выполнения.
        _plugins: список экземпляров плагинов.
        _max_concurrent_handlers: максимальное количество одновременно выполняющихся
            обработчиков плагинов для одного события.
        _aspect_cache: кэш для списков аспектов классов действий.
        _factory_cache: кэш для фабрик зависимостей классов действий.
        _plugin_cache: кэш для списков обработчиков плагинов для пар (событие, класс).
        _plugin_states: хранилище текущих состояний плагинов для выполняемого действия.
        _nest_level: текущий уровень вложенности (0 для верхнего уровня).
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
                raise TypeError(f"Класс имеет более одного summary_aspect")
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

    def _get_factory(self, action_class: Type[Any]) -> DependencyFactory:
        """
        Возвращает (и кэширует) фабрику зависимостей для класса действия.
        """
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, '_dependencies', [])
            self._factory_cache[action_class] = DependencyFactory(self, deps_info)
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
        """Проверка для CheckRoles.NONE."""
        return True

    def _check_any_role(self, user_roles: List[str]) -> bool:
        """Проверка для CheckRoles.ANY."""
        if not user_roles:
            raise AuthorizationException(
                "Требуется аутентификация: пользователь должен иметь хотя бы одну роль"
            )
        return True

    def _check_list_role(self, spec: List[str], user_roles: List[str]) -> bool:
        """Проверка для списка ролей."""
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

    # ---------- Методы для работы с плагинами (синхронная обёртка) ----------

    def _run_plugins_sync(
        self,
        event_name: str,
        action: BaseAction[P, R],
        params: P,
        state_aspect: Optional[Dict[str, Any]],
        is_summary: bool,
        result: Optional[BaseResult],
        duration: Optional[float],
    ) -> None:
        """
        Синхронная обёртка для запуска асинхронных обработчиков плагинов.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self._run_plugins_async(
                event_name, action, params, state_aspect, is_summary, result, duration
            ))
        else:
            loop.run_until_complete(self._run_plugins_async(
                event_name, action, params, state_aspect, is_summary, result, duration
            ))

    # ---------- Вспомогательные методы для асинхронного запуска плагинов ----------

    async def _init_plugin_states(self) -> None:
        """Инициализирует состояния всех плагинов для текущего запуска."""
        for plugin in self._plugins:
            plugin_id = id(plugin)
            if plugin_id not in self._plugin_states:
                self._plugin_states[plugin_id] = plugin.get_initial_state()

    async def _run_single_handler(
        self,
        handler: Callable[..., Any],
        ignore: bool,
        plugin: Plugin,
        event_name: str,
        action: BaseAction[P, R],
        params: P,
        state_aspect: Optional[Dict[str, Any]],
        is_summary: bool,
        result: Optional[BaseResult],
        duration: Optional[float],
    ) -> None:
        """
        Запускает один обработчик плагина, обрабатывая исключения согласно флагу ignore.
        """
        plugin_id = id(plugin)
        state = self._plugin_states[plugin_id]
        try:
            new_state = await handler(
                state_plugin=state,
                event_name=event_name,
                action_name=action.get_full_class_name(),
                params=params,
                state_aspect=state_aspect,
                is_summary=is_summary,
                deps=self._get_factory(action.__class__),
                context=self._context,
                result=result,
                duration=duration,
                nest_level=self._nest_level,
            )
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
        state_aspect: Optional[Dict[str, Any]],
        is_summary: bool,
        result: Optional[BaseResult],
        duration: Optional[float],
    ) -> None:
        """
        Асинхронно запускает все подходящие обработчики плагинов для данного события.
        """
        action_name = action.get_full_class_name()
        cache_key = (event_name, action_name)

        # Получаем обработчики из кэша или собираем
        if cache_key not in self._plugin_cache:
            handlers: List[Tuple[Callable[..., Any], bool]] = []
            for plugin in self._plugins:
                handlers.extend(plugin.get_handlers(event_name, action_name))
            self._plugin_cache[cache_key] = handlers
        else:
            handlers = self._plugin_cache[cache_key]

        if not handlers:
            return

        # Инициализируем состояния плагинов
        await self._init_plugin_states()

        semaphore = asyncio.Semaphore(self._max_concurrent_handlers)

        async def run_with_semaphore(
            handler: Callable[..., Any], ignore: bool, plugin: Plugin
        ) -> None:
            async with semaphore:
                await self._run_single_handler(
                    handler, ignore, plugin, event_name, action,
                    params, state_aspect, is_summary, result, duration
                )

        tasks = []
        for handler, ignore in handlers:
            for plugin in self._plugins:
                if hasattr(handler, '__self__') and handler.__self__ is plugin:
                    tasks.append(run_with_semaphore(handler, ignore, plugin))
                    break

        await asyncio.gather(*tasks)

    # ---------- Основной метод run ----------

    def run(self, action: BaseAction[P, R], params: P) -> R:
        """
        Синхронно запускает выполнение действия с учётом плагинов и вложенности.

        Последовательность выполнения:
            1. Увеличение уровня вложенности.
            2. Проверка ролей (декоратор CheckRoles).
            3. Событие global_start (плагины).
            4. Выполнение регулярных аспектов (с вызовом before/after для каждого).
            5. Выполнение summary-аспекта.
            6. Событие global_finish с общей длительностью.
            7. Уменьшение уровня вложенности.
        """
        self._nest_level += 1
        start_time = time.time()

        try:
            self._check_action_roles(action)
            factory = self._get_factory(action.__class__)

            self._run_plugins_sync('global_start', action, params, None, False, None, None)

            state = self._execute_regular_aspects(action, params, factory)

            _, summary_method = self._get_aspects(action.__class__)
            result = summary_method(action, params, state, factory)

            total_duration = time.time() - start_time
            self._run_plugins_sync('global_finish', action, params, None, False, result, total_duration)

            return cast(R, result)
        finally:
            self._nest_level -= 1

    def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        factory: DependencyFactory,
    ) -> Dict[str, Any]:
        """
        Синхронно выполняет цепочку регулярных аспектов, вызывая для каждого
        before и after события плагинов (асинхронно, с ожиданием).

        Для каждого аспекта:
            - вызывается before-событие плагинов,
            - выполняется сам аспект,
            - проверяется результат согласно правилам:
                * если у аспекта есть чекеры, то все поля в возвращённом state
                  должны быть описаны чекерами, и каждый чекер применяется;
                * если чекеров нет, то возвращённый state должен быть пустым;
                * в противном случае выбрасывается ValidationFieldException.
            - вызывается after-событие плагинов с длительностью выполнения аспекта.
        """
        action_class = action.__class__
        aspects, _ = self._get_aspects(action_class)
        state: Dict[str, Any] = {}

        for method, description in aspects:
            aspect_name = method.__name__

            self._run_plugins_sync(
                f'before:{aspect_name}', action, params, state,
                method._aspect_type == 'summary', None, None,
            )

            aspect_start = time.time()
            new_state = method(action, params, state, factory)
            if not isinstance(new_state, dict):
                raise TypeError(
                    f"Аспект {method.__qualname__} должен возвращать dict, "
                    f"получен {type(new_state).__name__}"
                )

            checkers = getattr(method, '_result_checkers', [])

            # Правило 1: если чекеров нет, разрешён только пустой словарь
            if not checkers and new_state:
                raise ValidationFieldException(
                    f"Аспект {method.__qualname__} не имеет чекеров, но вернул непустой state: {new_state}. "
                    f"Либо добавьте чекеры для всех полей, либо возвращайте пустой словарь."
                )

            # Правило 2: если чекеры есть, проверяем, что нет лишних ключей,
            # и применяем каждый чекер (типы, обязательность и т.д.)
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

            self._run_plugins_sync(
                f'after:{aspect_name}', action, params, new_state,
                method._aspect_type == 'summary', None, aspect_duration,
            )

            state = new_state

        return state