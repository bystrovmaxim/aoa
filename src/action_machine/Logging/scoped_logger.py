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
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine._call_aspect(...)
        │
        │  Создаёт ScopedLogger с координатами аспекта
        ▼
    ScopedLogger(coordinator, nest_level, machine, mode, action, aspect, context)
        │
        │  aspect вызывает box.info("сообщение", key=value)
        ▼
    ScopedLogger._emit("info", "сообщение", key=value)
        │
        │  Формирует var = {"level": "info", "key": value}
        │  Использует заранее созданный LogScope
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

State и params не передаются автоматически — ScopedLogger отправляет
пустые BaseState() и BaseParams(). Если аспекту нужно включить state
или params в лог, он передаёт их через kwargs:
    await box.info("Обработка", total=state.get("total"))

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Внутри аспекта (через ToolsBox):
    await box.info("Платёж обработан", txn_id=txn_id, amount=params.amount)
    await box.warning("Сумма превышает лимит", amount=params.amount)
    await box.error("Ошибка при обработке", error=str(e))
    await box.debug("Отладочная информация", state=state.to_dict())
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
    kwargs в var.

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
        """
        self._coordinator = coordinator
        self._nest_level = nest_level
        self._machine_name = machine_name
        self._mode = mode
        self._action_name = action_name
        self._aspect_name = aspect_name
        self._context = context

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

        Аргументы:
            lvl: уровень логирования (info, warning, error, debug).
            message: текст сообщения (может содержать шаблоны {%...}
                     и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
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
            state=BaseState(),      # state не передаётся автоматически
            params=BaseParams(),    # params не передаются автоматически
            indent=self._nest_level,
        )

    async def info(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня INFO.

        Аргументы:
            message: текст сообщения.
            **kwargs: пользовательские данные.
        """
        await self._emit("info", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня WARNING.

        Аргументы:
            message: текст сообщения.
            **kwargs: пользовательские данные.
        """
        await self._emit("warning", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня ERROR.

        Аргументы:
            message: текст сообщения.
            **kwargs: пользовательские данные.
        """
        await self._emit("error", message, **kwargs)

    async def debug(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня DEBUG.

        Аргументы:
            message: текст сообщения.
            **kwargs: пользовательские данные.
        """
        await self._emit("debug", message, **kwargs)
