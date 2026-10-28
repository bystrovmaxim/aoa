# packages/maxitor/src/maxitor/viewer/model/core/__init__.py
"""Core bounded-context markers and entities for the Maxitor model layer."""

from maxitor.viewer.model.core.core_domain import CoreDomain
from maxitor.viewer.model.core.entities import NodeCoreEntity

__all__ = [
    "CoreDomain",
    "NodeCoreEntity",
]
