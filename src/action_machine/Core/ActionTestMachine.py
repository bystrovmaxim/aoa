"""
Test action machine with mock support (asynchronous version).

Inherits from ActionProductMachine and is fully asynchronous (like its parent).
Allows dependency substitution via a mock dictionary.

Управление метаданными (зависимости) осуществляется через шлюз действия.
Фабрика зависимостей создаётся из шлюза, полученного через action.get_dependency_gate().
"""

from typing import Any, TypeVar, cast

from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.Core.MockAction import MockAction
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionTestMachine(ActionProductMachine):
    """
    Тестовая машина с удобным API для подстановки зависимостей (асинхронная).

    Принимает словарь моков в конструкторе: {class: value}.
    Значение может быть:
    - экземпляр MockAction (используется как есть)
    - экземпляр BaseAction (пройдёт через конвейер аспектов)
    - BaseResult (будет обёрнут в MockAction)
    - callable (используется как side_effect)
    - любой другой объект (возвращается как есть через resolve())

    Метод run является асинхронным (как в родителе).
    Для синхронного использования оберните в asyncio.run().
    """

    def __init__(
        self,
        mocks: dict[type[Any], Any] | None = None,
        mode: str = "test",
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Инициализирует тестовую машину.

        Аргументы:
            mocks: словарь подстановок {класс_зависимости: mock_значение}.
            mode: режим выполнения (по умолчанию "test"). Передаётся родителю.
            log_coordinator: координатор логирования. Если не указан, родитель
                             создаст координатор с ConsoleLogger по умолчанию.
        """
        super().__init__(
            mode=mode,
            log_coordinator=log_coordinator,
        )
        self._mocks: dict[type[Any], Any] = mocks or {}
        self._prepared_mocks: dict[type[Any], Any] = {}
        for cls, val in self._mocks.items():
            self._prepared_mocks[cls] = self._prepare_mock(val)

    def _prepare_mock(self, value: Any) -> Any:
        """
        Преобразует переданное значение в объект, пригодный для использования в фабрике.

        Аргументы:
            value: mock-значение из словаря.

        Возвращает:
            MockAction, BaseAction или любой другой объект.
        """
        if isinstance(value, MockAction):
            return value
        if isinstance(value, BaseAction):
            return value
        if callable(value):
            return MockAction(side_effect=value)
        if isinstance(value, BaseResult):
            return MockAction(result=value)
        return value

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Выполняет действие с поддержкой моков.

        Для MockAction использует прямой вызов (без аспектов).
        Для обычных действий вызывает _run_internal с моками как resources.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            connections: словарь менеджеров ресурсов.

        Возвращает:
            Результат выполнения действия.
        """
        # Для MockAction используем прямой вызов (без аспектов)
        if isinstance(action, MockAction):
            return cast(R, action.run(params))
        # Для обычных действий вызываем _run_internal с моками как resources
        return await self._run_internal(context, action, params, self._prepared_mocks, connections, 0)

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
    ) -> R:
        """
        Внутренний метод выполнения, позволяющий передавать ресурсы.

        Используется для внедрения моков как ресурсов при запуске дочерних действий
        или когда тестовой машине нужно явно передать ресурсы.

        Аргументы:
            context: контекст выполнения.
            action: экземпляр действия.
            params: входные параметры.
            resources: внешние ресурсы (моки или другие объекты).
            connections: менеджеры ресурсов.
            nested_level: текущий уровень вложенности.

        Возвращает:
            Результат действия.
        """
        # Для MockAction используем прямой вызов (без аспектов)
        if isinstance(action, MockAction):
            return cast(R, action.run(params))
        # Для обычных действий вызываем родительский _run_internal
        return await super()._run_internal(context, action, params, resources, connections, nested_level)

    def _get_factory(self, action: BaseAction[Any, Any]) -> DependencyFactory:
        """
        Возвращает фабрику зависимостей для действия, учитывая моки.

        Переопределяет родительский метод, чтобы создать фабрику на основе шлюза
        действия, но без внешних ресурсов (моки будут доступны через ToolsBox
        во время выполнения, а не через фабрику).

        Аргументы:
            action: экземпляр действия.

        Возвращает:
            DependencyFactory, связанную с действием.
        """
        # Моки передаются через resources в _run_internal, а не через фабрику.
        # Просто вызываем родительский метод для получения фабрики без внешних ресурсов.
        return super()._get_factory(action)

    def build_factory(self, action_class: type[BaseAction[Any, Any]]) -> DependencyFactory:
        """
        Возвращает фабрику для тестирования отдельных аспектов (без внешних ресурсов).

        Аргументы:
            action_class: класс действия, для которого создаётся фабрика.

        Возвращает:
            DependencyFactory, связанную с классом действия.
        """
        # Временный экземпляр для получения шлюза
        dummy = action_class()
        gate = dummy.get_dependency_gate()
        return DependencyFactory(gate)