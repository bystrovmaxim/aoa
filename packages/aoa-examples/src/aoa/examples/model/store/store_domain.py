# packages/aoa-examples/src/aoa/examples/model/store/store_domain.py
"""StoreDomain — storefront / checkout bounded context."""

from __future__ import annotations

from aoa.examples.model.store.marketplace_operations_domain import MarketplaceOperationsDomain


class StoreDomain(MarketplaceOperationsDomain):
    name = "store"
    description = "Sample storefront: checkout, entities, plugins, and persistence stubs"
