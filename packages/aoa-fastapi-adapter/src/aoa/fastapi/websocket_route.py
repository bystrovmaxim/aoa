# packages/aoa-fastapi-adapter/src/aoa/fastapi/websocket_route.py
"""
WebSocket routes — one connection turned into action runs, as an HTTP route turns one request into one.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A WebSocket route declares which action runs when a connection opens, which action
runs for each message type, and which action runs when the connection ends. The
adapter does the transport and nothing else: it accepts the connection, enforces
the size and rate limits, builds each action's params, runs the action through the
machine, and relays the message types that must not run an action (a pointer sent
twenty times a second) to the resource that owns them. Every decision — who may
join, what a message means — is made in an action.

A connection's identity comes from the connection, never from a message: the path
and query parameters and the ``Origin`` and ``Host`` headers fill the params fields of the same
name in every action of the route, and a message that carries one of those names is
refused. A client therefore cannot speak for another room or another participant.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    connect ─► accept ─► SocketChannel ─► on_open action ──refused──► close(code)
                                              │
                                              ▼
    frame ─► size ─► rate ─► JSON {"type": …} ─┬─► type in relay    ─► resource.relay(channel, message)
                                               ├─► type in messages ─► that action (one at a time)
                                               └─► anything else    ─► {"type": "error"}
                                              │
    disconnect / close ───────────────────────┴─► on_close action

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

``FastApiWebSocketRoute`` checks its declaration when it is created. ``build()``
resolves which connection keys each action declares, so a route that cannot give an
action exactly its declared connections fails at start-up, not on the first message.
The endpoint itself runs per connection.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections import deque
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError
from starlette.websockets import WebSocket, WebSocketDisconnect

from aoa.action_machine.adapters.base_route_record import extract_action_types
from aoa.action_machine.auth.auth_coordinator_protocol import AuthCoordinatorProtocol
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import ConnectionValue
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.socket_channel import SocketChannel

#: The connection key under which every action of a route receives its ``SocketChannel``.
SOCKET_KEY = "socket"

#: Close codes the adapter itself uses; codes 4000–4999 otherwise belong to the application.
AUTHENTICATION_REQUIRED = 4401
INVALID_PARAMETERS = 4422
MESSAGE_TOO_LARGE = 4413
TOO_MANY_MESSAGES = 4429
INTERNAL_ERROR = 1011


@runtime_checkable
class RelayTarget(Protocol):
    """A resource that takes the relayed messages of a route: who gets them is its own business."""

    def relay(self, channel: SocketChannel, message: dict[str, Any]) -> None:
        """Pass ``message``, received on ``channel``, on to whoever should see it."""


class ConnectionRefusalError(Exception):
    """
    AI-CORE-BEGIN
    ROLE: The way an action of a WebSocket route refuses, with a close code and a reason.
    CONTRACT: Raised by the open action it closes the connection with ``code`` and ``reason``;
    raised by a message action it answers ``{"type": "refused", "code", "reason"}`` and keeps it open.
    AI-CORE-END
    """

    def __init__(self, code: int, reason: str) -> None:
        super().__init__(f"{code} {reason}")
        self.code = code
        self.reason = reason


@dataclass(frozen=True)
class FastApiWebSocketRoute:
    """
    AI-CORE-BEGIN
    ROLE: The frozen declaration of one WebSocket route: its actions, relayed types, connections and limits.
    CONTRACT: Every action is a ``BaseAction``; relayed types and message types do not overlap; a relay
    names a resource with a ``relay`` method; ``socket`` is reserved for the adapter's ``SocketChannel``.
    INVARIANTS: Limits are positive; the declaration never changes after creation.
    AI-CORE-END
    """

    path: str
    on_open: type[BaseAction[Any, Any]]
    messages: Mapping[str, type[BaseAction[Any, Any]]]
    on_close: type[BaseAction[Any, Any]] | None = None
    relay: frozenset[str] = frozenset()
    relay_key: str | None = None
    connections: Mapping[str, ConnectionValue] = field(default_factory=dict)
    max_message_bytes: int = 4096
    max_messages_per_second: int = 40
    tags: tuple[str, ...] = ()
    description: str = ""
    auth_coordinator: AuthCoordinatorProtocol | None = None

    def __post_init__(self) -> None:
        """Refuse a declaration the endpoint could not serve."""
        self._check_actions_and_types()
        self._check_connections()
        if self.max_message_bytes <= 0 or self.max_messages_per_second <= 0:
            raise ValueError(f"{self.path}: message limits must be positive.")

    def _check_actions_and_types(self) -> None:
        """Every action has a params model; message types are non-empty and never both run and relayed."""
        for action_class in self.action_classes():
            if not isinstance(action_class, type) or not issubclass(action_class, BaseAction):
                raise TypeError(f"{self.path}: {action_class!r} is not a BaseAction subclass.")
            params_type, _ = extract_action_types(action_class)
            if params_type is None:
                raise TypeError(f"{self.path}: {action_class.__name__} has no resolvable params type.")
        for message_type in [*self.messages, *self.relay]:
            if not isinstance(message_type, str) or not message_type:
                raise ValueError(f"{self.path}: message types must be non-empty strings, got {message_type!r}.")
        overlap = set(self.messages) & set(self.relay)
        if overlap:
            raise ValueError(f"{self.path}: types both run an action and are relayed: {sorted(overlap)}.")

    def _check_connections(self) -> None:
        """``socket`` stays the adapter's; relayed types name a resource that can relay."""
        if SOCKET_KEY in self.connections:
            raise ValueError(f"{self.path}: the connection key {SOCKET_KEY!r} is reserved for the adapter.")
        if not self.relay:
            return
        target = self.connections.get(self.relay_key or "")
        if not isinstance(target, BaseResource) or not isinstance(target, RelayTarget):
            raise ValueError(
                f"{self.path}: relayed types need relay_key to name a resource with a relay(channel, message) method."
            )

    def action_classes(self) -> list[type[BaseAction[Any, Any]]]:
        """Every action of the route, the open and close actions included."""
        classes = [self.on_open, *self.messages.values()]
        if self.on_close is not None:
            classes.append(self.on_close)
        return classes


def _connection_values(websocket: WebSocket) -> dict[str, str]:
    """The values a connection speaks with: query parameters, then path parameters, ``origin`` and ``host``."""
    values: dict[str, str] = dict(websocket.query_params.items())
    values.update({key: str(value) for key, value in websocket.path_params.items()})
    values["origin"] = websocket.headers.get("origin", "")
    values["host"] = websocket.headers.get("host", "")
    return values


def _build_params(action_class: type[BaseAction[Any, Any]], values: Mapping[str, str], fields: Mapping[str, Any]) -> Any:
    """Build ``action_class``'s params from the connection's values and a message's own fields."""
    params_type, _ = extract_action_types(action_class)
    if params_type is None or not issubclass(params_type, BaseModel):
        raise TypeError(f"{action_class.__name__} has no params model.")
    declared = params_type.model_fields
    data = {name: value for name, value in values.items() if name in declared}
    data.update(fields)
    return params_type.model_validate(data)


def make_websocket_endpoint(
    route: FastApiWebSocketRoute,
    machine: ActionProductMachine,
    auth_coordinator: AuthCoordinatorProtocol,
    declared_keys: Mapping[type, frozenset[str]],
) -> Callable[[WebSocket], Coroutine[Any, Any, None]]:
    """Return the endpoint that serves ``route``, one call per connection."""

    async def endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        channel = SocketChannel(websocket)
        writer = asyncio.create_task(channel.run_writer())
        connections: dict[str, ConnectionValue] = {**route.connections, SOCKET_KEY: channel}
        values = _connection_values(websocket)
        context = await auth_coordinator.process(websocket)
        if context is None:
            channel.close(AUTHENTICATION_REQUIRED, "authentication required")
            await writer
            return

        async def run(action_class: type[BaseAction[Any, Any]], fields: Mapping[str, Any]) -> None:
            params = _build_params(action_class, values, fields)
            keys = declared_keys[action_class]
            scoped = {key: value for key, value in connections.items() if key in keys}
            async with connection_scope(scoped or None) as opened:
                await machine.run(context, action_class(), params, opened)

        opened = False
        try:
            try:
                await run(route.on_open, {})
            except ConnectionRefusalError as refusal:
                channel.close(refusal.code, refusal.reason)
                return
            except ValidationError:
                channel.close(INVALID_PARAMETERS, "invalid parameters")
                return
            opened = True
            await _serve_messages(websocket, channel, route, values, run)
        except WebSocketDisconnect:
            pass
        except Exception:
            # An unexpected failure must end this connection, never the server: the client is told
            # "internal error" and the failure itself is the machine's to log.
            channel.close(INTERNAL_ERROR, "internal error")
        finally:
            if opened and route.on_close is not None:
                with contextlib.suppress(Exception):
                    await run(route.on_close, {})
            if not channel.closed:
                channel.mark_closed()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(writer, timeout=5)

    return endpoint


def _within_limits(text: str, route: FastApiWebSocketRoute, channel: SocketChannel, arrivals: deque[float]) -> bool:
    """Apply the size and rate limits to one frame; close the connection and return ``False`` when one is broken."""
    if len(text.encode("utf-8")) > route.max_message_bytes:
        channel.close(MESSAGE_TOO_LARGE, "message too large")
        return False
    now = time.monotonic()
    arrivals.append(now)
    while arrivals and arrivals[0] <= now - 1.0:
        arrivals.popleft()
    if len(arrivals) > route.max_messages_per_second:
        channel.close(TOO_MANY_MESSAGES, "too many messages")
        return False
    return True


def _parse(text: str) -> tuple[dict[str, Any] | None, str]:
    """Return the message and its type, or ``None`` and the reason it cannot be read."""
    try:
        message = json.loads(text)
    except json.JSONDecodeError:
        return None, "a message must be a JSON object"
    if not isinstance(message, dict) or not isinstance(message.get("type"), str):
        return None, 'a message must be a JSON object with a string "type"'
    return message, str(message["type"])


async def _dispatch(
    message: dict[str, Any],
    message_type: str,
    channel: SocketChannel,
    route: FastApiWebSocketRoute,
    values: Mapping[str, str],
    run: Callable[[type[BaseAction[Any, Any]], Mapping[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    """Relay the message, run its action, or answer why neither is possible."""
    if message_type in route.relay:
        target = route.connections[route.relay_key or ""]
        if isinstance(target, RelayTarget):
            target.relay(channel, message)
        return
    action_class = route.messages.get(message_type)
    if action_class is None:
        channel.send({"type": "error", "reason": f"unknown message type {message_type!r}"})
        return
    fields = {key: value for key, value in message.items() if key != "type"}
    spoofed = sorted(set(fields) & set(values))
    if spoofed:
        channel.send({"type": "error", "reason": f"a message may not set {', '.join(spoofed)}"})
        return
    try:
        await run(action_class, fields)
    except ConnectionRefusalError as refusal:
        channel.send({"type": "refused", "code": refusal.code, "reason": refusal.reason})
    except ValidationError as error:
        channel.send({"type": "error", "reason": f"invalid {message_type!r}: {error.error_count()} field error(s)"})


async def _serve_messages(
    websocket: WebSocket,
    channel: SocketChannel,
    route: FastApiWebSocketRoute,
    values: Mapping[str, str],
    run: Callable[[type[BaseAction[Any, Any]], Mapping[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    """Receive frames until the connection ends, and turn each one into a relay, an action or an error."""
    arrivals: deque[float] = deque()
    while not channel.closed:
        frame = await websocket.receive()
        if frame["type"] == "websocket.disconnect":
            return
        text = frame.get("text")
        if text is None:
            channel.send({"type": "error", "reason": "only text frames are accepted"})
            continue
        if not _within_limits(text, route, channel, arrivals):
            return
        message, message_type = _parse(text)
        if message is None:
            channel.send({"type": "error", "reason": message_type})
            continue
        await _dispatch(message, message_type, channel, route, values, run)
