# ActionMachine/Core/ActionProductMachine.py
"""
Реализация продуктовой машины действий с поддержкой плагинов и вложенности.
"""

import asyncio
import time
from typing import TypeVar, Any, Dict, List, Optional, Tuple, Type, cast, Callable
import inspect

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
    def __init__(
        self,
        context: Context,
        plugins: Optional[List[Plugin]] = None,
        max_concurrent_handlers: int = DEFAULT_MAX_CONCURRENT_HANDLERS,
    ) -> None:
        self._context = context
        self._plugins: List[Plugin] = plugins or []
        self._max_concurrent_handlers = max_concurrent_handlers
        self._aspect_cache: Dict[Type[Any], Tuple[List[Tuple[AspectMethod, str]], AspectMethod]] = {}
        self._factory_cache: Dict[Type[Any], DependencyFactory] = {}
        self._plugin_cache: Dict[Tuple[str, str], List[Tuple[Callable[..., Any], bool]]] = {}
        self._plugin_states: Dict[int, Any] = {}
        self._nest_level: int = 0

    # ---------- Вспомогательные методы для аспектов ----------
    def _get_aspects(self, action_class: Type[Any]) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        if action_class not in self._aspect_cache:
            aspects, summary = self._collect_aspects(action_class)
            self._aspect_cache[action_class] = (aspects, summary)
        return self._aspect_cache[action_class]

    def _collect_aspects(self, action_class: Type[Any]) -> Tuple[List[Tuple[AspectMethod, str]], AspectMethod]:
        aspects: List[Tuple[AspectMethod, str]] = []
        summary_method: Optional[AspectMethod] = None

        for name, method in inspect.getmembers(action_class, predicate=inspect.isfunction):
            if method.__qualname__.split('.')[0] != action_class.__name__:
                continue
            if not hasattr(method, '_is_aspect') or not method._is_aspect:
                continue

            asp_method = cast(AspectMethod, method)
            if asp_method._aspect_type == 'regular':
                aspects.append((asp_method, asp_method._aspect_description))
            elif asp_method._aspect_type == 'summary':
                if summary_method is not None:
                    raise TypeError(f"Класс {action_class.__name__} имеет более одного summary_aspect")
                summary_method = asp_method
            else:
                raise TypeError(f"Неизвестный тип аспекта: {asp_method._aspect_type}")

        if summary_method is None:
            raise TypeError(f"Класс {action_class.__name__} не имеет summary_aspect")

        aspects.sort(key=lambda item: item[0].__code__.co_firstlineno)
        return aspects, summary_method

    def _get_factory(self, action_class: Type[Any]) -> DependencyFactory:
        if action_class not in self._factory_cache:
            deps_info = getattr(action_class, '_dependencies', [])
            self._factory_cache[action_class] = DependencyFactory(self, deps_info)
        return self._factory_cache[action_class]

    def _apply_checkers(self, method: Callable[..., Any], result: Dict[str, Any]) -> None:
        checkers = getattr(method, '_result_checkers', [])
        for checker in checkers:
            checker.check(result)

    def _check_action_roles(self, action: BaseAction[P, R]) -> None:
        role_spec = getattr(action.__class__, '_role_spec', None)
        if role_spec is None:
            raise TypeError(
                f"Действие {action.__class__.__name__} не имеет декоратора CheckRoles. "
                "Укажите явно CheckRoles.NONE если действие доступно без аутентификации."
            )
        user_roles = self._context.user.roles

        if role_spec == CheckRoles.NONE:
            return
        if role_spec == CheckRoles.ANY:
            if not user_roles:
                raise AuthorizationException("Требуется аутентификация: пользователь должен иметь хотя бы одну роль")
            return
        if isinstance(role_spec, list):
            if any(role in user_roles for role in role_spec):
                return
            raise AuthorizationException(
                f"Доступ запрещён. Требуется одна из ролей: {role_spec}, роли пользователя: {user_roles}"
            )
        if role_spec in user_roles:
            return
        raise AuthorizationException(
            f"Доступ запрещён. Требуется роль: '{role_spec}', роли пользователя: {user_roles}"
        )

    # ---------- Методы для работы с плагинами ----------
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

        for plugin in self._plugins:
            plugin_id = id(plugin)
            if plugin_id not in self._plugin_states:
                self._plugin_states[plugin_id] = plugin.get_initial_state()

        semaphore = asyncio.Semaphore(self._max_concurrent_handlers)

        async def run_one(handler: Callable[..., Any], ignore: bool, plugin: Plugin) -> None:
            async with semaphore:
                plugin_id = id(plugin)
                state = self._plugin_states[plugin_id]
                try:
                    new_state = await handler(
                        state_plugin=state,
                        event_name=event_name,
                        action_name=action_name,
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

        tasks = []
        for handler, ignore in handlers:
            for plugin in self._plugins:
                if hasattr(handler, '__self__') and handler.__self__ is plugin:
                    tasks.append(run_one(handler, ignore, plugin))
                    break
        await asyncio.gather(*tasks)

    # ---------- Основной метод run ----------
    def run(self, action: BaseAction[P, R], params: P) -> R:
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

            self._apply_checkers(method, new_state)

            checkers = getattr(method, '_result_checkers', [])
            if checkers:
                allowed_fields = {ch.field_name for ch in checkers}
                extra_fields = set(new_state.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldException(
                        f"Аспект {method.__qualname__} вернул лишние поля: {extra_fields}. "
                        f"Разрешены только: {allowed_fields}"
                    )

            aspect_duration = time.time() - aspect_start
            self._run_plugins_sync(
                f'after:{aspect_name}', action, params, new_state,
                method._aspect_type == 'summary', None, aspect_duration,
            )

            state = new_state

        return state