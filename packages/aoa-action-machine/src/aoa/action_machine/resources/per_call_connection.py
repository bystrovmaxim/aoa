# packages/aoa-action-machine/src/aoa/action_machine/resources/per_call_connection.py
"""
Per-route / per-tool connection declarations and resolution.

``connections`` is a mapping from connection key (string, matches ``@connection``)
to either a ready ``BaseResource`` or a ``PerCallConnection`` wrapper whose
factory is invoked on each resolve (FastAPI request or MCP tool call).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aoa.action_machine.resources.base_resource import BaseResource


@dataclass(frozen=True)
class PerCallConnection:
    """Lazy connection: ``factory`` runs on every ``resolve_connections`` call."""

    factory: Callable[[], BaseResource]


type ConnectionValue = BaseResource | PerCallConnection


def validate_connection_entries(
    connections: Mapping[str, ConnectionValue] | None,
) -> None:
    """
    Validate keys and value shapes at record construction time.

    Does not call ``PerCallConnection.factory()``; return type is checked in
    :func:`resolve_connections` when the adapter runs the route/tool.
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

    ``PerCallConnection`` entries call ``factory()`` on every invocation.
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
