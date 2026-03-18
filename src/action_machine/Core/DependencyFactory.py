"""
Фабрика зависимостей для действий.
Поддерживает создание и кэширование зависимостей, а также асинхронный запуск
вложенных действий с автоматическим оборачиванием connections.
"""

from typing import Any

from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseActionMachine import BaseActionMachine
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


class DependencyFactory:
    """
    Фабрика зависимостей для действий.

    Создаёт и кэширует экземпляры зависимостей, объявленных через @depends.
    При наличии внешних ресурсов (external_resources) использует их в приоритете.
    Предоставляет метод для асинхронного запуска вложенных действий
    с автоматическим оборачиванием connections через wrapper_class.
    """

    def __init__(
        self,
        machine: BaseActionMachine,
        deps_info: list[dict[str, Any]],
        external_resources: dict[type[Any], Any] | None = None,
    ) -> None:
        """
        Инициализирует фабрику.

        Аргументы:
            machine: экземпляр машины действий (для запуска вложенных действий).
            deps_info: список словарей с информацией о зависимостях (из @depends).
            external_resources: словарь внешних ресурсов, которые имеют приоритет.
        """
        self._machine: BaseActionMachine = machine
        self._deps: dict[type[Any], dict[str, Any]] = {info["class"]: info for info in deps_info}
        self._external: dict[type[Any], Any] = external_resources or {}
        self._instances: dict[type[Any], Any] = {}

    def get(self, klass: type[Any]) -> Any:
        """
        Возвращает экземпляр зависимости указанного класса.

        Если класс присутствует во внешних ресурсах, возвращается внешний экземпляр.
        Иначе, если экземпляр уже создан, возвращается из кэша.
        Иначе создаётся новый экземпляр через фабрику или конструктор по умолчанию.

        Аргументы:
            klass: класс зависимости.

        Возвращает:
            Экземпляр зависимости.

        Исключения:
            ValueError: если зависимость не объявлена через @depends и отсутствует во внешних ресурсах.
        """
        if klass in self._external:
            return self._external[klass]
        if klass in self._instances:
            return self._instances[klass]
        if klass not in self._deps:
            raise ValueError(f"Dependency {klass.__name__} not declared in @depends and not provided externally")
        info = self._deps[klass]
        if info["factory"]:
            instance = info["factory"]()
        else:
            instance = klass()
        self._instances[klass] = instance
        return instance

    def _wrap_connections(self, connections: dict[str, BaseResourceManager]) -> dict[str, BaseResourceManager]:
        """
        Оборачивает каждый connection в его wrapper-класс для передачи в дочерние действия.

        Для каждого connection:
        1. Вызывает get_wrapper_class() чтобы получить тип обёртки.
        2. Если wrapper_class не None — создаёт экземпляр обёртки, передавая
           оригинальный connection в конструктор.
        3. Если wrapper_class is None — передаёт connection как есть (без обёртки).

        Это гарантирует, что дочерние действия не могут управлять транзакциями
        (open/commit/rollback), но могут выполнять запросы (execute).
        При дальнейшей вложенности обёртка снова оборачивается (wrapper вокруг wrapper),
        что также запрещает управление транзакциями.

        Аргументы:
            connections: исходный словарь ресурсных менеджеров.

        Возвращает:
            Новый словарь с обёрнутыми (или оригинальными) ресурсными менеджерами.
        """
        wrapped: dict[str, BaseResourceManager] = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                # wrapper_class — это конкретный класс (например, WrapperConnectionManager),
                # чей __init__ принимает оригинальный менеджер как аргумент.
                # Приводим к Any, чтобы mypy не жаловался на сигнатуру BaseResourceManager.__init__,
                # которая не объявляет параметров (конкретные классы объявляют свои).
                wrapped_instance: Any = wrapper_class(connection)  # type: ignore[call-arg]
                wrapped[key] = wrapped_instance
            else:
                wrapped[key] = connection
        return wrapped

    async def run_action(
        self,
        action_class: type[BaseAction[Any, Any]],
        params: BaseParams,
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> BaseResult:
        """
        Асинхронно запускает указанное действие с переданными параметрами и ресурсами.

        Если передан connections, каждый connection оборачивается через get_wrapper_class()
        перед передачей в дочернее действие. Это гарантирует, что дочерние действия
        не могут управлять транзакциями (open/commit/rollback), но могут выполнять запросы.

        Аргументы:
            action_class: класс действия для запуска.
            params: входные параметры.
            resources: словарь ресурсов для передачи в дочернее действие (опционально).
            connections: словарь ресурсных менеджеров (опционально).

        Возвращает:
            Результат выполнения действия.
        """
        instance = self.get(action_class)

        # Оборачиваем connections для дочернего действия
        wrapped_connections: dict[str, BaseResourceManager] | None = None
        if connections is not None:
            wrapped_connections = self._wrap_connections(connections)

        return await self._machine.run(instance, params, resources=resources, connections=wrapped_connections)