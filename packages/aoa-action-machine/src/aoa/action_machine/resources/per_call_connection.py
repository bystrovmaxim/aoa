# packages/aoa-action-machine/src/aoa/action_machine/resources/per_call_connection.py
"""
Per-route / per-tool connection declarations and resolution.

``connections`` is a mapping from connection key (string, matches ``@connection``)
to either a ready ``BaseResource`` or a ``PerCallConnection`` — a **pair**: the
``factory`` that creates the resource for one call, and the ``finalize`` that
closes it and gives back whatever it borrowed.

The pair is mandatory as a pair. A resource created per call cannot be declared
without saying how it is closed, which is the whole reason ``finalize`` has no
default. ``resolve_connections`` builds the flat mapping a run receives;
:func:`~aoa.action_machine.resources.connection_scope.connection_scope` is what
applies the lifecycle around that run — opening before it and finalizing after
it, on every path.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from aoa.action_machine.resources.base_resource import BaseResource


@dataclass(frozen=True)
class PerCallConnection:
    """The pair for one call: ``factory`` runs on every resolve, ``finalize`` closes what it made."""

    factory: Callable[[], BaseResource]
    finalize: Callable[[BaseResource], Awaitable[None] | None]


type ConnectionValue = BaseResource | PerCallConnection


def validate_connection_entries(
    connections: Mapping[str, ConnectionValue] | None,
) -> None:
    """
    Validate keys and value shapes at record construction time.

    Does not call ``PerCallConnection.factory()`` or its ``finalize``; return type
    is checked in :func:`resolve_connections` when the adapter runs the route/tool.
    """
    if connections is None:
        return

    seen: set[str] = set()
    for key, value in connections.items():
        if not isinstance(key, str) or not key:
            raise TypeError("Connection key must be a non-empty string.")
        if key in seen:
            raise ValueError(f"Duplicate connection key: {key}")
        seen.add(key)

        if isinstance(value, BaseResource):
            continue
        if isinstance(value, PerCallConnection):
            if not callable(value.factory):
                raise TypeError("PerCallConnection.factory must be callable.")
            if not callable(value.finalize):
                raise TypeError("PerCallConnection.finalize must be callable.")
            continue

        raise TypeError(
            "Connection value must be a BaseResource or PerCallConnection, "
            f"got {type(value).__name__!r} for key {key!r}."
        )


def resolve_connections(
    connections: Mapping[str, ConnectionValue] | None,
) -> dict[str, BaseResource] | None:
    """
    Build the ``dict[str, BaseResource]`` passed to ``machine.run``.

    ``PerCallConnection`` entries call ``factory()`` on every invocation. The
    lifecycle — opening what was created and finalizing it — belongs to
    ``connection_scope``, which walks the declaration itself.
    """
    if not connections:
        return None

    result: dict[str, BaseResource] = {}
    for key, value in connections.items():
        if not isinstance(key, str) or not key:
            raise TypeError("Connection key must be a non-empty string.")
        if key in result:
            raise ValueError(f"Duplicate connection key: {key}")

        if isinstance(value, BaseResource):
            resource = value
        elif isinstance(value, PerCallConnection):
            resource = value.factory()
        else:
            raise TypeError(
                "Connection value must be a BaseResource or PerCallConnection, "
                f"got {type(value).__name__!r} for key {key!r}."
            )

        if not isinstance(resource, BaseResource):
            raise TypeError(
                f"PerCallConnection factory for key {key!r} must return BaseResource, "
                f"got {type(resource).__name__!r}."
            )
        result[key] = resource
    return result
