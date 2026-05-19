# packages/aoa-examples/src/aoa/examples/model/store/__init__.py
"""Primary demo bounded context: orders, audit, and the full decorator stack on actions."""

from aoa.examples.model.store.marketplace_operations_domain import MarketplaceOperationsDomain
from aoa.examples.model.store.store_domain import StoreDomain

__all__ = ["MarketplaceOperationsDomain", "StoreDomain"]
