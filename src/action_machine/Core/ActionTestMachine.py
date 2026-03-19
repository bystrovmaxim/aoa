# ActionMachine/Core/ActionTestMachine.py
"""
Test action machine with mock support (asynchronous version).

Inherits from ActionProductMachine and is fully asynchronous (like its parent).
Allows dependency substitution via a mock dictionary.

The constructor now accepts mode (passed to parent) and log_coordinator.
Default mode is "test", which corresponds to testing mode.
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
    - any other object (returned as is via get())

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
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Asynchronously runs the action. If action is a MockAction,
        it is called directly, bypassing the aspect pipeline.
        Otherwise, standard asynchronous execution through aspects is performed.

        Args:
            context: execution context for this request.
            action: action instance.
            params: input parameters.
            resources: dictionary of external resources.
            connections: dictionary of resource managers.

        Returns:
            Result of the action execution.
        """
        if isinstance(action, MockAction):
            # MockAction.run returns BaseResult, but in the test context
            # we are confident it matches the expected type R.
            return cast(R, action.run(params))
        return await super().run(context, action, params, resources=resources, connections=connections)

    def _get_factory(
        self, action_class: type[Any], external_resources: dict[type[Any], Any] | None = None
    ) -> DependencyFactory:
        """
        Returns the dependency factory for the action class,
        taking mocks and external resources into account.

        Priority: external_resources > prepared_mocks > standard dependencies.
        """
        deps_info = getattr(action_class, "_dependencies", [])
        all_resources: dict[type[Any], Any] = dict(self._prepared_mocks)
        if external_resources:
            # External resources override mocks
            all_resources.update(external_resources)
        return DependencyFactory(self, deps_info, all_resources)

    def build_factory(self, action_class: type[Any]) -> DependencyFactory:
        """
        Returns a factory for testing individual aspects (without external resources).
        """
        deps_info = getattr(action_class, "_dependencies", [])
        return DependencyFactory(self, deps_info, self._prepared_mocks)