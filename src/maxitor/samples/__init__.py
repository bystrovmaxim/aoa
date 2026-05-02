# src/maxitor/samples/__init__.py
"""
Maxitor sample domains: a connected pseudo-product for the ActionMachine graph.

Five bounded contexts (``store``, ``billing``, ``messaging``, ``catalog``, and
``support``) plus :mod:`maxitor.samples.roles`. Each domain mirrors the
structural depth of ``store``: dependencies, resources, plugins, entities, and
actions that exercise the full graph surface.

Load :data:`_MODULES` when import-time registrations are needed.
"""

from maxitor.samples.build import _MODULES
from maxitor.samples.store.domain import StoreDomain

__all__ = ["_MODULES", "StoreDomain"]
