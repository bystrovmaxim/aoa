# ActionMachine/Core/DependencyFactory.py
"""
Dependency factory for actions.
Supports creating and caching dependencies, as well as asynchronous execution
of nested actions with automatic wrapping of connections.
"""

from typing import Any

from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseActionMachine import BaseActionMachine
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager


class DependencyFactory:
    """
    Dependency factory for actions.

    Creates and caches instances of dependencies declared via @depends.
    When external resources (external_resources) are present, they are used with priority.
    Provides a method for asynchronously launching nested actions
    with automatic wrapping of connections via wrapper_class.
    """

    def __init__(
        self,
        machine: BaseActionMachine,
        deps_info: list[dict[str, Any]],
        external_resources: dict[type[Any], Any] | None = None,
    ) -> None:
        """
        Initializes the factory.

        Args:
            machine: instance of the action machine (for launching nested actions).
            deps_info: list of dictionaries with dependency information (from @depends).
            external_resources: dictionary of external resources that have priority.
        """
        self._machine: BaseActionMachine = machine
        self._deps: dict[type[Any], dict[str, Any]] = {info["class"]: info for info in deps_info}
        self._external: dict[type[Any], Any] = external_resources or {}
        self._instances: dict[type[Any], Any] = {}

    def get(self, klass: type[Any]) -> Any:
        """
        Returns an instance of the dependency of the specified class.

        If the class is present in external resources, the external instance is returned.
        Otherwise, if the instance has already been created, it is returned from the cache.
        Otherwise, a new instance is created via a factory or the default constructor.

        Args:
            klass: dependency class.

        Returns:
            Dependency instance.

        Raises:
            ValueError: if the dependency is not declared via @depends and is not present in external resources.
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
        Wraps each connection in its wrapper class for passing to child actions.

        For each connection:
        1. Calls get_wrapper_class() to obtain the wrapper type.
        2. If wrapper_class is not None – creates an instance of the wrapper,
           passing the original connection to the constructor.
        3. If wrapper_class is None – passes the connection as is (no wrapper).

        This ensures that child actions cannot manage transactions
        (open/commit/rollback), but can execute queries (execute).
        When nested further, the wrapper is wrapped again (wrapper around wrapper),
        which also prohibits transaction management.

        Args:
            connections: original dictionary of resource managers.

        Returns:
            New dictionary with wrapped (or original) resource managers.
        """
        wrapped: dict[str, BaseResourceManager] = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                # wrapper_class is a concrete class (e.g., WrapperConnectionManager)
                # whose __init__ takes the original manager as an argument.
                # Cast to Any to avoid mypy complaints about BaseResourceManager.__init__
                # signature, which declares no parameters (concrete classes declare their own).
                wrapped_instance: Any = wrapper_class(connection)  # type: ignore[call-arg]
                wrapped[key] = wrapped_instance
            else:
                wrapped[key] = connection
        return wrapped

    async def run_action(
        self,
        context: Context,
        action_class: type[BaseAction[Any, Any]],
        params: BaseParams,
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> BaseResult:
        """
        Asynchronously runs the specified action with the given parameters and resources.

        If connections are passed, each connection is wrapped via get_wrapper_class()
        before being passed to the child action. This ensures that child actions
        cannot manage transactions (open/commit/rollback), but can execute queries.

        Args:
            context: execution context for this request.
            action_class: action class to run.
            params: input parameters.
            resources: dictionary of resources to pass to the child action (optional).
            connections: dictionary of resource managers (optional).

        Returns:
            Result of the action execution.
        """
        instance = self.get(action_class)

        # Wrap connections for the child action
        wrapped_connections: dict[str, BaseResourceManager] | None = None
        if connections is not None:
            wrapped_connections = self._wrap_connections(connections)

        return await self._machine.run(context, instance, params, resources=resources, connections=wrapped_connections)