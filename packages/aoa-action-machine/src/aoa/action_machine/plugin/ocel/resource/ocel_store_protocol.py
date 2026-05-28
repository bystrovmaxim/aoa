# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/resource/ocel_store_protocol.py
# pylint: disable=unnecessary-ellipsis  # Protocol member bodies use ellipsis per PEP 544 stubs.
"""OcelStoreProtocol — full public OCEL store interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from aoa.action_machine.plugin.ocel.dto.ocel_event import OcelEvent


class OcelStoreProtocol(Protocol):
    """Full public protocol for OCEL store (§5.27)."""

    async def check_rollup_support(self) -> bool:
        """Same contract as ``BaseResource.check_rollup_support``."""
        ...

    async def open(self) -> None: ...

    async def add_event(self, event: OcelEvent) -> None: ...

    async def close(self) -> None: ...
