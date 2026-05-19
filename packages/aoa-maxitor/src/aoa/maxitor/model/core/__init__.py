# packages/aoa-maxitor/src/aoa/maxitor/model/core/__init__.py
"""Core bounded-context markers and entities for the Maxitor model layer."""

from aoa.maxitor.model.core.core_domain import CoreDomain
from aoa.maxitor.model.core.entities import NodeEntity

__all__ = [
    "CoreDomain",
    "NodeEntity",
]
