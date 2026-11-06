# packages/aoa-ocel/src/aoa/ocel/resource/ocel_storage_wrapper.py
"""
OcelStorageWrapper — proxy for nested actions (mirrors SqlStorageWrapper).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Allow nested actions to append events while reserving lifecycle control for the owner.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Owner storage -> nested storage wrapper -> shared OCEL events
"""

from __future__ import annotations

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources import BaseStorage
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.ocel.dto.ocel_event import OcelEvent
from aoa.ocel.exceptions.ocel_resource_access_prohibited_error import (
    OcelResourceAccessProhibitedError,
)
from aoa.ocel.resource.ocel_store_protocol import OcelStoreProtocol


@exclude_graph_model
class OcelStorageWrapper(BaseStorage, OcelStoreProtocol):
    """
    Restrict a nested action to appending OCEL events.

    AI-CORE-BEGIN
    ROLE: Same-kind wrapper for an owner's OCEL storage.
    CONTRACT: Forward add_event; refuse open and close from nested actions.
    INVARIANTS: The original action retains lifecycle and persistence ownership.
    AI-CORE-END
    """

    def __init__(self, resource: OcelStoreProtocol) -> None:
        """Retain the owner’s store for event forwarding."""
        self._resource = resource

    async def check_rollup_support(self) -> bool:
        """Use the underlying store’s rollback capability."""
        return await self._resource.check_rollup_support()

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """Preserve ownership restrictions through deeper nesting."""
        return OcelStorageWrapper

    async def open(self) -> None:
        """Refuse lifecycle control from a nested action."""
        raise OcelResourceAccessProhibitedError(
            "Opening OCEL store is allowed only in the action that created the resource. "
            "Current action received a proxy connection, so open is unavailable."
        )

    async def add_event(self, event: OcelEvent) -> None:
        """Forward an event to the owner’s store."""
        await self._resource.add_event(event)

    async def close(self) -> None:
        """Refuse persistence control from a nested action."""
        raise OcelResourceAccessProhibitedError(
            "Closing OCEL store is allowed only in the action that created the resource. "
            "Current action received a proxy connection, so close is unavailable."
        )
