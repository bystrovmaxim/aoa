# packages/aoa-action-machine/src/aoa/action_machine/runtime/tools_box.py
"""
Frozen toolbox passed into every action aspect as ``box``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

- Resolve dependencies: ``resolve(cls, *args, **kwargs)``.
- Run child actions: ``run(action_class, params, connections)``.
- Log: ``info`` / ``warning`` / ``critical`` with mandatory ``Channel`` first.

Callers pass a ``ScopedLogger`` and a ``DependencyFactory`` (for example built from the
wired ``action_node`` interchange ``@depends`` edges via ``resolved_dependency_infos()``).

═══════════════════════════════════════════════════════════════════════════════
CONTEXT PRIVACY — KEY INVARIANT
═══════════════════════════════════════════════════════════════════════════════

``ToolsBox`` does **not** store ``Context`` at all (no attribute, mangled or
otherwise). Aspects therefore cannot reach execution context through ``box``,
even via ``object.__getattribute__`` tricks.

- **Logging:** ``ScopedLogger`` passed into ``ToolsBox`` holds ``Context`` for
  template placeholders (e.g. ``{%context.user.id}``); that is internal to the
  logger, not exposed on ``box``.
- **Nested runs:** ``run_child`` is a closure created by the machine; it
  captures ``Context`` for ``_run_internal`` — ``ToolsBox.run()`` does not read
  context from fields.

The only way an aspect reads context data is ``ContextView``, injected by
``AspectExecutor`` / ``SagaCoordinator`` / ``ErrorHandlerExecutor`` when
``@context_requires`` is present. Unrequested keys → ``ContextAccessError``.

═══════════════════════════════════════════════════════════════════════════════
FROZEN CORE TYPES
═══════════════════════════════════════════════════════════════════════════════

Context privacy and immutable state/results share one idea: aspects run in a
sandbox (frozen ``State``; no ``Context`` on ``box`` except via ``ContextView``).

═══════════════════════════════════════════════════════════════════════════════
ROLLUP
═══════════════════════════════════════════════════════════════════════════════

``rollup`` is stored on ``ToolsBox`` and forwarded through resolves and nested
``run`` calls.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine._run_internal(...)
        │
        ├── ScopedLogger(..., action_node, context, params, …)
        └── ToolsBox(
                run_child=partial(_run_internal, …),
                resources=…, log=…,
                nested_level=…, rollup=…,
                factory=DependencyFactory(action_node.resolved_dependency_infos()))
                │
                ▼
            ToolsBox instance
        │
        ├── resolve(cls, *args, **kwargs)
        ├── run(action_class, params)
        └── info / warning / critical → ScopedLogger

"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from aoa.action_machine.logging.channel import Channel
from aoa.action_machine.logging.scoped_logger import ScopedLogger
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.dependency_factory import DependencyFactory

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ToolsBox:
    """
    Frozen toolbox: dependencies, child ``run``, and channel-scoped logging.

    One instance per nesting level. Does **not** expose ``Context`` on the box.
    """

    __slots__ = (
        "__factory",
        "__log",
        "__nested_level",
        "__resources",
        "__rollup",
        "__run_child",
    )

    # Type hints for private attributes (mypy/pylint)
    __run_child: Callable[..., Awaitable[BaseResult]]
    __factory: DependencyFactory
    __resources: dict[type[Any], Any] | None
    __log: ScopedLogger
    __nested_level: int
    __rollup: bool

    def __init__(
        self,
        run_child: Callable[..., Awaitable[BaseResult]],
        resources: dict[type[Any], Any] | None,
        log: ScopedLogger,
        nested_level: int,
        rollup: bool = False,
        *,
        factory: DependencyFactory,
    ) -> None:
        """
        Initialize ToolsBox.

        Args:
            run_child: callback that runs child action (closure).
            resources: external resource map (for example test mocks).
            log: aspect-scoped logger (context is internal for templates).
            nested_level: current execution nesting level.
            rollup: transaction auto-rollback mode flag.
            factory: stateless dependency factory (from interchange snapshot or cloned for aspects).
        """
        object.__setattr__(self, "_ToolsBox__run_child", run_child)
        object.__setattr__(self, "_ToolsBox__factory", factory)
        object.__setattr__(self, "_ToolsBox__resources", resources)
        object.__setattr__(self, "_ToolsBox__log", log)
        object.__setattr__(self, "_ToolsBox__nested_level", nested_level)
        object.__setattr__(self, "_ToolsBox__rollup", rollup)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"ToolsBox is a frozen object. Attribute write for '{name}' is forbidden."
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"ToolsBox is a frozen object. Attribute deletion for '{name}' is forbidden."
        )

    @property
    def run_child(self) -> Callable[..., Awaitable[BaseResult]]:
        return self.__run_child

    @property
    def factory(self) -> DependencyFactory:
        return self.__factory

    @property
    def resources(self) -> dict[type[Any], Any] | None:
        return self.__resources

    @property
    def nested_level(self) -> int:
        return self.__nested_level

    @property
    def rollup(self) -> bool:
        return self.__rollup

    def resolve(self, cls: type[Any], *args: Any, **kwargs: Any) -> Any:
        """
        Return dependency instance for requested class.

        Two-level lookup:
        1. Check ``resources`` first (external resources/mocks).
        2. Fallback to ``factory.resolve()``.
        """
        if self.__resources and cls in self.__resources:
            return self.__resources[cls]
        return self.__factory.resolve(cls, *args, rollup=self.__rollup, **kwargs)

    def _wrap_connections(
        self, connections: dict[str, BaseResource] | None,
    ) -> dict[str, BaseResource] | None:
        """
        Wrap each resource with its wrapper class for child-action propagation.
        """
        if connections is None:
            return None
        wrapped: dict[str, BaseResource] = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                wrapped[key] = wrapper_class(connection) # type: ignore[call-arg]
            else:
                wrapped[key] = connection
        return wrapped

    async def run(
        self,
        action_class: type[BaseAction[P, R]],
        params: P,
        connections: dict[str, BaseResource] | None = None,
    ) -> R:
        """
        Run child action; ``Context`` is propagated by ``run_child`` closure.
        """
        action_instance = action_class()
        wrapped_connections = self._wrap_connections(connections)
        result = await self.__run_child(
            action=action_instance,
            params=params,
            connections=wrapped_connections,
        )
        return cast("R", result)

    async def info(
        self, channels: Channel, message: str, **kwargs: Any,
    ) -> None:
        await self.__log.info(channels, message, **kwargs)

    async def warning(
        self, channels: Channel, message: str, **kwargs: Any,
    ) -> None:
        await self.__log.warning(channels, message, **kwargs)

    async def critical(
        self, channels: Channel, message: str, **kwargs: Any,
    ) -> None:
        await self.__log.critical(channels, message, **kwargs)
