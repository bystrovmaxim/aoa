# src/action_machine/Core/ToolsBox.py
"""
ToolsBox – контейнер инструментов для аспектов действий.

Обеспечивает единый интерфейс для:
- Получения зависимостей (resolve)
- Запуска дочерних действий (run)
- Логирования (info, warning, error, debug)
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.dependencies.dependency_factory  import DependencyFactory
from action_machine.Logging.action_bound_logger import ActionBoundLogger
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ToolsBox:
    """
    Контейнер инструментов для аспектов.

    Предоставляет методы для работы с зависимостями, логированием и запуском
    дочерних действий. Создаётся один раз на уровень вложенности и передаётся
    во все аспекты вместо отдельных параметров deps и log.
    """

    def __init__(
        self,
        run_child: Callable[..., Awaitable[BaseResult]],
        factory: DependencyFactory,
        resources: dict[type[Any], Any] | None,
        context: Context,
        log: ActionBoundLogger,
        nested_level: int,
    ) -> None:
        """
        Инициализирует ToolsBox.

        Аргументы:
            run_child: функция для запуска дочернего действия (замыкание,
                       предоставляемое машиной).
            factory: фабрика зависимостей для текущего действия.
            resources: словарь внешних ресурсов, переданных на этот уровень.
            context: контекст выполнения.
            log: логер, привязанный к текущему уровню (без аспекта).
            nested_level: уровень вложенности.
        """
        self.__run_child = run_child
        self.__factory = factory
        self.__resources = resources
        self.__context = context
        self.__log = log
        self.__nested_level = nested_level

    @property
    def run_child(self) -> Callable[..., Awaitable[BaseResult]]:
        """Возвращает функцию запуска дочернего действия."""
        return self.__run_child

    @property
    def factory(self) -> DependencyFactory:
        """Возвращает фабрику зависимостей."""
        return self.__factory

    @property
    def resources(self) -> dict[type[Any], Any] | None:
        """Возвращает словарь внешних ресурсов."""
        return self.__resources

    @property
    def context(self) -> Context:
        """Возвращает контекст выполнения."""
        return self.__context

    @property
    def nested_level(self) -> int:
        """Возвращает уровень вложенности."""
        return self.__nested_level

    def resolve(self, cls: type[Any]) -> Any:
        """
        Возвращает экземпляр зависимости указанного класса.

        Сначала ищет в __resources (если ресурс передан явно),
        затем в __factory.resolve (если зависимость объявлена через @depends).

        Args:
            cls: класс зависимости.

        Returns:
            Экземпляр зависимости.

        Raises:
            ValueError: если зависимость не найдена ни в ресурсах, ни в фабрике.
        """
        if self.__resources and cls in self.__resources:
            return self.__resources[cls]
        return self.__factory.resolve(cls)

    def _wrap_connections(
        self, connections: dict[str, BaseResourceManager] | None
    ) -> dict[str, BaseResourceManager] | None:
        """
        Обёртывает каждый ресурс в его класс-обёртку (если есть) для передачи в дочерние действия.

        Используется внутри run() для защиты дочерних действий от управления транзакциями.

        Args:
            connections: исходный словарь ресурсных менеджеров.

        Returns:
            Новый словарь с обёрнутыми ресурсами, или None если connections=None.
        """
        if connections is None:
            return None
        wrapped: dict[str, BaseResourceManager] = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                wrapped[key] = wrapper_class(connection)  # type: ignore[call-arg]
            else:
                wrapped[key] = connection
        return wrapped

    async def run(
        self,
        action_class: type[BaseAction[P, R]],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Запускает дочернее действие с текущими ресурсами и контекстом.

        Создаёт экземпляр действия, обёртывает connections (если переданы),
        и вызывает переданную функцию __run_child, которая реализует запуск
        через внутренний метод машины.

        Args:
            action_class: класс дочернего действия.
            params: параметры для дочернего действия.
            connections: словарь ресурсных менеджеров (опционально).

        Returns:
            Результат выполнения дочернего действия.
        """
        # Создаём экземпляр действия
        action_instance = action_class()

        # Обёртываем connections
        wrapped_connections = self._wrap_connections(connections)

        # Запускаем через замыкание, предоставленное машиной
        result = await self.__run_child(
            action=action_instance,
            params=params,
            connections=wrapped_connections,
        )
        return cast(R, result)

    # ----- Методы логирования (прокси к __log) -----

    async def info(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня INFO.

        Args:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.info(message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня WARNING.

        Args:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.warning(message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня ERROR.

        Args:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.error(message, **kwargs)

    async def debug(self, message: str, **kwargs: Any) -> None:
        """
        Отправляет сообщение уровня DEBUG.

        Args:
            message: текст сообщения (может содержать шаблоны {%...} и {iif(...)}).
            **kwargs: пользовательские данные, попадающие в var.
        """
        await self.__log.debug(message, **kwargs)