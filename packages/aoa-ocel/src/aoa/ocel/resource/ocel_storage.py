# packages/aoa-ocel/src/aoa/ocel/resource/ocel_storage.py
"""
OcelStorage — abstract base for OCEL persistence backends.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Define the storage contract for OCEL events and nested-action wrappers.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Owner storage -> nested storage wrapper -> shared OCEL events
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources import BaseStorage
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.ocel.dto.ocel_event import OcelEvent
from aoa.ocel.resource.ocel_storage_wrapper import OcelStorageWrapper
from aoa.ocel.resource.ocel_store_protocol import OcelStoreProtocol


@exclude_graph_model
class OcelStorage(BaseStorage, OcelStoreProtocol, ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract persistent resource for OCEL 2.0 accumulation and persist on close.
    CONTRACT: Public API is ``open``, ``add_event``, ``close``; nested actions get ``OcelStorageWrapper``.
    INVARIANTS: ``add_event`` accepts only ``OcelEvent`` DTO; persistence runs in ``close()``.
    AI-CORE-END
    """

    async def check_rollup_support(self) -> bool:
        """Declare that OCEL persistence cannot roll back."""
        return False

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """Protect store ownership when passing to nested actions."""
        return OcelStorageWrapper

    @abstractmethod
    async def open(self) -> None:
        """Initialize the resource."""

    @abstractmethod
    async def add_event(self, event: OcelEvent) -> None:
        """Accumulate one composite OCEL event record.

        Raises:
            OcelContractError: duplicate ``event.id`` or resource not open.
        """

    @abstractmethod
    async def close(self) -> None:
        """Persist accumulated data and release resources."""
