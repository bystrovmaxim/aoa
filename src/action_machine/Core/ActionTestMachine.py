# src/action_machine/Core/ActionTestMachine.py
"""
Test action machine with mock support (asynchronous version).

Inherits from ActionProductMachine and is fully asynchronous (like its parent).
Allows dependency substitution via a mock dictionary.

Изменения (этап 0–1):
- Публичный метод run() теперь не принимает resources (как и в родителе).
- Добавлен приватный _run_internal(), который принимает resources и вызывает родительский.
- _get_factory больше не принимает external_resources, так как DependencyFactory их не хранит.
- build_factory использует только моки и не передаёт external_resources.
- Обновлены комментарии.
"""

from typing import Any, TypeVar, cast

from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Core.MockAction import MockAction
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionTestMachine(ActionProductMachine):
    """
    Test machine with a convenient API for dependency substitution (asynchronous).

    Accepts a mock dictionary in the constructor: {class: value}.
    The value can be:
    - a MockAction instance (used as is)
    - a BaseAction instance (will go through the aspect pipeline)
    - a BaseResult (will be wrapped in a MockAction)
    - a callable (used as side_effect)
    - any other object (returned as is via resolve())

    The run method is asynchronous (as in the parent).
    For synchronous use, wrap it in asyncio.run().
    """

    def __init__(
        self,
        mocks: dict[type[Any], Any] | None = None,
        mode: str = "test",
        log_coordinator: LogCoordinator | None = None,
    ) -> None:
        """
        Initializes the test machine.

        Args:
            mocks: substitution dictionary {dependency_class: mock_value}.
            mode: execution mode (default "test"). Passed to parent.
            log_coordinator: logging coordinator. If not specified, the parent
                             will create a coordinator with default ConsoleLogger.
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
        Transforms the passed value into an object suitable for use in the factory.

        Args:
            value: mock value from the dictionary.

        Returns:
            MockAction, BaseAction, or any other object.
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
        Internal execution method that allows passing resources.

        This is used to inject mocks as resources when running child actions
        or when the test machine needs to pass resources explicitly.

        Args:
            context: execution context.
            action: action instance.
            params: input parameters.
            resources: external resources (mocks or other objects).
            connections: resource managers.
            nested_level: current nesting level.

        Returns:
            Action result.
        """
        # Для MockAction используем прямой вызов (без аспектов)
        if isinstance(action, MockAction):
            return cast(R, action.run(params))
        # Для обычных действий вызываем родительский _run_internal
        return await super()._run_internal(context, action, params, resources, connections, nested_level)

    def _get_factory(self, action_class: type[Any]) -> DependencyFactory:
        """
        Returns the dependency factory for the action class,
        taking mocks into account.

        Overrides parent to inject mocks as resources when building the factory.
        The factory is created without external resources (mocks are injected
        via the ToolsBox at runtime, not through the factory).
        """
        # We don't pass external_resources to DependencyFactory anymore.
        # Instead, mocks will be available via ToolsBox.resolve which checks
        # the resources dictionary passed to _run_internal.
        # So we just call parent to get a factory without external resources.
        return super()._get_factory(action_class)

    def build_factory(self, action_class: type[Any]) -> DependencyFactory:
        """
        Returns a factory for testing individual aspects (without external resources).
        """
        deps_info = getattr(action_class, "_dependencies", [])
        return DependencyFactory(deps_info)