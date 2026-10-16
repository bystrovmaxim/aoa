"""A service pool with a resource for each call.

Combine the two lifetimes after learning them separately. The holder makes a pool created at startup available to factories called later.

Run: uv run python examples/step_17_connections/16_pool_lifespan.py
"""

import asyncio
from aoa.action_machine.resources.postgres import PostgresResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.exceptions import HandleError, TransactionLeftOpenError

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
        for connection in self.connections:
            self.free.put_nowait(connection)
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
        for connection in self.connections:
            await connection.close()
        self.closed = True

from pydantic import Field
from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

class NotesDomain(BaseDomain):
    """Group the connection lesson."""
    name = "notes"
    description = "Notes example"

class EmptyParams(BaseParams):
    """No input fields are needed for this case."""

@meta(description="SQL statements for the notes example", domain=NotesDomain)
class NotesResource(PostgresResource):
    """Use the standard PostgreSQL lifecycle."""
    acquire_timeout = 1.0

class StatusResult(BaseResult):
    """Expose the command status."""
    status: str = Field(description="Driver command status")

@meta(description="Run one statement", domain=NotesDomain)
@check_roles(GuestRole)
@connection(NotesResource, key="db")
class QueryAction(BaseAction[EmptyParams, StatusResult]):
    """Use the supplied resource without managing its lifetime."""
    @summary_aspect("Execute a statement")
    async def query_summary(self, params, state, box, connections):
        """Return the driver's command status."""
        return StatusResult(status=await connections["db"].execute("SELECT 1"))

from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from aoa.fastapi import FastApiAdapter

class PoolHolder:
    """Expose the service pool only after startup."""
    pool = None
    def require(self):
        """Return the running pool or report missing startup."""
        if self.pool is None:
            raise RuntimeError("Pool is not started")
        return self.pool


async def main():
    """Run this case and verify its observable result."""
    holder = PoolHolder()
    created = []
    @asynccontextmanager
    async def lifespan(app):
        """Own the pool for the whole service lifetime."""
        pool = RecordingPool(size=2)
        holder.pool = pool
        created.append(pool)
        try:
            yield
        finally:
            await pool.close()
            holder.pool = None
    app = (FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=NoAuthCoordinator(context=Context()))
        .post("/query", QueryAction, connections={"db": PerCallConnection(
            factory=lambda: NotesResource(pool=holder.require()),
            finalize=lambda resource: resource.close(),
        )}).build(lifespan=lifespan))
    with TestClient(app) as client:
        response = client.post("/query", json={})
        assert response.status_code == 200 and response.json() == {"status": "OK"}
        assert not holder.require().held and not holder.require().closed
        print(response.json())
        print("returned after request:", len(holder.require().held) == 0)
    assert created[0].closed and holder.pool is None
    print("pool closed after shutdown:", created[0].closed)


if __name__ == "__main__":
    asyncio.run(main())
