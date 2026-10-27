# packages/aoa-fastapi-adapter/tests/test_websocket_route.py
"""
WebSocket routes of ``FastApiAdapter`` — one connection turned into action runs.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Drives real actions on a real ``ActionProductMachine`` through Starlette's test
client, so the whole path is exercised: accepting, building params from the
connection, filtering connections to what each action declares, refusing with a
close code, relaying without an action, the size and rate limits, and the close
action. ``SocketChannel``'s two queues are tested on their own with a websocket
that never reads, which a test client cannot simulate.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    TestClient.websocket_connect ─► FastApiAdapter.websocket(...) route
                                        │
                     OpenAction / EchoAction / CloseAction on the real machine
                                        │
                  Recorder (what ran) ◄─┴─► StubRelay (what was relayed)
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pydantic import Field
from starlette.websockets import WebSocketDisconnect

from aoa.action_machine.context.context import Context
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import ConnectionRefusalError, FastApiAdapter, SocketChannel

from .support import TestDomain


@meta(description="Records which actions of the test route ran", domain=TestDomain)
class Recorder(BaseController):
    """In-memory list of what the test route's actions did."""

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions see this recorder itself."""
        return None


@meta(description="Receives the relayed messages of the test route", domain=TestDomain)
class StubRelay(BaseController):
    """Relay target that records every relayed message and echoes it as a volatile event."""

    def __init__(self) -> None:
        self.relayed: list[dict[str, Any]] = []

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions see this relay itself."""
        return None

    def relay(self, channel: SocketChannel, message: dict[str, Any]) -> None:
        """Record ``message`` and send it back as the newest ``pointer``."""
        self.relayed.append(message)
        channel.send_volatile("pointer", {"type": "pointer", "x": message.get("x")})


class _Empty(BaseResult):
    """Nothing to return: the actions answer through the socket."""


@meta(description="Open a test connection", domain=TestDomain)
@check_roles(GuestRole)
@connection(SocketChannel, key="socket", description="The connection")
@connection(Recorder, key="recorder", description="What ran")
class OpenAction(BaseAction["OpenAction.Params", _Empty]):
    """Welcome a connection, or refuse it when its room is ``full``."""

    class Params(BaseParams):
        """The connection's room and origin."""

        room: str = Field(description="Room from the path")
        origin: str = Field(description="The Origin header")

    @summary_aspect("Welcome or refuse")
    async def welcome_summary(self, params: OpenAction.Params, state: BaseState, box: ToolsBox, connections: Connections) -> _Empty:
        """Refuse the room ``full``; otherwise record and welcome."""
        if params.room == "full":
            raise ConnectionRefusalError(4409, "room full")
        connections["recorder"].events.append(("open", (params.room, params.origin)))
        connections["socket"].send({"type": "welcome", "room": params.room})
        return _Empty()


@meta(description="Echo a test message", domain=TestDomain)
@check_roles(GuestRole)
@connection(SocketChannel, key="socket", description="The connection")
class EchoAction(BaseAction["EchoAction.Params", _Empty]):
    """Echo the text back, or refuse the text ``refuse``."""

    class Params(BaseParams):
        """The connection's room and the message's text."""

        room: str = Field(description="Room from the path")
        text: str = Field(description="Text to echo", max_length=20)

    @summary_aspect("Echo")
    async def echo_summary(self, params: EchoAction.Params, state: BaseState, box: ToolsBox, connections: Connections) -> _Empty:
        """Send the text back with the connection's room."""
        if params.text == "refuse":
            raise ConnectionRefusalError(4403, "not allowed")
        connections["socket"].send({"type": "echo", "room": params.room, "text": params.text})
        return _Empty()


@meta(description="Close a test connection", domain=TestDomain)
@check_roles(GuestRole)
@connection(Recorder, key="recorder", description="What ran")
class CloseAction(BaseAction["CloseAction.Params", _Empty]):
    """Record that the connection ended."""

    class Params(BaseParams):
        """The connection's room."""

        room: str = Field(description="Room from the path")

    @summary_aspect("Record the close")
    async def record_summary(self, params: CloseAction.Params, state: BaseState, box: ToolsBox, connections: Connections) -> _Empty:
        """Record the close of ``params.room``."""
        connections["recorder"].events.append(("close", params.room))
        return _Empty()


@meta(description="Needs a connection the route does not give", domain=TestDomain)
@check_roles(GuestRole)
@connection(Recorder, key="missing", description="Never provided")
class NeedsMissingAction(BaseAction["NeedsMissingAction.Params", _Empty]):
    """Declares a connection key no route provides."""

    class Params(BaseParams):
        """No fields."""

    @summary_aspect("Nothing")
    async def nothing_summary(self, params: NeedsMissingAction.Params, state: BaseState, box: ToolsBox, connections: Connections) -> _Empty:
        """Do nothing."""
        return _Empty()


def _client(recorder: Recorder, relay: StubRelay) -> tuple[TestClient, ActionProductMachine]:
    """Build an app with one WebSocket route on a real machine whose ``run`` is counted."""
    machine = ActionProductMachine(loggers=[])
    machine.run = AsyncMock(wraps=machine.run)  # type: ignore[method-assign]
    app = (
        FastApiAdapter(machine=machine, auth_coordinator=AsyncMock(process=AsyncMock(return_value=Context())))
        .websocket(
            "/rooms/{room}/live",
            on_open=OpenAction,
            messages={"echo": EchoAction},
            on_close=CloseAction,
            relay=frozenset({"pointer"}),
            relay_key="relay",
            connections={"recorder": recorder, "relay": relay},
        )
        .build()
    )
    return TestClient(app), machine


def _wait_for(predicate: Any, timeout: float = 3.0) -> bool:
    """Poll ``predicate`` until it holds or ``timeout`` passes; the server finishes on its own thread."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


class TestWebSocketRoute:
    """The route's behaviour, connection by connection."""

    def test_open_gets_path_and_origin(self) -> None:
        """(1) The open action runs with the path parameter and the Origin header."""
        recorder, relay = Recorder(), StubRelay()
        client, _ = _client(recorder, relay)
        with client.websocket_connect("/rooms/r1/live", headers={"origin": "http://maxitor"}) as ws:
            assert ws.receive_json() == {"type": "welcome", "room": "r1"}
        assert ("open", ("r1", "http://maxitor")) in recorder.events

    def test_message_runs_its_action(self) -> None:
        """(2) A mapped message runs its action, which answers through the socket with the connection's room."""
        client, _ = _client(Recorder(), StubRelay())
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"type": "echo", "text": "hi"}))
            assert ws.receive_json() == {"type": "echo", "room": "r1", "text": "hi"}

    def test_relayed_type_runs_no_action(self) -> None:
        """(3) A relayed type reaches the relay resource and runs no action."""
        relay = StubRelay()
        client, machine = _client(Recorder(), relay)
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
            runs_before = machine.run.await_count
            ws.send_text(json.dumps({"type": "pointer", "x": 5}))
            assert ws.receive_json() == {"type": "pointer", "x": 5}
            assert machine.run.await_count == runs_before
        assert relay.relayed == [{"type": "pointer", "x": 5}]

    def test_message_too_large_closes(self) -> None:
        """(4) A frame over 4 096 bytes closes the connection with 4413."""
        client, _ = _client(Recorder(), StubRelay())
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"type": "echo", "text": "x" * 4100}))
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
        assert closed.value.code == 4413

    def test_message_at_the_size_limit_is_accepted(self) -> None:
        """(4) A frame of exactly 4 096 bytes is still read (it fails validation, not the size limit)."""
        client, _ = _client(Recorder(), StubRelay())
        frame = json.dumps({"type": "echo", "text": ""})
        frame = frame.replace('""', '"' + "x" * (4096 - len(frame)) + '"')
        assert len(frame.encode()) == 4096
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
            ws.send_text(frame)
            assert ws.receive_json()["type"] == "error"

    def test_too_many_messages_closes(self) -> None:
        """(5) More than 40 messages in one second close the connection with 4429."""
        client, _ = _client(Recorder(), StubRelay())
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
            for index in range(41):
                ws.send_text(json.dumps({"type": "pointer", "x": index}))
            with pytest.raises(WebSocketDisconnect) as closed:
                while True:
                    ws.receive_json()
        assert closed.value.code == 4429

    def test_open_refusal_closes_with_its_code(self) -> None:
        """(6) A refusal from the open action closes with its code; the close action does not run."""
        recorder = Recorder()
        client, _ = _client(recorder, StubRelay())
        with client.websocket_connect("/rooms/full/live") as ws, pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert (closed.value.code, closed.value.reason) == (4409, "room full")
        assert not _wait_for(lambda: ("close", "full") in recorder.events, timeout=0.5)

    def test_message_refusal_keeps_the_connection(self) -> None:
        """(6) A refusal from a message action is answered and the connection stays open."""
        client, _ = _client(Recorder(), StubRelay())
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"type": "echo", "text": "refuse"}))
            assert ws.receive_json() == {"type": "refused", "code": 4403, "reason": "not allowed"}
            ws.send_text(json.dumps({"type": "echo", "text": "still here"}))
            assert ws.receive_json()["text"] == "still here"

    def test_unknown_type_and_spoofed_identity_are_errors(self) -> None:
        """(7) An unknown type, and a message that sets a connection value, are answered with an error."""
        client, _ = _client(Recorder(), StubRelay())
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"type": "nope"}))
            assert ws.receive_json()["type"] == "error"
            ws.send_text(json.dumps({"type": "echo", "text": "hi", "room": "other"}))
            error = ws.receive_json()
            assert error["type"] == "error" and "room" in error["reason"]

    def test_close_action_runs_on_disconnect(self) -> None:
        """(8) The close action runs when the client goes away."""
        recorder = Recorder()
        client, _ = _client(recorder, StubRelay())
        with client.websocket_connect("/rooms/r1/live") as ws:
            ws.receive_json()
        assert _wait_for(lambda: ("close", "r1") in recorder.events)

    def test_build_refuses_a_missing_connection(self) -> None:
        """A route that cannot give an action its declared connections fails at build time."""
        adapter = FastApiAdapter(
            machine=ActionProductMachine(loggers=[]),
            auth_coordinator=AsyncMock(process=AsyncMock(return_value=Context())),
        ).websocket("/x", on_open=NeedsMissingAction, messages={})
        with pytest.raises(ValueError, match="missing"):
            adapter.build()


class _NeverReading:
    """A websocket that accepts sends into a list, slowly or never."""

    def __init__(self, gate: asyncio.Event) -> None:
        self.sent: list[Any] = []
        self.closed_with: tuple[int, str] | None = None
        self._gate = gate

    async def send_json(self, data: Any) -> None:
        """Wait for the gate, then record ``data``."""
        await self._gate.wait()
        self.sent.append(data)

    async def close(self, code: int, reason: str) -> None:
        """Record the close."""
        self.closed_with = (code, reason)


class TestSocketChannel:
    """The channel's two queues against a client that does not read."""

    def test_volatile_keeps_only_the_newest(self) -> None:
        """(9) Ten volatile events to a paused client arrive as the newest one."""

        async def scenario() -> list[Any]:
            gate = asyncio.Event()
            socket = _NeverReading(gate)
            channel = SocketChannel(socket)  # type: ignore[arg-type]
            writer = asyncio.create_task(channel.run_writer())
            for index in range(10):
                channel.send_volatile("pointer", {"x": index})
            gate.set()
            await asyncio.sleep(0.05)
            channel.mark_closed()
            await asyncio.wait_for(writer, 1)
            return socket.sent

        assert asyncio.run(scenario()) == [{"x": 9}]

    def test_too_many_durable_events_close_the_client(self) -> None:
        """(10) 257 durable events to a client that never reads close it with 4008."""

        async def scenario() -> tuple[int, str] | None:
            socket = _NeverReading(asyncio.Event())
            channel = SocketChannel(socket)  # type: ignore[arg-type]
            for index in range(257):
                channel.send({"n": index})
            writer = asyncio.create_task(channel.run_writer())
            await asyncio.wait_for(writer, 1)
            return socket.closed_with

        assert asyncio.run(scenario()) == (4008, "client too slow")
