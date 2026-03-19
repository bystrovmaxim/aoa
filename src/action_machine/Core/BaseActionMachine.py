"""
Abstract base class for all action machines.
Defines the asynchronous run method and the synchronous sync_run wrapper.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from action_machine.Context.context import Context
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class BaseActionMachine(ABC):
    """
    Abstract action machine.

    All implementations (production, test) inherit from this class
    and implement the asynchronous run method. For synchronous usage,
    the sync_run method is provided, which safely runs the async pipeline
    outside an already running event loop.
    """

    @abstractmethod
    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Asynchronously executes the action and returns the result.

        This method should be used inside an asynchronous context
        (e.g., in FastAPI endpoints, aiohttp handlers, asyncio applications).
        It must be called with the await keyword.

        Args:
            context: execution context for this specific request
                     (contains user, request, and environment information).
            action: action instance to execute.
            params: action input parameters.
            resources: dictionary of external resources (key – resource class,
                       value – instance) that will be passed to the dependency
                       factory with priority.
            connections: dictionary of resource managers (connections),
                         key – string connection name (matches the name in @connection),
                         value – BaseResourceManager instance.
                         Passed to all aspects as is.
                         When passed to child actions via DependencyFactory,
                         each connection is wrapped using get_wrapper_class().

        Returns:
            Result of the action execution.
        """
        pass

    def sync_run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Synchronous wrapper for use outside an async context.

        Suitable for command‑line scripts, Celery tasks, Django views without
        async support, and any other synchronous environment. The method creates
        a new event loop, executes the action, and returns the result.

        If called inside an already running event loop (e.g., accidentally in
        a FastAPI endpoint), a RuntimeError is raised with a clear message.

        Args:
            context: execution context for this specific request.
            action: action instance.
            params: input parameters.
            resources: external resources (optional).
            connections: dictionary of resource managers (optional).

        Returns:
            Result of the action execution.
        """
        import asyncio

        try:
            # Check if an event loop is already running
            asyncio.get_running_loop()
            # If we reached this point, a loop is running – this is a usage error
            raise RuntimeError(
                "sync_run() called inside an already running asyncio loop. "
                "In asynchronous code, use await run()."
            )
        except RuntimeError:
            # No running loop – we can safely use asyncio.run()
            return asyncio.run(self.run(context, action, params, resources, connections))