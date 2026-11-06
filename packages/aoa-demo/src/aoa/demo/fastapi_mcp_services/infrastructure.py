# packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/infrastructure.py
"""
Shared ActionMachine runtime wiring for the FastAPI and MCP example apps.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ActionProductMachine`` and ``NoAuthCoordinator`` are constructed once and
imported by both transports so HTTP and MCP share the same runtime instance and
auth policy.

``GetExampleModelGraphJsonAction`` is imported before ``ActionProductMachine()`` so
``create_node_graph_coordinator()`` materializes that action on the default graph.

``ActionProductMachine`` creates its default ``NodeGraphCoordinator`` eagerly.
Adapters receive ``machine`` and ``auth``; they use ``machine.graph_coordinator``
when they need the graph.

``NoAuthCoordinator`` states that this sample performs no real authentication.
For production, supply an ``AuthCoordinator`` with ``CredentialExtractor``,
``Authenticator``, and ``ContextAssembler``. Keep ``NoAuthCoordinator`` only
for intentionally public APIs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    infrastructure (this module)
    +-- machine = ActionProductMachine()
    |       +-- built NodeGraphCoordinator (eager ``create_node_graph_coordinator()``)
    +-- auth    = NoAuthCoordinator()
              |
              +------------------+------------------+
              |                                     |
      app_fastapi_service                   app_mcp_service
      FastApiAdapter(machine, auth)         McpAdapter(machine, auth)
              |                                     |
              v                                     v
        HTTP routes                          MCP tools
              \\___________________________________/
                    same machine + auth instances

═══════════════════════════════════════════════════════════════════════════════
THE POOL, AND THE MODE WITHOUT A DATABASE
═══════════════════════════════════════════════════════════════════════════════

``pool_lifespan`` opens the identity data source — the identity database and its one
pool — when ``AOA_DEMO_POSTGRES_DSN`` is set, and closes it when the application stops. Both services pass it to their builder, which hands it
to the framework untouched — an MCP service has no request-scoped startup hook, but
its server has one.

With a DSN, the identity route declares a per-call resource over that data source: one
connection per call, taken in ``open()`` and given back in ``close()``. Without the
variable, nothing is created and the route declares the in-memory identity store
instead, so the demo answers with no database and with no driver installed.

"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

from aoa.action_machine.auth import NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.resources.per_call_connection import ConnectionValue, PerCallConnection
from aoa.action_machine.resources.sql import SqlStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

if TYPE_CHECKING:
    from aoa.demo.model.identity.resources.identity_data_source import IdentityDataSource

# Register on the default graph before ``create_node_graph_coordinator()`` runs.
from aoa.demo.model.actions import GetExampleModelGraphJsonAction  # noqa: F401  # pylint: disable=unused-import
from aoa.demo.model.identity.actions import IdentityLookupAction  # noqa: F401  # pylint: disable=unused-import
from aoa.demo.model.identity.resources.identity_stub_storage import IdentityStubStorage

machine = ActionProductMachine()
auth = NoAuthCoordinator(context=Context())

DEMO_DSN_ENV = "AOA_DEMO_POSTGRES_DSN"
"""Where the demo looks for a connection description; unset means the database-free mode."""


def demo_dsn() -> str | None:
    """Return the configured connection description, or ``None`` for the database-free mode."""
    return os.getenv(DEMO_DSN_ENV) or None


class DataSourceHolder:
    """Carries the identity data source, and its pool, to whoever needs it after the application has started."""

    data_source: IdentityDataSource | None = None

    def require(self) -> IdentityDataSource:
        """
        Return the open data source, or fail naming the situation rather than an attribute.

        Raises:
            HandleError: when there is none — a call before startup, or a process started
                without a connection description.
        """
        if self.data_source is None:
            raise HandleError(
                f"The demo has no database: set {DEMO_DSN_ENV} before starting, or use the "
                "database-free mode the identity route falls back to."
            )
        return self.data_source


data_source_holder = DataSourceHolder()


@asynccontextmanager
async def pool_lifespan(app: object) -> AsyncIterator[None]:
    """
    Open the identity data source, and with it the pool, at startup and close it at shutdown.

    Without a connection description nothing is created, and nothing is closed.
    """
    dsn = demo_dsn()
    if dsn:
        # The optional ``postgres`` extra, imported only when a DSN is given, so that the
        # demo still imports and runs without the driver installed.
        from aoa.demo.model.identity.resources.identity_data_source import (  # pylint: disable=import-outside-toplevel
            IdentityDataSource,
        )

        # The size bounds are stated here; the wait for a free connection is stated on the
        # data source (``IdentityDataSource.acquire_timeout``).
        source = IdentityDataSource(dsn, min_size=1, max_size=10)
        await source.open()
        data_source_holder.data_source = source
    try:
        yield
    finally:
        if data_source_holder.data_source is not None:
            await data_source_holder.data_source.close()
            data_source_holder.data_source = None


def identity_connection() -> ConnectionValue:
    """
    Declare the identity connection for one call.

    Over the pool when a connection description was given — the driver is reached for lazily,
    at call time — and over the in-memory store otherwise. The route, the action and the
    lifecycle are the same in both modes; only the storage differs.
    """
    if demo_dsn():

        def pooled() -> BaseResource:
            from aoa.demo.model.identity.resources.identity_postgres_storage import (  # pylint: disable=import-outside-toplevel
                IdentityPostgresStorage,
            )

            return IdentityPostgresStorage(data_source=data_source_holder.require())

        return PerCallConnection(factory=pooled, finalize=_close_store)

    return PerCallConnection(factory=IdentityStubStorage, finalize=_close_store)


def _close_store(store: BaseResource) -> Awaitable[None]:
    """Close the store this call created; its connection goes back to the pool."""
    return cast(SqlStorage, store).close()
