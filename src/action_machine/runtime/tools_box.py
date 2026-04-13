# src/action_machine/runtime/tools_box.py
"""
Frozen toolbox passed into every action aspect as ``box``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

- Resolve dependencies: ``resolve(cls, *args, **kwargs)``.
- Run child actions: ``run(action_class, params, connections)``.
- Log: ``info`` / ``warning`` / ``critical`` with mandatory ``Channel`` first.

The embedded ``ScopedLogger`` is created by ``ToolsBoxFactory`` (or test bench)
with ``domain=resolve_domain(action_cls)`` so ``var`` carries domain metadata.

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
        │  Builds ToolsBox with:
        │  - run_child: nested-run closure (captures Context)
        │  - factory: DependencyFactory for current action
        │  - resources: external deps (mocks in tests)
        │  - log: ScopedLogger(domain=resolve_domain(...), …)
        │  - nested_level, rollup
        ▼
    ToolsBox
        │
        ├── resolve(cls, *args, **kwargs) → resources then factory
        ├── run(action, params)           → instantiate, wrap connections
        ├── info / warning / critical     → delegate to ScopedLogger

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Per-aspect frozen API surface (resolve, run, log).
CONTRACT: no Context on instance; log methods require Channel.
INVARIANTS: rollup propagation; ScopedLogger owns context for templates only.
FLOW: machine builds ToolsBox → aspect uses box.* → logger emits via coordinator.
FAILURES: dependency / run errors propagate; logging uses same coordinator rules.
EXTENSION POINTS: none on box shape; custom factories build different loggers.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.intents.logging.channel import Channel
from action_machine.intents.logging.scoped_logger import ScopedLogger
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource_manager import BaseResourceManager

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

    # Аннотации типов для приватных атрибутов (для mypy и pylint)
    __run_child: Callable[..., Awaitable[BaseResult]]
    __factory: DependencyFactory
    __resources: dict[type[Any], Any] | None
    __log: ScopedLogger
    __nested_level: int
    __rollup: bool

    def __init__(
        self,
        run_child: Callable[..., Awaitable[BaseResult]],
        factory: DependencyFactory,
        resources: dict[type[Any], Any] | None,
        log: ScopedLogger,
        nested_level: int,
        rollup: bool = False,
    ) -> None:
        """
        Инициализирует ToolsBox.

        Args:
            run_child: функция для запуска дочернего действия (замыкание).
            factory: stateless-фабрика зависимостей.
            resources: словарь внешних ресурсов (моки в тестах).
            log: ScopedLogger, привязанный к текущему аспекту (context lives here for templates).
            nested_level: уровень вложенности вызова.
            rollup: флаг автоотката транзакций.
        """
        object.__setattr__(self, "_ToolsBox__run_child", run_child)
        object.__setattr__(self, "_ToolsBox__factory", factory)
        object.__setattr__(self, "_ToolsBox__resources", resources)
        object.__setattr__(self, "_ToolsBox__log", log)
        object.__setattr__(self, "_ToolsBox__nested_level", nested_level)
        object.__setattr__(self, "_ToolsBox__rollup", rollup)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"ToolsBox является frozen-объектом. Запись атрибута '{name}' запрещена."
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"ToolsBox является frozen-объектом. Удаление атрибута '{name}' запрещено."
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
        Returns экземпляр зависимости указанного класса.

        Двухуровневый поиск:
        1. Сначала ищет в resources (внешние ресурсы / моки).
        2. Если не найдено — делегирует в factory.resolve().
        """
        if self.__resources and cls in self.__resources:
            return self.__resources[cls]
        return self.__factory.resolve(cls, *args, rollup=self.__rollup, **kwargs)

    def _wrap_connections(
        self, connections: dict[str, BaseResourceManager] | None,
    ) -> dict[str, BaseResourceManager] | None:
        """
        Обёртывает каждый ресурс в его класс-обёртку для передачи в дочерние действия.
        """
        if connections is None:
            return None
        wrapped: dict[str, BaseResourceManager] = {}
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
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Запускает дочернее действие; ``Context`` прокидывает замыкание ``run_child``.
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
