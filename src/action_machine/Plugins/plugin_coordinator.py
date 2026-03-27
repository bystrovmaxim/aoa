# src/action_machine/plugins/plugin_coordinator.py
"""
Координатор плагинов для ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Отделён от ActionProductMachine для разделения зон ответственности.
ActionProductMachine управляет конвейером аспектов,
PluginCoordinator управляет жизненным циклом плагинов:

    1. Ленивая инициализация состояний плагинов (get_initial_state).
    2. Кеширование обработчиков по ключу (event_name, action_name).
    3. Асинхронное выполнение обработчиков.
    4. Обработка ignore_exceptions.

Координатор ничего не знает об аспектах, ролях и соединениях.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine
        │
        │  emit_event(event_name, action, params, ...)
        ▼
    PluginCoordinator
        │
        ├── _get_handlers(event_name, action_name)
        │       └── plugin.get_handlers(event_name, action_name)
        │           └── сканирует _on_subscriptions на методах плагина
        │
        ├── _init_plugin_states()
        │       └── plugin.get_initial_state() для каждого плагина
        │
        └── _run_single_handler(handler, ignore, plugin, event)
                └── handler(plugin, state, event) → new_state

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Каждый обработчик плагина имеет флаг ignore_exceptions (задаётся в @on):

- ignore_exceptions=True (по умолчанию): ошибка обработчика подавляется
  молча. Состояние плагина не обновляется. Это безопасный режим для
  метрик, логирования и других некритичных плагинов.

- ignore_exceptions=False: ошибка обработчика пробрасывается наружу
  и прерывает выполнение действия. Используется для критичных плагинов,
  например, аудита или обязательных проверок.

Никакие ошибки не выводятся через print. Если диагностика игнорированных
ошибок необходима, она должна быть реализована через отдельный callback
или LogCoordinator, переданный в конструктор.

═══════════════════════════════════════════════════════════════════════════════
ИЗМЕНЕНИЯ (Этап 1 — очистка)
═══════════════════════════════════════════════════════════════════════════════

- Удалён print() из _run_single_handler(). При ignore_exceptions=True
  ошибка теперь подавляется молча, без вывода в stdout. Это соответствует
  конвенции проекта: никаких print в ядре.
- Восстановлен сбор обработчиков через встроенный метод plugin.get_handlers,
  чтобы избежать циклических зависимостей со шлюзами и координатором
  метаданных.
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
    Создаётся ActionProductMachine при инициализации и используется
    для рассылки событий (global_start, global_finish, before/after аспектов)
    всем подписанным плагинам.

    Атрибуты:
        _plugins : list[Plugin]
            Список экземпляров плагинов, переданных при создании.

        _handler_cache : dict[tuple[str, str], list[tuple[Callable, bool, Plugin]]]
            Кеш обработчиков. Ключ — (event_name, action_name).
            Значение — список кортежей (handler, ignore_exceptions, plugin).
            Заполняется лениво при первом запросе для каждой пары.

        _plugin_states : dict[int, Any]
            Состояния плагинов. Ключ — id(plugin), значение — текущее
            состояние, возвращённое get_initial_state() или последним
            обработчиком. Инициализируется лениво при первом событии.
    """

    def __init__(
        self,
        plugins: list[Plugin],
    ) -> None:
        """
        Инициализирует координатор плагинов.

        Аргументы:
            plugins: список экземпляров плагинов. Каждый плагин должен
                     наследовать Plugin и реализовывать get_initial_state().
                     Методы-обработчики помечаются декоратором @on.
        """
        self._plugins: list[Plugin] = plugins

        # Кеш: (event_name, action_name) → [(handler, ignore_exceptions, plugin)]
        self._handler_cache: dict[
            tuple[str, str],
            list[tuple[Callable[..., Any], bool, Plugin]]
        ] = {}

        # Состояния плагинов: id(plugin) → state
        self._plugin_states: dict[int, Any] = {}

    # ─────────────────────────────────────────────────────────────────────
    # Приватные методы
    # ─────────────────────────────────────────────────────────────────────

    def _get_handlers(
        self,
        event_name: str,
        action_name: str,
    ) -> list[tuple[Callable[..., Any], bool, Plugin]]:
        """
        Возвращает (и кеширует) список обработчиков для данного события и действия.

        Для каждого плагина вызывает plugin.get_handlers(), который сканирует
        методы плагина на наличие _on_subscriptions и проверяет совпадение
        event_type и action_filter.

        Аргументы:
            event_name: имя события (например, "global_finish").
            action_name: полное имя класса действия (включая модуль).

        Возвращает:
            Список кортежей (handler, ignore_exceptions, plugin).
        """
        cache_key = (event_name, action_name)

        if cache_key not in self._handler_cache:
            handlers: list[tuple[Callable[..., Any], bool, Plugin]] = []
            for plugin in self._plugins:
                for handler, ignore in plugin.get_handlers(event_name, action_name):
                    handlers.append((handler, ignore, plugin))
            self._handler_cache[cache_key] = handlers

        return self._handler_cache[cache_key]

    async def _init_plugin_states(self) -> None:
        """
        Асинхронно инициализирует состояния всех плагинов.

        Вызывает get_initial_state() для каждого плагина, у которого
        ещё не было инициализации. Результат сохраняется в _plugin_states
        по ключу id(plugin).
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

        Передаёт текущее состояние плагина в обработчик и обновляет
        состояние возвращённым значением. Если обработчик выбрасывает
        исключение:
        - При ignore=True: ошибка подавляется молча, состояние
          плагина не обновляется.
        - При ignore=False: ошибка пробрасывается наружу.

        Аргументы:
            handler: метод-обработчик (unbound — требует передачи self).
            ignore: флаг ignore_exceptions из @on.
            plugin: экземпляр плагина (передаётся как self в handler).
            event: объект события PluginEvent.
        """
        plugin_id = id(plugin)
        state = self._plugin_states[plugin_id]
        try:
            new_state = await handler(plugin, state, event)
            self._plugin_states[plugin_id] = new_state
        except Exception:
            if ignore:
                # Ошибка подавляется молча. Состояние плагина не обновляется.
                # Для диагностики игнорированных ошибок используйте
                # LogCoordinator или callback, переданный в конструктор.
                pass
            else:
                raise

    def _find_plugin_for_handler(
        self,
        handler: Callable[..., Any],
    ) -> Plugin | None:
        """
        Находит экземпляр плагина, которому принадлежит переданный обработчик.

        Используется в тестах для проверки привязки обработчиков к плагинам.

        Аргументы:
            handler: метод-обработчик.

        Возвращает:
            Plugin или None, если обработчик не найден.
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

    # ─────────────────────────────────────────────────────────────────────
    # Публичные методы
    # ─────────────────────────────────────────────────────────────────────

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

        Последовательность:
        1. Получает полное имя действия через action.get_full_class_name().
        2. Ищет (и кеширует) обработчики для пары (event_name, action_name).
        3. Если обработчиков нет — выходит без действий.
        4. Инициализирует состояния плагинов (лениво).
        5. Создаёт объект PluginEvent.
        6. Запускает все обработчики параллельно через asyncio.gather().

        Аргументы:
            event_name: имя события ("global_start", "global_finish",
                        "before:{aspect}", "after:{aspect}").
            action: экземпляр действия.
            params: входные параметры действия.
            state_aspect: состояние конвейера на момент события (dict или None).
            is_summary: True если событие связано с summary-аспектом.
            result: результат действия (для global_finish) или None.
            duration: длительность в секундах (для after-событий) или None.
            factory: фабрика зависимостей текущего действия.
            context: контекст выполнения.
            nest_level: уровень вложенности вызова.
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
