# src/action_machine/Plugins/PluginCoordinator.py
"""
Координатор плагинов для ActionMachine.

Отделен от ActionProductMachine для разделения зон ответственности.
ActionProductMachine управляет конвейером аспектов,
PluginCoordinator управляет жизненным циклом плагинов:

    1. Ленивая инициализация состояний плагинов (get_initial_state).
    2. Кеширование обработчиков по ключу (event_name, action_name).
    3. Асинхронное выполнение обработчиков.
    4. Обработка ignore_exceptions.

Координатор ничего не знает об аспектах, ролях и соединениях.

Изменения:
- Восстановлен сбор обработчиков через встроенный метод `plugin.get_handlers`,
  чтобы избежать циклических зависимостей со шлюзами и координатором метаданных.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_event import PluginEvent


class PluginCoordinator:
    """
    Координатор жизненного цикла плагинов.

    Управляет состояниями плагинов и маршрутизацией событий к обработчикам.
    """

    def __init__(
        self,
        plugins: list[Plugin],
    ) -> None:
        """
        Инициализирует координатор плагинов.

        Аргументы:
            plugins: список экземпляров плагинов.
        """
        self._plugins: list[Plugin] = plugins

        # Кеш: (event_name, action_name) → [(handler, ignore_exceptions, plugin)]
        self._handler_cache: dict[
            tuple[str, str],
            list[tuple[Callable[..., Any], bool, Plugin]]
        ] = {}

        # Состояния плагинов: id(plugin) → state
        self._plugin_states: dict[int, Any] = {}

    # ---------- Приватные методы ----------

    def _get_handlers(
        self,
        event_name: str,
        action_name: str,
    ) -> list[tuple[Callable[..., Any], bool, Plugin]]:
        """
        Возвращает (и кеширует) список обработчиков для данного события и действия.
        """
        cache_key = (event_name, action_name)

        if cache_key not in self._handler_cache:
            handlers: list[tuple[Callable[..., Any], bool, Plugin]] = []
            for plugin in self._plugins:
                # Используем встроенный метод плагина для поиска обработчиков
                for handler, ignore in plugin.get_handlers(event_name, action_name):
                    handlers.append((handler, ignore, plugin))
            self._handler_cache[cache_key] = handlers

        return self._handler_cache[cache_key]

    async def _init_plugin_states(self) -> None:
        """
        Асинхронно инициализирует состояния всех плагинов.
        """
        for plugin in self._plugins:
            plugin_id = id(plugin)
            if plugin_id not in self._plugin_states:
                state = await plugin.get_initial_state()
                self._plugin_states[plugin_id] = state

    async def _run_single_handler(
        self,
        handler: Callable[..., Any],
        ignore: bool,
        plugin: Plugin,
        event: PluginEvent,
    ) -> None:
        """
        Запускает один обработчик плагина.
        """
        plugin_id = id(plugin)
        state = self._plugin_states[plugin_id]
        try:
            # Передаем plugin как self, так как handler — это unbound метод класса
            new_state = await handler(plugin, state, event)
            self._plugin_states[plugin_id] = new_state
        except Exception as e:
            if ignore:
                print(f"Plugin {plugin.__class__.__name__} ignored error: {e}")
            else:
                raise

    def _find_plugin_for_handler(
        self,
        handler: Callable[..., Any],
    ) -> Plugin | None:
        """
        Находит экземпляр плагина, которому принадлежит переданный обработчик.
        (Используется в тестах).
        """
        handler_name = getattr(handler, '__name__', None)
        if handler_name is None:
            return None

        for plugin in self._plugins:
            for cls in type(plugin).__mro__:
                cls_method = cls.__dict__.get(handler_name)
                if cls_method is handler:
                    return plugin

        return None

    # ---------- Публичные методы ----------

    async def emit_event(
        self,
        event_name: str,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state_aspect: dict[str, object] | None,
        is_summary: bool,
        result: BaseResult | None,
        duration: float | None,
        factory: DependencyFactory,
        context: Context,
        nest_level: int,
    ) -> None:
        """
        Отправляет событие всем подходящим обработчикам плагинов.
        """
        action_name = action.get_full_class_name()
        handlers = self._get_handlers(event_name, action_name)

        if not handlers:
            return

        await self._init_plugin_states()

        event = PluginEvent(
            event_name=event_name,
            action_name=action_name,
            params=params,
            state_aspect=state_aspect,
            is_summary=is_summary,
            deps=factory,
            context=context,
            result=result,
            duration=duration,
            nest_level=nest_level,
        )

        tasks: list[Any] = []
        for handler, ignore, plugin in handlers:
            tasks.append(self._run_single_handler(handler, ignore, plugin, event))

        if tasks:
            await asyncio.gather(*tasks)
