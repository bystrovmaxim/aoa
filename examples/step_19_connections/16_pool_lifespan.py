"""A service pool with a resource for each call.

Combine the two lifetimes after learning them separately. The holder makes a pool created at startup available to factories called later.

Run: uv run python examples/step_19_connections/16_pool_lifespan.py
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.resources.postgres import PostgresDataSource, PostgresStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.fastapi import FastApiAdapter


class RecordingConnection:
    """Record commands; do not parse SQL or simulate database storage."""
    def __init__(self, number):
        """Give this connection a visible identity."""
        self.number = number
        self.commands = []
        self.busy = False
        self.closed = False
    async def execute(self, query, *params):
        """Reject concurrent use and record one command."""
        if self.busy or self.closed:
            raise RuntimeError("connection is busy or closed")
        self.busy = True
        try:
            await asyncio.sleep(0)
            self.commands.append(query)
            return "OK"
        finally:
            self.busy = False
    async def close(self):
        """Mark the physical connection closed."""
        self.closed = True

class RecordingPool:
    """Offer a fixed number of observable connections without a server."""
    def __init__(self, size=1):
        """Create the fixed capacity used by this example."""
        self.connections = [RecordingConnection(i + 1) for i in range(size)]
        self.free = asyncio.Queue()
        for pooled_connection in self.connections:
            self.free.put_nowait(pooled_connection)
        self.held = set()
        self.closed = False
    async def acquire(self, *, timeout=None):
        """Wait for an available connection with the supplied bound."""
        connection = await asyncio.wait_for(self.free.get(), timeout)
        self.held.add(connection)
        return connection
    async def release(self, connection):
        """Return a borrowed connection exactly once."""
        self.held.remove(connection)
        self.free.put_nowait(connection)
    async def close(self):
        """Close the pool only after all borrowers have returned."""
        assert not self.held
        for pooled_connection in self.connections:
            await pooled_connection.close()
        self.closed = True




class NotesDomain(BaseDomain):
    """Group the connection lesson."""
    name = "notes"
    description = "Notes example"

class EmptyParams(BaseParams):
    """No input fields are needed for this case."""

@meta(description="The notes database")
class ExampleDataSource(PostgresDataSource):
    """The database of this example: it hands out the recording pool's connections."""


@meta(description="SQL statements for the notes example", domain=NotesDomain)
class NotesStorage(PostgresStorage[ExampleDataSource]):
    """Use the standard PostgreSQL lifecycle."""

    async def add_note(self, text: str) -> str:
        """Write one note through the driver's statement helper."""
        return await self._execute("INSERT INTO notes(text) VALUES ($1)", (text,))

class StatusResult(BaseResult):
    """Expose the command status."""
    status: str = Field(description="Driver command status")

@meta(description="Run one statement", domain=NotesDomain)
@check_roles(GuestRole)
@connection(NotesStorage, key="db")
class QueryAction(BaseAction[EmptyParams, StatusResult]):
    """Use the supplied resource without managing its lifetime."""
    @summary_aspect("Execute a statement")
    async def query_summary(self, params: EmptyParams, state: BaseState, box: ToolsBox, connections: Connections) -> StatusResult:
        """Return the driver's command status."""
        return StatusResult(status=await connections["db"].add_note("one note"))





class PoolHolder:
    """Expose the service's data source only after startup."""
    data_source = None
    def require(self):
        """Return the running pool or report missing startup."""
        if self.data_source is None:
            raise RuntimeError("Pool is not started")
        return self.data_source


async def main():
    """Run this case and verify its observable result."""
    holder = PoolHolder()
    created = []
    @asynccontextmanager
    async def lifespan(app):
        """Own the pool for the whole service lifetime."""
        pool = RecordingPool(size=2)
        holder.data_source = ExampleDataSource(pool=pool)
        created.append(pool)
        try:
            yield
        finally:
            await pool.close()
            holder.data_source = None
    app = (FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=NoAuthCoordinator(context=Context()))
        .post("/query", QueryAction, connections={"db": PerCallConnection(
            factory=lambda: NotesStorage(data_source=holder.require()),
            finalize=lambda resource: resource.close(),
        )}).build(lifespan=lifespan))
    with TestClient(app) as client:
        response = client.post("/query", json={})
        assert response.status_code == 200 and response.json() == {"status": "OK"}
        assert not created[0].held and not created[0].closed
        print(response.json())
        print("returned after request:", len(created[0].held) == 0)
    assert created[0].closed and holder.data_source is None
    print("pool closed after shutdown:", created[0].closed)


if __name__ == "__main__":
    asyncio.run(main())
