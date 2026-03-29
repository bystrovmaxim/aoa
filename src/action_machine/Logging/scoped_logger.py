# src/action_machine/logging/scoped_logger.py
"""
ScopedLogger — логгер, привязанный к scope текущего аспекта или плагина.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ScopedLogger — обёртка над LogCoordinator, привязанная к конкретному
scope выполнения. Автоматически добавляет координаты выполнения в LogScope
и передаёт их в LogCoordinator при каждом вызове info/warning/error/debug.

═══════════════════════════════════════════════════════════════════════════════
ДВА РЕЖИМА ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

1. ЛОГГЕР ДЛЯ АСПЕКТОВ ДЕЙСТВИЙ

   Создаётся ActionProductMachine для каждого вызова аспекта. Передаётся
   в аспекты через ToolsBox (box.info, box.warning и т.д.).

   Scope содержит поля: machine, mode, action, aspect, nest_level.

   Пример:
       await box.info("Платёж обработан: {%var.txn_id}", txn_id="TXN-123")

2. ЛОГГЕР ДЛЯ ОБРАБОТЧИКОВ ПЛАГИНОВ

   Создаётся PluginRunContext перед вызовом обработчика плагина с сигнатурой
   (self, state, event, log). Передаётся как параметр log.

   Scope содержит поля: machine, mode, plugin, action, event, nest_level.

   Пример:
       @on("global_finish", ".*")
       async def on_finish(self, state, event, log):
           await log.info("Действие {%scope.action} завершено за {%var.duration}с",
                          duration=event.duration)

═══════════════════════════════════════════════════════════════════════════════
STATE И PARAMS
═══════════════════════════════════════════════════════════════════════════════

ScopedLogger получает реальные state и params при создании. Это позволяет
использовать шаблоны вида {%state.total} и {%params.amount} в сообщениях
логов без необходимости дублировать значения через kwargs.

Для аспектов: state содержит данные, накопленные предыдущими regular-аспектами;
params — входные параметры действия.

Для плагинов: state и params передаются из контекста события; если не указаны,
создаются пустые экземпляры BaseState() и BaseParams().

Пользовательские данные, переданные через **kwargs в info/warning/error/debug,
попадают в namespace var и доступны через {%var.key}.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА (ДЛЯ АСПЕКТОВ)
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._call_aspect(...)
        │
        │  Создаёт ScopedLogger с координатами аспекта, state и params
        ▼
    ScopedLogger(coordinator, nest_level, machine, mode, action, aspect, context, state, params)
        │
        │  аспект вызывает box.info("сообщение", key=value)
        ▼
    ScopedLogger._emit("info", "сообщение", key=value)
        │
        │  Формирует var = {"level": "info", "key": value}
        │  Использует заранее созданный LogScope (с nest_level)
        │  Передаёт реальные state и params
        ▼
    LogCoordinator.emit(message, var, scope, ctx, state, params, indent)

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА (ДЛЯ ПЛАГИНОВ)
═══════════════════════════════════════════════════════════════════════════════

    PluginRunContext._run_single_handler(...)
        │
        │  Создаёт ScopedLogger с координатами плагина
        ▼
    ScopedLogger(coordinator, nest_level, machine, mode, action, ...,
                 context, state, params, plugin_name, event_name)
        │
        │  обработчик вызывает log.info("сообщение", key=value)
        ▼
    ScopedLogger._emit("info", "сообщение", key=value)
        │
        ▼
    LogCoordinator.emit(...)

═══════════════════════════════════════════════════════════════════════════════
ПЯТЬ NAMESPACE В ШАБЛОНАХ
═══════════════════════════════════════════════════════════════════════════════

    {%var.key}           — пользовательские kwargs + level
    {%state.field}       — текущее состояние конвейера аспектов
    {%params.field}      — входные параметры действия
    {%context.user.id}   — контекст выполнения
    {%scope.action}      — координаты в конвейере (включая nest_level)

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ В АСПЕКТЕ
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Обработка платежа")
    async def process_payment(self, params, state, box, connections):
        # Данные из state и params подставляются автоматически:
        await box.info("Итого: {%state.total}, пользователь: {%params.user_id}")

        # Пользовательские данные через kwargs → namespace var:
        await box.info("Платёж обработан", txn_id=txn_id, amount=params.amount)

        # Уровень вложенности доступен через scope:
        await box.info("[Уровень {%scope.nest_level}] Обработка завершена")

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ В ПЛАГИНЕ
═══════════════════════════════════════════════════════════════════════════════

    class MetricsPlugin(Plugin):
        @on("global_finish", ".*")
        async def track(self, state, event, log):
            await log.info(
                "[{%scope.plugin}] Действие {%scope.action} завершено "
                "за {%var.duration}с на уровне {%scope.nest_level}",
                duration=event.duration,
            )
            state["count"] = state.get("count", 0) + 1
            return state
"""

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope


class ScopedLogger:
    """
    Логгер, привязанный к scope текущего аспекта или плагина.

    Создаётся ActionProductMachine (для аспектов) или PluginRunContext
    (для плагинов). Все аспекты получают ScopedLogger через ToolsBox,
    обработчики плагинов — через параметр log.

    Методы info, warning, error, debug отправляют сообщение через
    LogCoordinator, автоматически добавляя ключ "level" и пользовательские
    kwargs в var. State и params передаются из конструктора.

    Атрибуты:
        _coordinator : LogCoordinator
            Координатор логирования (шина).
        _nest_level : int
            Уровень вложенности вызова действия.
        _context : Context
            Контекст выполнения (пользователь, запрос, окружение).
        _state : BaseState
            Текущее состояние конвейера аспектов. Доступно в шаблонах
            через {%state.field}.
        _params : BaseParams
            Входные параметры действия. Доступны в шаблонах
            через {%params.field}.
        _scope : LogScope
            Заранее созданный scope с полями, зависящими от контекста
            создания (аспект или плагин). Содержит nest_level.
    """

    def __init__(
        self,
        coordinator: LogCoordinator,
        nest_level: int,
        machine_name: str,
        mode: str,
        action_name: str,
        aspect_name: str,
        context: Context,
        state: BaseState | None = None,
        params: BaseParams | None = None,
        plugin_name: str | None = None,
        event_name: str | None = None,
    ) -> None:
        """
        Инициализирует привязанный логгер.

        Создаёт LogScope с полями, зависящими от контекста использования:

        Для аспектов (plugin_name=None):
            Поля scope: machine, mode, action, aspect, nest_level.

        Для плагинов (plugin_name задан):
            Поля scope: machine, mode, plugin, action, event, nest_level.

        Аргументы:
            coordinator: координатор логирования (шина).
            nest_level: уровень вложенности вызова действия (0 — корневой).
            machine_name: имя класса машины ("ActionProductMachine").
            mode: режим выполнения ("production", "test", "staging").
            action_name: полное имя класса действия (включая модуль).
            aspect_name: имя метода-аспекта. Пустая строка для scope плагинов.
            context: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера аспектов. Если None,
                   создаётся пустой BaseState(). Доступно в шаблонах
                   через {%state.field}.
            params: входные параметры действия. Если None, создаётся
                    пустой BaseParams(). Доступно в шаблонах через
                    {%params.field}.
            plugin_name: имя класса плагина. Если задано, создаётся scope
                         для плагина (с полями plugin и event). Если None —
                         создаётся scope для аспекта (с полем aspect).
            event_name: имя события плагина ("global_finish", "before:validate").
                        Используется только при plugin_name is not None.
        """
        self._coordinator = coordinator
        self._nest_level = nest_level
        self._context = context
        self._state = state if state is not None else BaseState()
        self._params = params if params is not None else BaseParams()

        # Формируем scope в зависимости от контекста использования.
        # Для плагинов — scope с полями plugin и event.
        # Для аспектов — scope с полем aspect.
        if plugin_name is not None:
            self._scope = LogScope(
                machine=machine_name,
                mode=mode,
                plugin=plugin_name,
                action=action_name,
                event=event_name or "",
                nest_level=nest_level,
            )
        else:
            self._scope = LogScope(
                machine=machine_name,
                mode=mode,
                action=action_name,
                aspect=aspect_name,
                nest_level=nest_level,
            )

    async def _emit(self, lvl: str, message: str, **kwargs: Any) -> None:
        """
        Внутренний метод отправки сообщения в координатор.

        Формирует словарь var из системного ключа "level" и пользовательских
        kwargs. Если пользователь случайно передал ключ "level", он
        игнорируется — используется системное значение.

        State и params берутся из конструктора — это реальные данные
        конвейера, доступные в шаблонах через {%state.field} и {%params.field}.

        Аргументы:
            lvl: уровень логирования (info, warning, error, debug).
            message: текст сообщения (может содержать шаблоны {%...}
                     и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в namespace var.
                      Доступны в шаблонах через {%var.key}.
        """
        # Удаляем ключ 'level' из kwargs, если пользователь случайно передал его.
        kwargs.pop("level", None)

        # В var попадают только level и пользовательские данные.
        var = {"level": lvl, **kwargs}

        await self._coordinator.emit(
            message=message,
            var=var,
            scope=self._scope,
            ctx=self._context,
            state=self._state,
            params=self._params,
            indent=self._nest_level,
        )

    async def info(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня INFO.

        Аргументы:
            message: текст сообщения. Поддерживает шаблоны:
                     {%var.key}, {%state.field}, {%params.field},
                     {%context.user.id}, {%scope.action}, {%scope.nest_level},
                     {%scope.plugin}, {%scope.event}, {iif(...)}.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("info", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня WARNING.

        Аргументы:
            message: текст сообщения. Поддерживает все шаблоны.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("warning", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня ERROR.

        Аргументы:
            message: текст сообщения. Поддерживает все шаблоны.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("error", message, **kwargs)

    async def debug(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня DEBUG.

        Аргументы:
            message: текст сообщения. Поддерживает все шаблоны.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("debug", message, **kwargs)
