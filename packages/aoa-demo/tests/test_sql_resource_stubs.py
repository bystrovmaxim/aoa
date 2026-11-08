# packages/aoa-demo/tests/test_sql_resource_stubs.py
"""
The demo's SQL stubs satisfy the contract without an edit.

The SQL contract gained ``close()`` with a concrete harmless body, and the point
of that body is exactly this file: every ``SqlStorage`` subclass in the demo
keeps working untouched. The generic query member then left the contract, and
nothing here had to change for that either: a stub that holds no connection has
no statement to run. None of them is PostgreSQL, and none of this needs a
database.

The storefront, the support desk and inventory share one database, so the demo
has one stub for them — ``ShopDatabaseStorage`` — instead of three.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    SqlStorage (contract: open/begin/commit/rollback/close)
        │  close() has a concrete harmless body
        ├── catalog:   CatalogSearchSidecarStorage, CatalogObjectStoreStorage
        ├── messaging: OutboxPrimaryDatabaseStorage
        ├── billing:   BillingWarehouseStorage, BillingReadReplicaStorage
        └── databases: ShopDatabaseStorage (store + support + inventory)
                       StorefrontSessionCacheStorage

"""

from __future__ import annotations

import pytest

from aoa.action_machine.resources.sql import ProtocolSqlResource
from aoa.demo.model.billing.resources.billing_read_replica_storage import BillingReadReplicaStorage
from aoa.demo.model.billing.resources.billing_warehouse_storage import BillingWarehouseStorage
from aoa.demo.model.catalog.resources.catalog_object_store_storage import CatalogObjectStoreStorage
from aoa.demo.model.catalog.resources.catalog_search_sidecar_storage import CatalogSearchSidecarStorage
from aoa.demo.model.databases import ShopDatabaseStorage
from aoa.demo.model.messaging.resources.outbox_primary_database_storage import OutboxPrimaryDatabaseStorage
from aoa.demo.model.store.resources.storefront_session_cache_storage import StorefrontSessionCacheStorage

STUBS: list[type] = [
    CatalogSearchSidecarStorage,
    CatalogObjectStoreStorage,
    OutboxPrimaryDatabaseStorage,
    BillingWarehouseStorage,
    BillingReadReplicaStorage,
    ShopDatabaseStorage,
    StorefrontSessionCacheStorage,
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
