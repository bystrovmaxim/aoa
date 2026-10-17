# packages/aoa-demo/tests/test_sql_resource_stubs.py
"""
The eight demo stubs satisfy the SQL contract without an edit.

The SQL contract gained ``close()`` with a concrete harmless body, and the point
of that body is exactly this file: every ``SqlResource`` subclass in the demo —
four domains, eight classes — keeps working untouched. The generic query member
then left the contract, and nothing here had to change for that either: a stub
that holds no connection has no statement to run. None of them is PostgreSQL, and
none of this needs a database.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    SqlResource (contract: open/begin/commit/rollback/close)
        │  close() has a concrete harmless body
        ├── catalog:   CatalogSearchSidecar, CatalogObjectStore
        ├── messaging: MessagingDeadLetterStore, OutboxPrimaryDatabase
        ├── billing:   BillingWarehouse, BillingReadReplica
        └── store:     StorefrontDatabase, StorefrontSessionCache

"""

from __future__ import annotations

import pytest

from aoa.action_machine.resources.sql import ProtocolSqlResource
from aoa.demo.model.billing.resources.read_replica import BillingReadReplica
from aoa.demo.model.billing.resources.warehouse import BillingWarehouse
from aoa.demo.model.catalog.resources.object_store import CatalogObjectStore
from aoa.demo.model.catalog.resources.search_sidecar import CatalogSearchSidecar
from aoa.demo.model.messaging.resources.dlq_store import MessagingDeadLetterStore
from aoa.demo.model.messaging.resources.outbox_primary import OutboxPrimaryDatabase
from aoa.demo.model.store.resources.cache import StorefrontSessionCache
from aoa.demo.model.store.resources.db import StorefrontDatabase

STUBS: list[type] = [
    CatalogSearchSidecar,
    CatalogObjectStore,
    MessagingDeadLetterStore,
    OutboxPrimaryDatabase,
    BillingWarehouse,
    BillingReadReplica,
    StorefrontDatabase,
    StorefrontSessionCache,
]


@pytest.mark.parametrize("stub_class", STUBS, ids=lambda cls: cls.__name__)
def test_a_demo_stub_still_satisfies_the_contract(stub_class: type) -> None:
    """Instantiation and the structural contract are unchanged by closing and by the removal."""
    assert isinstance(stub_class(), ProtocolSqlResource)


@pytest.mark.parametrize("stub_class", STUBS, ids=lambda cls: cls.__name__)
def test_a_demo_stub_carries_no_query_member(stub_class: type) -> None:
    """A stub holds no connection, so it has no statement to run and no passthrough to publish."""
    stub = stub_class()

    for member in ("execute", "_execute", "_fetchrow"):
        assert not hasattr(stub, member), member


@pytest.mark.parametrize("stub_class", STUBS, ids=lambda cls: cls.__name__)
async def test_a_demo_stub_closes_harmlessly(stub_class: type) -> None:
    """It holds no connection, so the inherited default is the whole of its closing."""
    stub = stub_class()

    assert await stub.close() is None
