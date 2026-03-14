# ActionMachine/Core/DependencyFactory.py
"""
Фабрика зависимостей для действий.
Поддерживает создание и кэширование зависимостей, а также асинхронный запуск вложенных действий.
"""

from typing import Any, Dict, List, Type, Optional
from ActionMachine.Core.BaseActionMachine import BaseActionMachine
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseParams import BaseParams


class DependencyFactory:
    """
    Фабрика зависимостей для действий.

    Создаёт и кэширует экземпляры зависимостей, объявленных через @depends.
    При наличии внешних ресурсов (external_resources) использует их в приоритете.
    Предоставляет метод для асинхронного запуска вложенных действий.
    """

    def __init__(
        self,
        machine: BaseActionMachine,
        deps_info: List[Dict[str, Any]],
        external_resources: Optional[Dict[Type[Any], Any]] = None
    ) -> None:
        """
        Инициализирует фабрику.

        Аргументы:
            machine: экземпляр машины действий (для запуска вложенных действий).
            deps_info: список словарей с информацией о зависимостях (из @depends).
            external_resources: словарь внешних ресурсов, которые имеют приоритет.
        """
        self._machine = machine
        self._deps: Dict[Type[Any], Dict[str, Any]] = {info['class']: info for info in deps_info}
        self._external = external_resources or {}
        self._instances: Dict[Type[Any], Any] = {}

    def get(self, klass: Type[Any]) -> Any:
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
        if info['factory']:
            instance = info['factory']()
        else:
            instance = klass()
        self._instances[klass] = instance
        return instance

    async def run_action(
        self,
        action_class: Type[BaseAction[Any, Any]],
        params: BaseParams,
        resources: Optional[Dict[Type[Any], Any]] = None
    ) -> BaseResult:
        """
        Асинхронно запускает указанное действие с переданными параметрами и ресурсами.

        Аргументы:
            action_class: класс действия для запуска.
            params: входные параметры.
            resources: словарь ресурсов для передачи в дочернее действие (опционально).

        Возвращает:
            Результат выполнения действия.
        """
        instance = self.get(action_class)
        return await self._machine.run(instance, params, resources=resources)
