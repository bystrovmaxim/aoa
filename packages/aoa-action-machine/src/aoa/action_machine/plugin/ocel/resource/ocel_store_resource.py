# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/resource/ocel_store_resource.py
"""OcelStoreResource — abstract base for OCEL persistence backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.plugin.ocel.dto.ocel_event import OcelEvent
from aoa.action_machine.plugin.ocel.resource.ocel_store_protocol import OcelStoreProtocol
from aoa.action_machine.plugin.ocel.resource.ocel_store_wrapper import OcelStoreWrapper
from aoa.action_machine.resources.base_resource import BaseResource


@exclude_graph_model
class OcelStoreResource(BaseResource, OcelStoreProtocol, ABC):
    """
    AI-CORE-BEGIN
    ROLE: Abstract persistent resource for OCEL 2.0 accumulation and persist on close.
    CONTRACT: Public API is ``open``, ``add_event``, ``close``; nested actions get ``OcelStoreWrapper``.
    INVARIANTS: ``add_event`` accepts only ``OcelEvent`` DTO; persistence runs in ``close()``.
    AI-CORE-END
    """

    async def check_rollup_support(self) -> bool:
        return False

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return OcelStoreWrapper

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
