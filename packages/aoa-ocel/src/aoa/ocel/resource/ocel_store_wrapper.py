# packages/aoa-ocel/src/aoa/ocel/resource/ocel_store_wrapper.py
"""OcelStoreWrapper — proxy for nested actions (mirrors WrapperSqlResource)."""

from __future__ import annotations

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.ocel.dto.ocel_event import OcelEvent
from aoa.ocel.exceptions.ocel_resource_access_prohibited_error import (
    OcelResourceAccessProhibitedError,
)
from aoa.ocel.resource.ocel_store_protocol import OcelStoreProtocol


@exclude_graph_model
class OcelStoreWrapper(BaseResource, OcelStoreProtocol):
    """Proxy wrapper for OCEL store passed into nested actions via ``ToolsBox.run``.

    Delegates ``add_event``; ``open`` and ``close`` raise
    ``OcelResourceAccessProhibitedError`` (§5.27.2).
    """

    def __init__(self, resource: OcelStoreProtocol) -> None:
        self._resource = resource

    async def check_rollup_support(self) -> bool:
        return await self._resource.check_rollup_support()

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return OcelStoreWrapper

    async def open(self) -> None:
        raise OcelResourceAccessProhibitedError(
            "Opening OCEL store is allowed only in the action that created the resource. "
            "Current action received a proxy connection, so open is unavailable."
        )

    async def add_event(self, event: OcelEvent) -> None:
        await self._resource.add_event(event)

    async def close(self) -> None:
        raise OcelResourceAccessProhibitedError(
            "Closing OCEL store is allowed only in the action that created the resource. "
            "Current action received a proxy connection, so close is unavailable."
        )
