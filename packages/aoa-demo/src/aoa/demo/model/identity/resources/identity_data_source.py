# packages/aoa-demo/src/aoa/demo/model/identity/resources/identity_data_source.py
"""
IdentityDataSource — the identity database, with the pool its resources share.

The demo creates it once, in the application's lifespan, when ``AOA_DEMO_POSTGRES_DSN``
is set, and builds ``IdentityStore(data_source=…)`` on every call. Importing this module
needs the ``postgres`` extra, because ``PostgresDataSource`` imports the driver; the demo
reaches for it lazily, as it does for ``IdentityStore``.
"""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.postgres import PostgresDataSource


@meta(description="The identity database")
class IdentityDataSource(PostgresDataSource):
    """
    AI-CORE-BEGIN
        ROLE: The identity database: its connection parameters and its pool.
        CONTRACT: Created in the lifespan from the DSN with pool bounds; ``IdentityStore`` takes connections from it.
        INVARIANTS: The wait for a free connection is stated here, not inherited silently.
    AI-CORE-END
    """

    acquire_timeout: float | None = 30.0
    """How long a resource waits for a free connection before it fails, stated here for the reader."""
