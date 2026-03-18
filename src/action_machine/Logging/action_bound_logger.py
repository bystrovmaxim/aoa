# ActionMachine/Logging/action_bound_logger.py
"""
Логер, привязанный к текущему аспекту.

Автоматически добавляет координаты выполнения в LogScope:
- machine: имя класса машины (например, "ActionProductMachine")
- mode: режим выполнения (например, "test", "production")
- action: полное имя класса действия (включая модуль)
- aspect: имя метода-аспекта

Уровень логирования передаётся в var как ключ "level".
Пользовательские данные передаются только через kwargs и попадают в var.
"""

from typing import Any

from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Logging.log_scope import LogScope


class ActionBoundLogger:
    """
    Логер, привязанный к текущему аспекту.

    Создаётся ActionProductMachine для каждого вызова аспекта.
    Все аспекты обязаны принимать параметр `log` (шестой).

    Методы info, warning, error, debug отправляют сообщение через LogCoordinator,
    автоматически добавляя в var ключ `level` и пользовательские kwargs.
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
        Инициализирует привязанный логер.

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

        # Создаём скоуп с фиксированным порядком ключей.
        # Порядок: machine, mode, action, aspect.
        self._scope = LogScope(
            machine=machine_name,
            mode=mode,
            action=action_name,
            aspect=aspect_name,
        )

    async def _emit(self, lvl: str, message: str, **kwargs: Any) -> None:
        """
        Внутренний метод отправки сообщения.

        Аргументы:
            lvl: уровень логирования (info, warning, error, debug).
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, которые попадут в var.
        """
        # Удаляем ключ 'level' из kwargs, если он там есть (пользователь мог передать).
        # Мы используем системный уровень, поэтому пользовательский игнорируется.
        kwargs.pop("level", None)

        # В var кладём только уровень и пользовательские данные.
        var = {"level": lvl, **kwargs}

        await self._coordinator.emit(
            message=message,
            var=var,
            scope=self._scope,
            ctx=self._context,
            state=BaseState(),      # состояние не передаём автоматически
            params=BaseParams(),    # параметры не передаём автоматически
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