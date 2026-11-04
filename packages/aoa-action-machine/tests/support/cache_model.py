# packages/aoa-action-machine/tests/support/cache_model.py
"""
Entities the cache tests tag their entries with, and the action that drops them.

A cache tag names an entity type (issue #412), and the graph build refuses a type
some action caches that no action invalidates. Every test module that caches one of
these types imports this module, so the action below, which invalidates all of them,
is in each graph those modules build.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.cache import cache_invalidate
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.params_stub import ParamsStub
from aoa.action_machine.model.result_stub import ResultStub
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

from .domain_model.domains import OrdersDomain


@entity(description="A cached item of the cache tests", domain=OrdersDomain)
class CachedItemCoreEntity(BaseCoreEntity):
    """What a cached Result of the cache tests is about."""

    id: str = Field(description="Item id")


@entity(description="A cached report of the cache tests", domain=OrdersDomain)
class CachedReportCoreEntity(BaseCoreEntity):
    """A report, cached and dropped by the invalidation tests."""

    id: str = Field(description="Report id")


@entity(description="A cached invoice of the cache tests", domain=OrdersDomain)
class CachedInvoiceCoreEntity(BaseCoreEntity):
    """An invoice, cached and dropped by the invalidation tests."""

    id: str = Field(description="Invoice id")


CACHED_TYPES = (CachedItemCoreEntity, CachedReportCoreEntity, CachedInvoiceCoreEntity)


@meta(description="Drop every entry of the cache tests", domain=OrdersDomain)
@check_roles(GuestRole)
class ClearCachedModelAction(BaseAction[ParamsStub, ResultStub]):
    """Invalidates every type the cache tests cache."""

    @cache_invalidate("Drop every cached item, report and invoice", tags=CACHED_TYPES)
    async def clear_cache_invalidate(
        self, params: ParamsStub, box: ToolsBox, connections: Connections, result: ResultStub
    ) -> list[CacheTag] | None:
        return [CacheTag(type=entity_type) for entity_type in CACHED_TYPES]

    @summary_aspect("Clear")
    async def clear_summary(
        self, params: ParamsStub, state: BaseState, box: ToolsBox, connections: Connections
    ) -> ResultStub:
        return ResultStub()
