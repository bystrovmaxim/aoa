# ActionMachine/Core/CoreHelper.py
"""
Вспомогательные утилиты для ядра ActionMachine.
Содержит статические методы для работы с асинхронностью и другими общими задачами.
"""

import asyncio
from typing import TypeVar, Callable, Any

T = TypeVar('T')


class CoreHelper:
    """Набор вспомогательных статических методов."""

    @staticmethod
    async def run_in_thread(func: Callable[..., T], *args: Any) -> T:
        """
        Запускает синхронную блокирующую функцию в отдельном потоке.
        Позволяет выполнять тяжёлые вычисления или вызывать синхронные библиотеки,
        не блокируя event loop.

        Аргументы:
            func: синхронная функция для выполнения.
            *args: позиционные аргументы, передаваемые в функцию.

        Возвращает:
            Результат выполнения функции.

        Пример:
            result = await CoreHelper.run_in_thread(heavy_computation, arg1, arg2)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)