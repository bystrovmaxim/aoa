# src/action_machine/plugins/plugin_run_context.py
"""
Модуль: PluginRunContext — изолированный контекст плагинов для одного вызова run().

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

PluginRunContext инкапсулирует всё мутабельное состояние плагинов,
необходимое для одного вызова ActionProductMachine.run(). Каждый вызов
run() создаёт свой экземпляр PluginRunContext, который живёт ровно
столько, сколько длится выполнение действия, и уничтожается по завершении.

Это гарантирует полную изоляцию между запросами: состояния плагинов
одного run() не влияют на другой run(), даже при параллельном выполнении
в рамках одного event loop (asyncio.gather нескольких run()).

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИЯ ВЫПОЛНЕНИЯ ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

emit_event выбирает стратегию выполнения обработчиков на основе флагов
ignore_exceptions:

1. ВСЕ обработчики имеют ignore_exceptions=True:
   Запуск параллельно через asyncio.gather(return_exceptions=True).
   Исключения подавляются внутри _run_single_handler, состояние плагина
   не обновляется при ошибке. Параллельное выполнение безопасно, потому что
   отмена одной задачи не нужна — все исключения игнорируются.

2. ХОТЯ БЫ ОДИН обработчик имеет ignore_exceptions=False:
   Запуск последовательно. Это гарантирует, что при ошибке критического
   обработчика (ignore_exceptions=False) некритические обработчики
   (ignore_exceptions=True) уже завершились и обновили свои состояния.

   Проблема параллельного выполнения: asyncio.gather без return_exceptions
   при первом исключении ОТМЕНЯЕТ все незавершённые задачи. Обработчик
   с ignore_exceptions=True мог бы быть отменён через CancelledError
   до завершения, и его состояние не обновится. Последовательное
   выполнение устраняет эту проблему.

Оверхед последовательного выполнения минимален: типичные обработчики
плагинов (инкремент счётчика, запись метрики) занимают наносекунды
CPU-работы. При 5 плагинах и 6 событиях за run() это ~0 мс.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._run_internal(...)
        │
        │  plugin_ctx = await self._plugin_coordinator.create_run_context()
        ▼
    PluginRunContext
        │
        │  Хранит: {id(plugin): state} для каждого плагина
        │  Метод emit_event() находит обработчики и вызывает их
        │  Метод get_plugin_state(plugin) — доступ к состоянию для тестов
        │
        ├── emit_event("global_start", ...)
        ├── emit_event("before:validate", ...)
        ├── emit_event("after:validate", ...)
        ├── emit_event("global_finish", ...)
        │
        └── (контекст уничтожается после завершения run())

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. ИЗОЛЯЦИЯ: каждый PluginRunContext содержит собственную копию состояний
   плагинов, инициализированную через get_initial_state(). Состояния
   не разделяются между вызовами run().

2. ВРЕМЯ ЖИЗНИ: контекст создаётся в начале _run_internal() и существует
   до завершения run(). После этого сборщик мусора освобождает память.

3. БЕЗ КЕШИРОВАНИЯ ОБРАБОТЧИКОВ: поиск обработчиков выполняется при
   каждом emit_event() через plugin.get_handlers(). Оверхед минимален
   (~300 мкс на запрос при 5 плагинах) и не оправдывает усложнение
   архитектуры кешированием.

4. ОБРАБОТКА ОШИБОК: каждый обработчик имеет флаг ignore_exceptions
   (задаётся в @on). При ignore_exceptions=True ошибка подавляется молча,
   состояние плагина не обновляется. При ignore_exceptions=False ошибка
   пробрасывается наружу и прерывает выполнение действия.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Внутри ActionProductMachine._run_internal():
    plugin_ctx = await self._plugin_coordinator.create_run_context()

    await plugin_ctx.emit_event(
        event_name="global_start",
        action=action,
        params=params,
        ...
    )

    # ... выполнение аспектов ...

    await plugin_ctx.emit_event(
        event_name="global_finish",
        action=action,
        params=params,
        result=result,
        ...
    )

    # Для тестов: доступ к финальному состоянию плагина
    state = plugin_ctx.get_plugin_state(counter_plugin)

═══════════════════════════════════════════════════════════════════════════════
АККУМУЛЯЦИЯ ДАННЫХ МЕЖДУ ЗАПРОСАМИ
═══════════════════════════════════════════════════════════════════════════════

Если плагину необходимо накапливать данные между запросами (например,
счётчик общего числа выполненных действий), он использует внешнее
хранилище, переданное через конструктор плагина:

    class MetricsPlugin(Plugin):
        def __init__(self, storage: MetricsStorage):
            self._storage = storage

        async def get_initial_state(self) -> dict:
            return {}

        @on("global_finish", ".*")
        async def track(self, state, event):
            await self._storage.increment(event.action_name)
            return state

Фреймворк предоставляет изоляцию per-request состояния. Пользователь
выбирает политику аккумуляции (внешний счётчик, база данных, Redis и т.д.).
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


class PluginRunContext:
    """
    Изолированный контекст плагинов для одного вызова run().

    Создаётся методом PluginCoordinator.create_run_context() в начале
    каждого _run_internal(). Хранит состояния всех плагинов и предоставляет
    метод emit_event() для рассылки событий обработчикам.

    После завершения run() контекст уничтожается вместе с состояниями.

    Атрибуты:
        _plugins : list[Plugin]
            Список экземпляров плагинов (ссылка на список из координатора).
            Плагины сами по себе stateless — состояние хранится в _plugin_states.

        _plugin_states : dict[int, Any]
            Состояния плагинов для текущего запроса. Ключ — id(plugin),
            значение — текущее состояние, инициализированное через
            get_initial_state() и обновляемое обработчиками.
    """

    def __init__(
        self,
        plugins: list[Plugin],
        initial_states: dict[int, Any],
    ) -> None:
        """
        Инициализирует контекст с плагинами и их начальными состояниями.

        Не вызывается напрямую — используйте PluginCoordinator.create_run_context().

        Аргументы:
            plugins: список экземпляров плагинов.
            initial_states: словарь {id(plugin): initial_state} для каждого
                           плагина, полученный вызовом get_initial_state().
        """
        self._plugins: list[Plugin] = plugins
        self._plugin_states: dict[int, Any] = dict(initial_states)

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

        Стратегия выполнения зависит от флагов ignore_exceptions:

        - Все обработчики имеют ignore_exceptions=True → параллельно
          через asyncio.gather(return_exceptions=True). Безопасно,
          потому что все исключения подавляются.

        - Хотя бы один имеет ignore_exceptions=False → последовательно.
          Гарантирует, что некритические обработчики (ignore=True)
          завершатся и обновят состояние даже при ошибке критического.

        Поиск обработчиков выполняется при каждом вызове без кеширования.

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

        # Собираем все обработчики из всех плагинов
        handlers: list[tuple[Callable[..., Any], bool, Plugin]] = []
        for plugin in self._plugins:
            for handler, ignore in plugin.get_handlers(event_name, action_name):
                handlers.append((handler, ignore, plugin))

        if not handlers:
            return

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

        # Выбираем стратегию выполнения на основе флагов ignore_exceptions.
        #
        # Если все обработчики подавляют исключения — безопасно запускать
        # параллельно: ни одна задача не будет отменена из-за ошибки другой.
        #
        # Если хотя бы один обработчик НЕ подавляет исключения — запускаем
        # последовательно. Это гарантирует, что при ошибке критического
        # обработчика (ignore=False) некритические (ignore=True) уже
        # завершились и обновили свои состояния. При параллельном выполнении
        # asyncio.gather без return_exceptions отменил бы незавершённые задачи.
        all_ignore = all(ignore for _, ignore, _ in handlers)

        if all_ignore:
            await self._run_all_parallel(handlers, event)
        else:
            await self._run_all_sequential(handlers, event)

    async def _run_all_parallel(
        self,
        handlers: list[tuple[Callable[..., Any], bool, Plugin]],
        event: PluginEvent,
    ) -> None:
        """
        Запускает все обработчики параллельно.

        Используется когда ВСЕ обработчики имеют ignore_exceptions=True.
        asyncio.gather с return_exceptions=True гарантирует, что все задачи
        завершатся, даже если некоторые бросят исключения.

        Аргументы:
            handlers: список кортежей (handler, ignore, plugin).
            event: объект события PluginEvent.
        """
        await asyncio.gather(
            *(
                self._run_single_handler(handler, ignore, plugin, event)
                for handler, ignore, plugin in handlers
            ),
            return_exceptions=True,
        )

    async def _run_all_sequential(
        self,
        handlers: list[tuple[Callable[..., Any], bool, Plugin]],
        event: PluginEvent,
    ) -> None:
        """
        Запускает все обработчики последовательно.

        Используется когда хотя бы один обработчик имеет
        ignore_exceptions=False. Последовательное выполнение гарантирует,
        что обработчики с ignore_exceptions=True завершатся и обновят
        состояние даже при ошибке критического обработчика.

        При ошибке в обработчике с ignore_exceptions=False исключение
        пробрасывается наружу немедленно. Обработчики, стоящие после
        него в списке, не выполняются.

        Аргументы:
            handlers: список кортежей (handler, ignore, plugin).
            event: объект события PluginEvent.
        """
        for handler, ignore, plugin in handlers:
            await self._run_single_handler(handler, ignore, plugin, event)

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
                pass
            else:
                raise

    def get_plugin_state(self, plugin: Plugin) -> Any:
        """
        Возвращает текущее состояние указанного плагина.

        Используется в тестах для проверки финального состояния плагина
        после выполнения действия.

        Аргументы:
            plugin: экземпляр плагина, состояние которого нужно получить.

        Возвращает:
            Текущее состояние плагина (тип определяется get_initial_state()).

        Исключения:
            KeyError: если плагин не зарегистрирован в контексте.
        """
        return self._plugin_states[id(plugin)]
