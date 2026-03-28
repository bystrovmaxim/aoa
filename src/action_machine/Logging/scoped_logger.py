# src/action_machine/logging/scoped_logger.py
"""
ScopedLogger — логгер, привязанный к scope текущего аспекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ScopedLogger — обёртка над LogCoordinator, привязанная к конкретному
scope выполнения. Создаётся ActionProductMachine для каждого вызова аспекта.
Автоматически добавляет координаты выполнения (machine, mode, action, aspect)
в LogScope и передаёт их в LogCoordinator при каждом вызове
info/warning/error/debug.

═══════════════════════════════════════════════════════════════════════════════
STATE И PARAMS
═══════════════════════════════════════════════════════════════════════════════

ScopedLogger получает реальные state и params при создании. Это позволяет
использовать шаблоны вида {%state.total} и {%params.amount} в сообщениях
логов без необходимости дублировать значения через kwargs.

ActionProductMachine создаёт ScopedLogger в _call_aspect, передавая
текущий state конвейера и params действия. Для аспектов state содержит
все данные, накопленные предыдущими regular-аспектами.

Пользовательские данные, переданные через **kwargs в info/warning/error/debug,
попадают в namespace var и доступны через {%var.key}.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._call_aspect(...)
        │
        │  Создаёт ScopedLogger с координатами аспекта, state и params
        ▼
    ScopedLogger(coordinator, nest_level, machine, mode, action, aspect,
                 context, state, params)
        │
        │  аспект вызывает box.info("сообщение", key=value)
        ▼
    ScopedLogger._emit("info", "сообщение", key=value)
        │
        │  Формирует var = {"level": "info", "key": value}
        │  Использует заранее созданный LogScope
        │  Передаёт реальные state и params
        ▼
    LogCoordinator.emit(message, var, scope, ctx, state, params, indent)
        │
        ▼
    [Logger1, Logger2, ...] — каждый фильтрует и пишет

═══════════════════════════════════════════════════════════════════════════════
SCOPE И ПЕРЕМЕННЫЕ
═══════════════════════════════════════════════════════════════════════════════

LogScope создаётся один раз в конструкторе ScopedLogger с фиксированным
порядком ключей: machine, mode, action, aspect. Этот порядок определяет
результат scope.as_dotpath() и используется в фильтрах логгеров.

Уровень логирования (info, warning, error, debug) передаётся в var
под ключом "level". Пользовательские данные передаются через **kwargs
и попадают в var рядом с level.

Пять namespace доступны в шаблонах:
- {%var.key}           — пользовательские kwargs + level
- {%state.field}       — текущее состояние конвейера аспектов
- {%params.field}      — входные параметры действия
- {%context.user.id}   — контекст выполнения
- {%scope.action}      — координаты в конвейере

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Внутри аспекта (через ToolsBox):

    # Данные из state и params подставляются автоматически:
    await box.info("Итого: {%state.total}, пользователь: {%params.user_id}")

    # Пользовательские данные через kwargs → namespace var:
    await box.info("Платёж обработан", txn_id=txn_id, amount=params.amount)
    # В шаблоне: "Транзакция {%var.txn_id} на сумму {%var.amount}"

    # Условные конструкции с данными из state:
    await box.info("Риск: {iif({%state.total} > 100000; 'HIGH'; 'LOW')}")

    # Контекст пользователя:
    await box.info("Запрос от {%context.user.user_id}")
"""

from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope


class ScopedLogger:
    """
    Логгер, привязанный к scope текущего аспекта.

    Создаётся ActionProductMachine для каждого вызова аспекта.
    Все аспекты получают ScopedLogger через ToolsBox и используют
    его методы info/warning/error/debug для логирования.

    Методы info, warning, error, debug отправляют сообщение через
    LogCoordinator, автоматически добавляя ключ "level" и пользовательские
    kwargs в var. State и params передаются из конструктора — они
    содержат реальные данные конвейера, а не пустые заглушки.

    Атрибуты:
        _coordinator : LogCoordinator
            Координатор логирования (шина).
        _nest_level : int
            Уровень вложенности вызова действия.
        _machine_name : str
            Имя класса машины (например, "ActionProductMachine").
        _mode : str
            Режим выполнения (например, "test", "production").
        _action_name : str
            Полное имя класса действия (включая модуль).
        _aspect_name : str
            Имя метода-аспекта.
        _context : Context
            Контекст выполнения (пользователь, запрос, окружение).
        _state : BaseState
            Текущее состояние конвейера аспектов. Содержит данные,
            накопленные предыдущими regular-аспектами. Доступно
            в шаблонах через {%state.field}.
        _params : BaseParams
            Входные параметры действия. Доступны в шаблонах
            через {%params.field}.
        _scope : LogScope
            Заранее созданный scope с фиксированным порядком ключей.
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
    ) -> None:
        """
        Инициализирует привязанный логгер.

        Создаёт LogScope с фиксированным порядком ключей:
        machine, mode, action, aspect. Этот порядок определяет
        результат scope.as_dotpath().

        Аргументы:
            coordinator: координатор логирования (шина).
            nest_level: уровень вложенности вызова действия.
            machine_name: имя класса машины (например, "ActionProductMachine").
            mode: режим выполнения (например, "test", "production").
            action_name: полное имя класса действия (включая модуль).
            aspect_name: имя метода-аспекта.
            context: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера аспектов. Если None,
                   создаётся пустой BaseState(). Передаётся в LogCoordinator
                   при каждом вызове, доступно в шаблонах через {%state.field}.
            params: входные параметры действия. Если None, создаётся
                    пустой BaseParams(). Передаётся в LogCoordinator
                    при каждом вызове, доступно в шаблонах через {%params.field}.
        """
        self._coordinator = coordinator
        self._nest_level = nest_level
        self._machine_name = machine_name
        self._mode = mode
        self._action_name = action_name
        self._aspect_name = aspect_name
        self._context = context
        self._state = state if state is not None else BaseState()
        self._params = params if params is not None else BaseParams()

        # Создаём scope с фиксированным порядком ключей.
        # Порядок: machine, mode, action, aspect.
        self._scope = LogScope(
            machine=machine_name,
            mode=mode,
            action=action_name,
            aspect=aspect_name,
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
        # Используется системный уровень, пользовательский игнорируется.
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
                     {%context.user.id}, {%scope.action}, {iif(...)}.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("info", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня WARNING.

        Аргументы:
            message: текст сообщения. Поддерживает шаблоны.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("warning", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня ERROR.

        Аргументы:
            message: текст сообщения. Поддерживает шаблоны.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("error", message, **kwargs)

    async def debug(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня DEBUG.

        Аргументы:
            message: текст сообщения. Поддерживает шаблоны.
            **kwargs: пользовательские данные → namespace var.
        """
        await self._emit("debug", message, **kwargs)
