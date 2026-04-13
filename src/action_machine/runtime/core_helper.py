# src/action_machine/runtime/core_helper.py
"""
Вспомогательные утилиты для ядра ActionMachine.
Содержит статические methodы для работы с асинхронностью и другими общими задачами.
"""

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class CoreHelper:
    """Набор вспомогательных статических methodов."""

    @staticmethod
    async def run_in_thread(func: Callable[..., T], *args: Any) -> T:
        """
        Запускает синхронную блокирующую функцию в отдельном потоке.
        Позволяет выполнять тяжёлые вычисления или вызывать синхронные библиотеки,
        не блокируя event loop.

        Args:
            func: синхронная функция для выполнения.
            *args: позиционные аргументы, передаваемые в функцию.

        Returns:
            Результат выполнения функции.

        Пример:
            result = await CoreHelper.run_in_thread(heavy_computation, arg1, arg2)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)
