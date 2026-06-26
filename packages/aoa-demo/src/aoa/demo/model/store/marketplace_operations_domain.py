# packages/aoa-demo/src/aoa/demo/model/store/marketplace_operations_domain.py
"""MarketplaceOperationsDomain — cross-channel retail policy umbrella."""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class MarketplaceOperationsDomain(BaseDomain):
    """Parent context: channel mix, policy classes, and compliance surfaces shared by storefronts."""

    name = "marketplace_operations"
    description = "Umbrella for multi-channel retail operations that concrete storefront slices specialize"
