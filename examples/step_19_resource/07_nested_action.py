"""A real nested action receives a restricted view.

Let the machine create the wrapper through box.run. The child asks to close the resource and catches the explicit refusal.

Run: uv run python examples/step_19_resource/07_nested_action.py
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

from aoa.action_machine.intents.depends import depends, UseCase
from aoa.action_machine.exceptions import TransactionProhibitedError

@meta(description="Try closing a parent connection", domain=NotesDomain)
@check_roles(GuestRole)
@connection(NotesResource, key="db")
class ChildAction(BaseAction[EmptyParams, StatusResult]):
    """Observe the wrapper supplied by the runtime."""
    @summary_aspect("Attempt closing")
    async def close_summary(self, params, state, box, connections):
        """Report the nested closing refusal."""
        try:
            await connections["db"].close()
        except TransactionProhibitedError:
            return StatusResult(status="TransactionProhibitedError")
        raise AssertionError("Child closed its parent's connection")

@meta(description="Call the child with the parent's connection", domain=NotesDomain)
@check_roles(GuestRole)
@connection(NotesResource, key="db")
@depends(ChildAction, mode=UseCase.include)
class ParentAction(BaseAction[EmptyParams, StatusResult]):
    """Keep ownership while delegating part of the work."""
    @summary_aspect("Run child")
    async def child_summary(self, params, state, box, connections):
        """Pass the connection to the child through the runtime."""
        return await box.run(ChildAction, EmptyParams(), connections=connections)


async def main():
    """Run this case and verify its observable result."""
    pool = RecordingPool()
    async with connection_scope({"db": PerCallConnection(lambda: NotesResource(pool=pool), lambda resource: resource.close())}) as connections:
        result = await ActionProductMachine(loggers=[]).run(Context(), ParentAction(), EmptyParams(), connections)
        assert result.status == "TransactionProhibitedError"
        assert len(pool.held) == 1
        print(result.model_dump())
    assert not pool.held
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
