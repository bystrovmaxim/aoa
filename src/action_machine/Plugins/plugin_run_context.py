# src/action_machine/plugins/plugin_run_context.py
"""
PluginRunContext — изолированный контекст плагинов для одного вызова run().

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
ЛОГГЕР ДЛЯ ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Все обработчики плагинов имеют сигнатуру (self, state, event, log).
PluginRunContext создаёт ScopedLogger для каждого вызова обработчика
со следующим scope:

    LogScope(
        machine=<имя машины>,
        mode=<режим>,
        plugin=<имя класса плагина>,
        action=<полное имя действия>,
        event=<имя события>,
        nest_level=<уровень вложенности>,
    )

Логгер передаётся как четвёртый аргумент: handler(plugin, state, event, log).

Для создания логгера PluginRunContext использует LogCoordinator и Context,
переданные в emit_event(). Это позволяет шаблонам в логах обращаться
ко всем пяти namespace: var, state, params, context, scope.

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИЯ ВЫПОЛНЕНИЯ ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

emit_event выбирает стратегию на основе флагов ignore_exceptions:

1. ВСЕ обработчики имеют ignore_exceptions=True:
   Запуск параллельно через asyncio.gather(return_exceptions=True).
   Исключения подавляются, состояние не обновляется при ошибке.

2. ХОТЯ БЫ ОДИН обработчик имеет ignore_exceptions=False:
   Запуск последовательно. При ошибке критического обработчика
   (ignore_exceptions=False) исключение пробрасывается наружу.
   Некритические обработчики (ignore_exceptions=True), стоящие перед ним,
   уже завершились и обновили свои состояния.

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
        │  emit_event() находит обработчики, создаёт ScopedLogger,
        │  вызывает handler(plugin, state, event, log)
        │
        ├── emit_event("global_start", ...)
        ├── emit_event("before:validate", ...)
        ├── emit_event("after:validate", ...)
        ├── emit_event("global_finish", ...)
        │
        └── (контекст уничтожается после завершения run())

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Внутри ActionProductMachine._run_internal():
    plugin_ctx = await self._plugin_coordinator.create_run_context()

    await plugin_ctx.emit_event(
        event_name="global_start",
        action=action, params=params,
        state_aspect=None, is_summary=False, result=None, duration=None,
        factory=factory, context=context, nest_level=current_nest,
        log_coordinator=self._log_coordinator,
        machine_name=self.__class__.__name__,
        mode=self._mode,
    )

    # Для тестов: доступ к финальному состоянию плагина
    state = plugin_ctx.get_plugin_state(counter_plugin)
"""

import asyncio
from collections.abc import Callable
from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_event import PluginEvent


class PluginRunContext:
    """
    Изолированный контекст плагинов для одного вызова run().

    Создаётся методом PluginCoordinator.create_run_context() в начале
    каждого _run_internal(). Хранит состояния всех плагинов и предоставляет
    метод emit_event() для рассылки событий обработчикам.

    Для каждого вызова обработчика создаёт ScopedLogger с scope плагина
    и передаёт его как четвёртый аргумент.

    После завершения run() контекст уничтожается вместе с состояниями.

    Атрибуты:
        _plugins : list[Plugin]
            Список экземпляров плагинов (ссылка на список из координатора).

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

        Не вызывается напрямую — используйте
        PluginCoordinator.create_run_context().

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
        log_coordinator: LogCoordinator | None = None,
        machine_name: str = "",
        mode: str = "",
    ) -> None:
        """
        Отправляет событие всем подходящим обработчикам плагинов.

        Для каждого обработчика создаёт ScopedLogger с scope плагина
        и вызывает handler(plugin, state, event, log).

        Стратегия выполнения зависит от флагов ignore_exceptions:
        - Все ignore=True → параллельно через asyncio.gather.
        - Хотя бы один ignore=False → последовательно.

        Аргументы:
            event_name: имя события ("global_start", "global_finish",
                        "before:{aspect}", "after:{aspect}").
            action: экземпляр действия.
            params: входные параметры действия.
            state_aspect: состояние конвейера на момент события.
            is_summary: True если событие связано с summary-аспектом.
            result: результат действия (для global_finish) или None.
            duration: длительность в секундах (для after-событий) или None.
            factory: фабрика зависимостей текущего действия.
            context: контекст выполнения.
            nest_level: уровень вложенности вызова.
            log_coordinator: координатор логирования. Обязательный параметр —
                             машина всегда передаёт его при вызове emit_event().
                             Используется для создания ScopedLogger обработчикам.
                             Если передать None, обработчик получит log=None
                             и любой вызов log.info() вызовет AttributeError.
            machine_name: имя класса машины для scope логгера.
            mode: режим выполнения для scope логгера.
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

        # Выбираем стратегию выполнения
        all_ignore = all(ignore for _, ignore, _ in handlers)

        if all_ignore:
            await self._run_all_parallel(
                handlers, event, log_coordinator, machine_name, mode,
                action_name, event_name, nest_level, context, params,
            )
        else:
            await self._run_all_sequential(
                handlers, event, log_coordinator, machine_name, mode,
                action_name, event_name, nest_level, context, params,
            )

    def _create_plugin_logger(
        self,
        plugin: Plugin,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
        action_name: str,
        event_name: str,
        nest_level: int,
        context: Context,
        params: BaseParams,
    ) -> ScopedLogger | None:
        """
        Создаёт ScopedLogger для обработчика плагина.

        Если log_coordinator равен None — возвращает None.
        Логгер создаётся с scope плагина, содержащим поля:
        machine, mode, plugin, action, event, nest_level.

        Аргументы:
            plugin: экземпляр плагина (для извлечения имени класса).
            log_coordinator: координатор логирования (или None).
            machine_name: имя класса машины.
            mode: режим выполнения.
            action_name: полное имя действия.
            event_name: имя события.
            nest_level: уровень вложенности.
            context: контекст выполнения.
            params: входные параметры действия.

        Возвращает:
            ScopedLogger с scope плагина, или None если log_coordinator
            не передан.
        """
        if log_coordinator is None:
            return None

        plugin_name = type(plugin).__name__

        return ScopedLogger(
            coordinator=log_coordinator,
            nest_level=nest_level,
            machine_name=machine_name,
            mode=mode,
            action_name=action_name,
            aspect_name="",
            context=context,
            state=BaseState(),
            params=params,
            plugin_name=plugin_name,
            event_name=event_name,
        )

    async def _run_all_parallel(
        self,
        handlers: list[tuple[Callable[..., Any], bool, Plugin]],
        event: PluginEvent,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
        action_name: str,
        event_name: str,
        nest_level: int,
        context: Context,
        params: BaseParams,
    ) -> None:
        """
        Запускает все обработчики параллельно.

        Используется когда ВСЕ обработчики имеют ignore_exceptions=True.
        asyncio.gather с return_exceptions=True гарантирует, что все задачи
        завершатся, даже если некоторые бросят исключения.
        """
        await asyncio.gather(
            *(
                self._run_single_handler(
                    handler, ignore, plugin, event,
                    log_coordinator, machine_name, mode,
                    action_name, event_name, nest_level,
                    context, params,
                )
                for handler, ignore, plugin in handlers
            ),
            return_exceptions=True,
        )

    async def _run_all_sequential(
        self,
        handlers: list[tuple[Callable[..., Any], bool, Plugin]],
        event: PluginEvent,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
        action_name: str,
        event_name: str,
        nest_level: int,
        context: Context,
        params: BaseParams,
    ) -> None:
        """
        Запускает все обработчики последовательно.

        Используется когда хотя бы один обработчик имеет
        ignore_exceptions=False.
        """
        for handler, ignore, plugin in handlers:
            await self._run_single_handler(
                handler, ignore, plugin, event,
                log_coordinator, machine_name, mode,
                action_name, event_name, nest_level,
                context, params,
            )

    async def _run_single_handler(
        self,
        handler: Callable[..., Any],
        ignore: bool,
        plugin: Plugin,
        event: PluginEvent,
        log_coordinator: LogCoordinator | None,
        machine_name: str,
        mode: str,
        action_name: str,
        event_name: str,
        nest_level: int,
        context: Context,
        params: BaseParams,
    ) -> None:
        """
        Запускает один обработчик плагина.

        Создаёт ScopedLogger с scope плагина и вызывает обработчик
        с четырьмя аргументами: handler(plugin, state, event, log).

        Передаёт текущее состояние плагина и обновляет его возвращённым
        значением.

        При ошибке:
        - ignore=True → ошибка подавляется, состояние не обновляется.
        - ignore=False → ошибка пробрасывается наружу.

        Аргументы:
            handler: unbound-метод обработчика (требует передачи self).
            ignore: флаг ignore_exceptions из @on.
            plugin: экземпляр плагина (передаётся как self в handler).
            event: объект события PluginEvent.
            log_coordinator: координатор логирования (или None).
            machine_name: имя машины для scope логгера.
            mode: режим для scope логгера.
            action_name: имя действия для scope логгера.
            event_name: имя события для scope логгера.
            nest_level: уровень вложенности для scope логгера.
            context: контекст выполнения.
            params: параметры действия.
        """
        plugin_id = id(plugin)
        state = self._plugin_states[plugin_id]

        try:
            log = self._create_plugin_logger(
                plugin, log_coordinator, machine_name, mode,
                action_name, event_name, nest_level, context, params,
            )
            new_state = await handler(plugin, state, event, log)
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
