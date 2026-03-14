# ActionMachine/Core/BaseActionMachine.py
"""
Абстрактный базовый класс для всех машин действий.
Определяет асинхронный метод run и синхронную обёртку sync_run.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Optional, Dict, Type, Any

from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)


class BaseActionMachine(ABC):
    """
    Абстрактная машина действий.

    Все реализации (продуктовая, тестовая) наследуют от этого класса
    и реализуют асинхронный метод run. Для синхронного использования
    предоставляется метод sync_run, который безопасно запускает асинхронный
    конвейер вне уже работающего цикла событий.
    """

    @abstractmethod
    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        resources: Optional[Dict[Type[Any], Any]] = None
    ) -> R:
        """
        Асинхронно запускает действие и возвращает результат.

        Этот метод следует использовать внутри асинхронного контекста
        (например, в FastAPI-эндпоинтах, aiohttp-обработчиках, asyncio-приложениях).
        Вызывается с ключевым словом await.

        Аргументы:
            action: экземпляр действия для выполнения.
            params: входные параметры действия.
            resources: словарь внешних ресурсов (ключ – класс ресурса, значение – экземпляр),
                       которые будут переданы в фабрику зависимостей с приоритетом.

        Возвращает:
            Результат выполнения действия.
        """
        pass

    def sync_run(
        self,
        action: BaseAction[P, R],
        params: P,
        resources: Optional[Dict[Type[Any], Any]] = None
    ) -> R:
        """
        Синхронная обёртка для использования вне async-контекста.

        Подходит для скриптов командной строки, задач Celery, Django-представлений
        без поддержки async и любого другого синхронного окружения. Метод создаёт
        новый цикл событий, выполняет действие и возвращает результат.

        Если метод вызван внутри уже запущенного цикла событий (например,
        случайно в FastAPI-эндпоинте), будет выброшено исключение RuntimeError
        с понятным сообщением на русском языке.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы (опционально).

        Возвращает:
            Результат выполнения действия.
        """
        import asyncio
        try:
            # Проверяем, запущен ли уже event loop
            asyncio.get_running_loop()
            # Если дошли сюда, значит loop запущен – это ошибка
            raise RuntimeError(
                "Метод sync_run() предназначен для использования в синхронном коде "
                "без запущенного цикла событий (например, в скриптах, Celery-задачах, "
                "Django-представлениях без async). В асинхронном контексте (например, "
                "в FastAPI-эндпоинте) необходимо использовать await run()."
            )
        except RuntimeError:
            # Нет текущего запущенного loop – можно использовать asyncio.run()
            return asyncio.run(self.run(action, params, resources))
        