# packages/aoa-examples/src/aoa/examples/model/store/__init__.py
"""Primary demo bounded context: orders, audit, and the full decorator stack on actions."""

from aoa.examples.model.store.domain import CommerceDomain, StoreDomain

__all__ = ["CommerceDomain", "StoreDomain"]
