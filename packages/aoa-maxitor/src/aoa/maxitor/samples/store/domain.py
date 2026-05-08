# packages/aoa-maxitor/src/aoa/maxitor/samples/store/domain.py
"""Bounded-context marker for the store / checkout slice."""

from aoa.action_machine.domain import BaseDomain


class StoreDomain(BaseDomain):
    name = "store"
    description = "Sample storefront: checkout, entities, plugins, and persistence stubs"
