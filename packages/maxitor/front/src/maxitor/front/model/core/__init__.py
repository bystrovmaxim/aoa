# packages/maxitor/front/src/maxitor/front/model/core/__init__.py
"""Core bounded-context markers and entities for the Maxitor model layer."""

from maxitor.front.model.core.core_domain import CoreDomain
from maxitor.front.model.core.entities import NodeCoreEntity

__all__ = [
    "CoreDomain",
    "NodeCoreEntity",
]
