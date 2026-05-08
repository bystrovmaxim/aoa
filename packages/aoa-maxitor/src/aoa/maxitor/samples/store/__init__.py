# packages/aoa-maxitor/src/aoa/maxitor/samples/store/__init__.py
"""Primary demo bounded context: orders, audit, and the full decorator stack on actions."""

from aoa.maxitor.samples.store.domain import StoreDomain

__all__ = ["StoreDomain"]
