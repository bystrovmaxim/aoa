# packages/aoa-examples/src/aoa/examples/model/store/domain.py
"""Bounded-context marker for the store / checkout slice."""

from aoa.action_machine.domain import BaseDomain


class CommerceDomain(BaseDomain):
    """Intermediate commerce context for sample domain generalization (PR-6)."""

    name = "commerce"
    description = "Sample commerce umbrella for storefront and checkout demos"


class StoreDomain(CommerceDomain):
    name = "store"
    description = "Sample storefront: checkout, entities, plugins, and persistence stubs"
