# ActionMachine/Plugins/PluginCoordinator.py
"""
Координатор плагинов для ActionMachine.

Выделен из ActionProductMachine для разделения обязанностей.
ActionProductMachine отвечает за аспектный конвейер,
PluginCoordinator — за жизненный цикл плагинов:

    1. Ленивая инициализация состояний плагинов (get_initial_state).
    2. Кеширование обработчиков по ключу (event_name, action_name).
    3. Асинхронный запуск обработчиков с ограничением конкурентности
       через asyncio.Semaphore.
    4. Обработка ignore_exceptions — если обработчик помечен
       ignore_exceptions=True, его ошибки печатаются, но не прерывают
       выполнение действия.

Координатор не знает про аспекты, роли, connections — только про плагины.
Это позволяет тестировать плагины отдельно от аспектного конвейера.

Все методы кроме emit_event — приватные. Единственная точка входа —
метод emit_event, который вызывается из ActionProductMachine.

Состояния плагинов (_plugin_states) живут столько же, сколько координатор.
При каждом вызове run() в ActionProductMachine координатор используется
повторно — состояния накапливаются между вызовами. Это позволяет
плагинам агрегировать метрики за несколько запусков (например, счётчик
вызовов в MetricsPlugin).

Кеш обработчиков (_handler_cache) также живёт столько же, сколько
координатор. Ключ кеша — (event_name, action_name). Это безопасно,
потому что множество обработчиков плагина для данного события и действия
не меняется после создания плагина (декоратор @on применяется при
определении класса).
"""

import asyncio
from collections.abc import Callable
from typing import Any

from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginEvent import PluginEvent


class PluginCoordinator:
    """
    Координатор жизненного цикла плагинов.

    Управляет:
        - Инициализацией состояний плагинов (ленивая, через executor).
        - Кешированием обработчиков по (event_name, action_name).
        - Асинхронным запуском обработчиков с семафором конкурентности.
        - Обработкой ignore_exceptions для отдельных обработчиков.

    Не знает про аспекты, роли, connections — только про плагины.

    Атрибуты:
        _plugins: список экземпляров плагинов.
        _max_concurrent_handlers: максимальное количество одновременно
                                   выполняющихся обработчиков для одного события.
        _handler_cache: кеш обработчиков по (event_name, action_name).
        _plugin_states: словарь состояний плагинов по id(plugin).
    """

    def __init__(
        self,
        plugins: list[Plugin],
        max_concurrent_handlers: int = 10,
    ) -> None:
        """
        Инициализирует координатор плагинов.

        Аргументы:
            plugins: список экземпляров плагинов. Порядок определяет
                     порядок вызова обработчиков при совпадении нескольких.
            max_concurrent_handlers: максимальное количество одновременно
                                     выполняющихся обработчиков для одного
                                     события. По умолчанию 10.
                                     Используется asyncio.Semaphore для
                                     ограничения конкурентности.
        """
        self._plugins: list[Plugin] = plugins
        self._max_concurrent_handlers: int = max_concurrent_handlers

        # Кеш обработчиков: (event_name, action_name) → [(handler, ignore)]
        # Заполняется лениво при первом вызове _get_handlers для каждого ключа.
        # Безопасен для повторного использования, т.к. множество обработчиков
        # не меняется после создания плагина.
        self._handler_cache: dict[tuple[str, str], list[tuple[Callable[..., Any], bool]]] = {}

        # Состояния плагинов: id(plugin) → state
        # Инициализируются лениво при первом событии через _init_plugin_states.
        # Обновляются после каждого вызова обработчика — обработчик возвращает
        # новое состояние, которое сохраняется обратно в словарь.
        self._plugin_states: dict[int, Any] = {}

    # ---------- Приватные методы ----------

    def _get_handlers(
        self,
        event_name: str,
        action_name: str,
    ) -> list[tuple[Callable[..., Any], bool]]:
        """
        Возвращает (и кеширует) список обработчиков для данного события и действия.

        При первом вызове для данного (event_name, action_name) обходит все
        плагины и собирает подходящие обработчики через plugin.get_handlers().
        Результат кешируется для последующих вызовов.

        Аргументы:
            event_name: имя события (например, 'global_start', 'before:validate').
            action_name: полное имя класса действия (включая модуль).

        Возвращает:
            Список кортежей (handler, ignore_exceptions).
            Пустой список если ни один обработчик не подходит.
        """
        cache_key = (event_name, action_name)

        if cache_key not in self._handler_cache:
            handlers: list[tuple[Callable[..., Any], bool]] = []
            for plugin in self._plugins:
                handlers.extend(plugin.get_handlers(event_name, action_name))
            self._handler_cache[cache_key] = handlers

        return self._handler_cache[cache_key]

    async def _init_plugin_states(self) -> None:
        """
        Асинхронно инициализирует состояния всех плагинов.

        Для каждого плагина, состояние которого ещё не инициализировано,
        вызывает синхронный метод get_initial_state() в отдельном потоке
        (через run_in_executor), чтобы не блокировать event loop.

        Метод идемпотентен: повторные вызовы для уже инициализированных
        плагинов не выполняют никакой работы.
        """
        loop = asyncio.get_running_loop()
        for plugin in self._plugins:
            plugin_id = id(plugin)
            if plugin_id not in self._plugin_states:
                # Выполняем синхронный метод в executor,
                # чтобы не блокировать event loop.
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
        Запускает один обработчик плагина.

        Извлекает текущее состояние плагина из _plugin_states,
        передаёт его в обработчик вместе с event,
        и сохраняет возвращённое новое состояние обратно.

        Если ignore=True и обработчик выбросил исключение —
        ошибка печатается в stdout, но не прерывает выполнение.
        Если ignore=False — исключение пробрасывается наверх.

        Аргументы:
            handler: метод-обработчик плагина (async def).
            ignore: флаг ignore_exceptions из декоратора @on.
            plugin: экземпляр плагина (для получения id и имени класса).
            event: объект PluginEvent со всеми данными события.
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

    def _find_plugin_for_handler(
        self,
        handler: Callable[..., Any],
    ) -> Plugin | None:
        """
        Находит экземпляр плагина, которому принадлежит данный обработчик.

        Проверяет атрибут __self__ связанного метода (bound method),
        чтобы определить, какой экземпляр плагина создал этот обработчик.

        Аргументы:
            handler: метод-обработчик плагина.

        Возвращает:
            Экземпляр Plugin если найден, иначе None.
        """
        for plugin in self._plugins:
            if hasattr(handler, "__self__") and handler.__self__ is plugin:
                return plugin
        return None

    # ---------- Публичный метод ----------

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
        Рассылает событие всем подходящим обработчикам плагинов.

        Это единственный публичный метод координатора. Вызывается
        из ActionProductMachine в нужные моменты конвейера:
        global_start, before:aspect, after:aspect, global_finish.

        Последовательность выполнения:
            1. Получение списка обработчиков из кеша (или сбор + кеширование).
            2. Если обработчиков нет — ранний возврат (оптимизация).
            3. Инициализация состояний плагинов (ленивая, идемпотентная).
            4. Создание объекта PluginEvent со всеми данными.
            5. Создание задач для каждого обработчика с семафором.
            6. Параллельный запуск через asyncio.gather.

        Аргументы:
            event_name: имя события (например, 'global_start',
                        'before:validate', 'after:save', 'global_finish').
            action: экземпляр действия.
            params: входные параметры действия.
            state_aspect: состояние конвейера на момент события
                          (dict или None для global_start/global_finish).
            is_summary: True если событие относится к summary-аспекту.
            result: результат действия (для global_finish, иначе None).
            duration: длительность выполнения в секундах
                      (для after-событий и global_finish, иначе None).
            factory: фабрика зависимостей текущего выполнения.
            context: контекст выполнения (пользователь, запрос, окружение).
            nest_level: уровень вложенности вызова действия
                        (0 для корневого, 1 для дочернего и т.д.).
        """
        action_name = action.get_full_class_name()
        handlers = self._get_handlers(event_name, action_name)

        # Оптимизация: если нет подходящих обработчиков — ничего не делаем.
        # Это покрывает ~80% событий в типичном приложении.
        if not handlers:
            return

        # Инициализируем состояния плагинов асинхронно (ленивая инициализация).
        # При повторных вызовах уже инициализированные плагины пропускаются.
        await self._init_plugin_states()

        # Создаём объект события со всеми данными для обработчиков.
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

        # Семафор ограничивает количество одновременно выполняющихся
        # обработчиков. Это предотвращает ситуацию, когда 50 плагинов
        # одновременно выполняют тяжёлые IO-операции.
        semaphore = asyncio.Semaphore(self._max_concurrent_handlers)

        async def run_with_semaphore(
            handler: Callable[..., Any],
            ignore: bool,
            plugin: Plugin,
        ) -> None:
            """Запускает обработчик с ограничением конкурентности."""
            async with semaphore:
                await self._run_single_handler(handler, ignore, plugin, event)

        # Собираем задачи для всех обработчиков.
        # Для каждого обработчика находим его плагин через _find_plugin_for_handler.
        tasks: list[Any] = []
        for handler, ignore in handlers:
            plugin = self._find_plugin_for_handler(handler)
            if plugin is not None:
                tasks.append(run_with_semaphore(handler, ignore, plugin))

        # Запускаем все задачи параллельно.
        # asyncio.gather ждёт завершения всех задач.
        # Если какой-то обработчик с ignore=False выбросит исключение —
        # оно пробросится из gather наверх.
        await asyncio.gather(*tasks)
