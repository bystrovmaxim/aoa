# src/maxitor/samples/store/__init__.py
"""Primary demo bounded context: orders, audit, and the full decorator stack on actions."""

from maxitor.samples.store.domain import StoreDomain

__all__ = ["StoreDomain"]
