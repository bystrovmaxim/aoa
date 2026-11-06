# packages/aoa-action-machine/tests/action_machine/runtime/test_cache_hit_round_trip.py
"""
Rule 2 of #399 on a real cache hit: the bytes written to the store read back to the same state.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Phase 4 of issue #410. A Result with relations loaded, not loaded and loaded with
zero rows, a lifecycle and a dictionary value goes through the machine and a store
that keeps bytes; the hit is a new object with no observable difference from the
written one. The second test removes ``entities`` from the stored JSON, as a broken
store or serializer would, and shows the hit is then seen to differ.
"""

from __future__ import annotations

import json

from aoa.action_machine.context.context import Context
from aoa.action_machine.domain import observable_difference
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import cache_key, cache_write
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.stub_params import StubParams
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.cache_model import CachedItemCoreEntity
from ...support.domain_model.domains import OrdersDomain
from ...support.round_trip_model import RtLineCoreEntity, RtOrderResult, result


@meta(description="Caches an order Result of every value type", domain=OrdersDomain)
@check_roles(GuestRole)
class CachedOrderResultAction(BaseAction[StubParams, RtOrderResult]):
    """Answers with one order Result and caches it under one key."""

    @cache_key("One key")
    async def order_cache_key(self, params: StubParams, box: ToolsBox, connections: Connections) -> str | None:
        return "order"

    @cache_write("Keep it", tags=(CachedItemCoreEntity,))
    async def order_cache_write(
        self, params: StubParams, box: ToolsBox, connections: Connections, result: RtOrderResult, duration_ms: float
    ) -> list[CacheTag] | None:
        return [CacheTag(type=CachedItemCoreEntity, key="order")]

    @summary_aspect("Answer")
    async def order_summary(
        self, params: StubParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> RtOrderResult:
        return result(lines=(RtLineCoreEntity(id="l1", quantity=2),))


class BytesStoreCoordinator(CacheCoordinator):
    """The shipped store, keeping the last payload it was given so a test can read and edit it."""

    def __init__(self) -> None:
        super().__init__()
        self.payload = b""

    async def put(self, action_cls: type, user_key: str, payload: bytes, pipeline_duration_ms: float, tags: list[CacheTag] | None = None) -> None:
        self.payload = payload
        await super().put(action_cls, user_key, payload, pipeline_duration_ms, tags)


async def _miss_then_hit(*, drop_entities: bool) -> tuple[RtOrderResult, RtOrderResult, bytes]:
    store = BytesStoreCoordinator()
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]), cache_coordinator=store)
    written = await machine.run(Context(), CachedOrderResultAction(), StubParams())
    stored = store.payload
    if drop_entities:
        document = json.loads(stored)
        del document["order"]["lines"]["entities"]
        await store.put(CachedOrderResultAction, "order", json.dumps(document).encode(), 1.0)
    hit = await machine.run(Context(), CachedOrderResultAction(), StubParams())
    return written, hit, stored


async def test_a_hit_reads_the_written_bytes_back_to_the_same_state() -> None:
    """The store holds the Result's JSON, and the hit is a new object with the same observable state."""
    written, hit, stored = await _miss_then_hit(drop_entities=False)
    assert stored == written.model_dump_json().encode()
    assert hit is not written
    assert observable_difference(written, hit) is None
    assert hit.order.lines.is_loaded and hit.history[0].lines.is_loaded is False


async def test_a_hit_that_lost_the_loaded_entities_is_seen_to_differ() -> None:
    """The adversarial case: without ``entities`` the lines read back as not loaded."""
    written, hit, _ = await _miss_then_hit(drop_entities=True)
    assert observable_difference(written, hit) == "$.order.lines: loaded True != False"
