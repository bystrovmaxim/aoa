# src/action_machine/intents/connection/connection_decorator.py
"""
``@connection`` decorator for declaring external resource bindings.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@connection`` is part of the ActionMachine intent grammar. It declares that
an action uses an external resource (database, message queue, HTTP client, and
so on) managed by a ``ResourceManager``. At runtime, the machine validates
declared vs provided connections and passes them to aspects.

Each connection is identified by a string key used in aspects:
``connections["db"]``, ``connections["redis"]``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @connection(PostgresManager, key="db", description="Primary DB")
        │
        ▼  Decorator writes to cls._connection_info
    ConnectionInfo(cls=PostgresManager, key="db", description="Primary DB")
        │
        ▼  ConnectionIntentInspector reads _connection_info
    get_connections(cls) → (ConnectionInfo(...), ...)
        │
        ▼  ActionProductMachine._check_connections(action, connections, metadata)
    Compares declared keys (facet snapshot ``connections``) with provided runtime keys
        │
        ▼  Aspects receive connections["db"] (PostgresManager instance)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Applies only to classes (not functions, methods, or properties).
- ``klass`` must be a ``BaseResourceManager`` subclass.
- ``key`` must be a non-empty string.
- ``description`` must be a string.
- Duplicate keys in one class are forbidden.

═══════════════════════════════════════════════════════════════════════════════
INHERITANCE
═══════════════════════════════════════════════════════════════════════════════

On first ``@connection`` use for a subclass, decorator copies inherited
``_connection_info`` into subclass ``__dict__``. Child class inherits parent
connections, while new registrations do not mutate parent list.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    @connection(PostgresManager, key="db", description="Primary DB")
    @connection(RedisManager, key="cache", description="Cache")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Load data")
        async def load_data(self, params, state, box, connections):
            db = connections["db"]
            result = await db.execute("SELECT ...")
            return {"data": result}

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

    TypeError - invalid manager class, invalid target class, invalid ``key`` type,
                or invalid ``description`` type.
    ValueError - empty ``key`` or duplicate connection key.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Declarative class decorator for resource connection contracts.
CONTRACT: Store immutable ConnectionInfo records in class-level scratch list.
INVARIANTS: Manager subclass + ConnectionIntent + unique non-empty key required.
FLOW: decorator args validation -> class validation -> metadata registration.
FAILURES: TypeError/ValueError on invalid declaration shape or duplicates.
EXTENSION POINTS: New manager types only need BaseResourceManager compliance.
AI-CORE-END
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.resources.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Dataclass carrying one connection declaration
# ═════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ConnectionInfo:
    """
    Immutable record for one declared resource connection.

    Created by ``@connection`` and stored on ``cls._connection_info``.
    ``ConnectionIntentInspector`` builds the coordinator facet; the machine
    compares keys from the ``connections`` facet snapshot to the runtime
    ``connections`` mapping passed into ``run``.

    Attributes:
        cls: ``BaseResourceManager`` subclass (resource type).
        key: Non-empty string key for ``connections[key]`` inside aspects.
        description: Human-readable label for introspection and docs.
    """
    cls: type
    key: str
    description: str = ""


# ═════════════════════════════════════════════════════════════════════════════
# Decorator argument validation (split out to keep complexity low)
# ═════════════════════════════════════════════════════════════════════════════


def _validate_connection_args(klass: Any, key: str, description: str) -> None:
    """
    Validate ``@connection`` decorator arguments.
    """
    if not isinstance(klass, type):
        raise TypeError(
            f"@connection expects a class, got {type(klass).__name__}: {klass!r}. "
            f"Pass a resource manager class."
        )

    if not issubclass(klass, BaseResourceManager):
        raise TypeError(
            f"@connection: class {klass.__name__} is not a BaseResourceManager "
            f"subclass. Resource manager must inherit BaseResourceManager."
        )

    if not isinstance(key, str):
        raise TypeError(
            f"@connection: key must be a string, "
            f"got {type(key).__name__}: {key!r}."
        )

    if not key.strip():
        raise ValueError(
            "@connection: key cannot be empty. "
            "Provide a key identifier, for example 'db'."
        )

    if not isinstance(description, str):
        raise TypeError(
            f"@connection: description must be a string, "
            f"got {type(description).__name__}."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Main decorator
# ═════════════════════════════════════════════════════════════════════════════


def connection(klass: Any, *, key: str, description: str = "") -> Callable[[type], type]:
    """
    Class-level decorator declaring an external resource connection.
    """
    # Argument validation (delegated to helper)
    _validate_connection_args(klass, key, description)

    def decorator(cls: Any) -> Any:
        """
        Internal decorator applied to the target class.
        """
        # Target must be a class
        if not isinstance(cls, type):
            raise TypeError(
                f"@connection can only be applied to classes. "
                f"Got object of type {type(cls).__name__}: {cls!r}."
            )

        # Ensure subclass-local declaration list on first use
        if '_connection_info' not in cls.__dict__:
            cls._connection_info = list(getattr(cls, '_connection_info', []))

        # Duplicate key check
        if any(info.key == key for info in cls._connection_info):
            raise ValueError(
                f"@connection(key=\"{key}\"): key \"{key}\" is already declared "
                f"for class {cls.__name__}. Each key must be unique."
            )

        # Register connection declaration
        cls._connection_info.append(
            ConnectionInfo(cls=klass, key=key, description=description)
        )

        return cls

    return decorator
