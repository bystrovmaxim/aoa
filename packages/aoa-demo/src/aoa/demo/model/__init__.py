# packages/aoa-demo/src/aoa/demo/model/__init__.py
"""
Example ActionMachine domains: a connected pseudo-product for interchange and ERD demos.

Eight bounded contexts (``store``, ``billing``, ``messaging``, ``catalog``,
``identity``, ``inventory``, ``analytics``, and ``support``) plus :mod:`aoa.demo.model.roles`.
Most domains mirror the end-to-end contour of ``store`` (dependencies,
resources, plugins, entities, actions). Synthetic contexts (``identity``,
``inventory``, ``analytics``) are entity-only scaffolding focused on heterogeneous
ERD / graph layouts.

Load :data:`_MODULES` when import-time registrations are needed.
"""

from aoa.demo.model.build import _MODULES
from aoa.demo.model.store.marketplace_operations_domain import MarketplaceOperationsDomain
from aoa.demo.model.store.store_domain import StoreDomain

__all__ = ["_MODULES", "MarketplaceOperationsDomain", "StoreDomain"]
