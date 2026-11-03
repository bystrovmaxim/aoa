# packages/maxitor/maxitor-web/maxitor/web/model/core/__init__.py
"""Core bounded-context markers and entities for the Maxitor model layer."""

from maxitor.web.model.core.core_domain import CoreDomain
from maxitor.web.model.core.entities import NodeCoreEntity

__all__ = [
    "CoreDomain",
    "NodeCoreEntity",
]
