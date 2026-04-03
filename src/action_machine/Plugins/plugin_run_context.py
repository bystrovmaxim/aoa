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
со scope: machine, mode, plugin, action, event, nest_level.

═══════════════════════════════════════════════════════════════════════════════
СОБЫТИЕ on_error
═══════════════════════════════════════════════════════════════════════════════

При эмитировании события "on_error" машина передаёт дополнительные
параметры error (экземпляр исключения) и has_action_handler (наличие
подходящего @on_error обработчика на Action). Эти параметры включаются
в PluginEvent и доступны обработчикам плагинов через event.error
и event.has_action_handler.

Плагины-наблюдатели не могут изменить результат или подавить ошибку.
Событие "on_error" эмитируется ДО вызова @on_error обработчика Action.

═══════════════════════════════════════════════════════════════════════════════
СТРАТЕГИЯ ВЫПОЛНЕНИЯ ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

emit_event выбирает стратегию на основе флагов ignore_exceptions:

1. ВСЕ обработчики имеют ignore_exceptions=True:
   Запуск параллельно через asyncio.gather(return_exceptions=True).

2. ХОТЯ БЫ ОДИН обработчик имеет ignore_exceptions=False:
   Запуск последовательно.
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

    Атрибуты:
        _plugins : list[Plugin]
            Список экземпляров плагинов (ссылка на список из координатора).
        _plugin_states : dict[int, Any]
            Состояния плагинов для текущего запроса. Ключ — id(plugin),
            значение — текущее состояние.
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
            initial_states: словарь {id(plugin): initial_state}.
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
        error: Exception | None = None,
        has_action_handler: bool = False,
    ) -> None:
        """
        Отправляет событие всем подходящим обработчикам плагинов.

        Для каждого обработчика создаёт ScopedLogger с scope плагина
        и вызывает handler(plugin, state, event, log).

        Аргументы:
            event_name: имя события ("global_start", "global_finish",
                        "before:{aspect}", "after:{aspect}", "on_error").
            action: экземпляр действия.
            params: входные параметры действия.
            state_aspect: состояние конвейера на момент события.
            is_summary: True если событие связано с summary-аспектом.
            result: результат действия (для global_finish) или None.
            duration: длительность в секундах или None.
            factory: фабрика зависимостей текущего действия.
            context: контекст выполнения.
            nest_level: уровень вложенности вызова.
            log_coordinator: координатор логирования (для ScopedLogger).
            machine_name: имя класса машины для scope логгера.
            mode: режим выполнения для scope логгера.
            error: исключение из аспекта (только для события "on_error").
                   Для остальных событий — None.
            has_action_handler: наличие подходящего @on_error обработчика
                                на уровне Action (только для "on_error").
                                Для остальных событий — False.
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
            error=error,
            has_action_handler=has_action_handler,
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
        self, plugin: Plugin, log_coordinator: LogCoordinator | None,
        machine_name: str, mode: str, action_name: str, event_name: str,
        nest_level: int, context: Context, params: BaseParams,
    ) -> ScopedLogger | None:
        """Создаёт ScopedLogger для обработчика плагина."""
        if log_coordinator is None:
            return None

        plugin_name = type(plugin).__name__

        return ScopedLogger(
            coordinator=log_coordinator, nest_level=nest_level,
            machine_name=machine_name, mode=mode,
            action_name=action_name, aspect_name="",
            context=context, state=BaseState(), params=params,
            plugin_name=plugin_name, event_name=event_name,
        )

    async def _run_all_parallel(
        self, handlers: list[tuple[Callable[..., Any], bool, Plugin]],
        event: PluginEvent, log_coordinator: LogCoordinator | None,
        machine_name: str, mode: str, action_name: str, event_name: str,
        nest_level: int, context: Context, params: BaseParams,
    ) -> None:
        """Запускает все обработчики параллельно (все ignore_exceptions=True)."""
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
        self, handlers: list[tuple[Callable[..., Any], bool, Plugin]],
        event: PluginEvent, log_coordinator: LogCoordinator | None,
        machine_name: str, mode: str, action_name: str, event_name: str,
        nest_level: int, context: Context, params: BaseParams,
    ) -> None:
        """Запускает все обработчики последовательно."""
        for handler, ignore, plugin in handlers:
            await self._run_single_handler(
                handler, ignore, plugin, event,
                log_coordinator, machine_name, mode,
                action_name, event_name, nest_level,
                context, params,
            )

    async def _run_single_handler(
        self, handler: Callable[..., Any], ignore: bool, plugin: Plugin,
        event: PluginEvent, log_coordinator: LogCoordinator | None,
        machine_name: str, mode: str, action_name: str, event_name: str,
        nest_level: int, context: Context, params: BaseParams,
    ) -> None:
        """Запускает один обработчик плагина с ScopedLogger."""
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

        Используется в тестах для проверки финального состояния.
        """
        return self._plugin_states[id(plugin)]
