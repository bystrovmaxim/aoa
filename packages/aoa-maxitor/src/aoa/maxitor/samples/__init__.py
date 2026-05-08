# packages/aoa-maxitor/src/aoa/maxitor/samples/__init__.py
"""
Maxitor sample domains: a connected pseudo-product for the ActionMachine graph.

Eight bounded contexts (``store``, ``billing``, ``messaging``, ``catalog``,
``identity``, ``inventory``, ``analytics``, and ``support``) plus :mod:`aoa.maxitor.samples.roles`.
Most domains mirror the end-to-end contour of ``store`` (dependencies,
resources, plugins, entities, actions). Synthetic contexts (``identity``,
``inventory``, ``analytics``) are entity-only scaffolding focused on heterogeneous
ERD / graph layouts.

Load :data:`_MODULES` when import-time registrations are needed.
"""

from aoa.maxitor.samples.build import _MODULES
from aoa.maxitor.samples.store.domain import StoreDomain

__all__ = ["_MODULES", "StoreDomain"]
