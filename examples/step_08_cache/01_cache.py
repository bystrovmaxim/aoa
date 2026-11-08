"""
Caching: a key from params, a write only for heavy runs, and an invalidation that drops it.

The cache is four declarations, like the object check: @cache_key, @cache_write,
@cache_read and @cache_invalidate. Each tag names an entity type, declared in tags=(...),
and the graph build checks that a type some action caches is one some action drops.

Run:
    uv run python examples/step_08_cache/01_cache.py
"""
import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.cache import cache_invalidate, cache_key, cache_write
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

# Cache only when the pipeline took at least this long (ms)
HEAVY_MIN_MS = 50.0


class RootDomain(BaseDomain):
    name = "root"
    description = "Root domain"


class ConfigParams(BaseParams):
    tenant_id: str = Field(description="Tenant ID")
    name: str = Field(description="Config name")


class ConfigResult(BaseResult):
    value: str = Field(description="Config value")


@entity(description="A tenant's configuration value", domain=RootDomain)
class ConfigCoreEntity(BaseCoreEntity):
    id: str = Field(description="tenant:name")


@meta(description="Stores the root entities")
@entities(
    ConfigCoreEntity,
)
class RootStorage(BaseStorage):
    """Hold the root entities."""


@meta(description="Get config (cached)", domain=RootDomain)
@check_roles(GuestRole)
class GetConfigAction(BaseAction[ConfigParams, ConfigResult]):
    @cache_key("Config by tenant and name")
    async def config_cache_key(self, params: ConfigParams, box: ToolsBox, connections: Connections) -> str | None:
        return f"{params.tenant_id}:{params.name}"

    @cache_write("Keep only heavy runs", tags=(ConfigCoreEntity,))
    async def config_cache_write(
        self,
        params: ConfigParams,
        box: ToolsBox,
        connections: Connections,
        result: ConfigResult,
        duration_ms: float,
    ) -> list[CacheTag] | None:
        if duration_ms < HEAVY_MIN_MS:
            print(f"  config_cache_write: duration_ms={duration_ms:.1f}, write=no (too light)")
            return None
        print(f"  config_cache_write: duration_ms={duration_ms:.1f}, write=yes")
        return [CacheTag(type=ConfigCoreEntity, key=f"{params.tenant_id}:{params.name}")]

    @summary_aspect("Load config")
    async def load_summary(self, params: ConfigParams, state: BaseState, box: ToolsBox, connections: Connections) -> ConfigResult:
        heavy = params.name != "ping"
        if heavy:
            await asyncio.sleep(0.08)
        await box.info(
            Channel.business,
            "{%var.kind} request: tenant={%var.tenant}, name={%var.name}",
            kind="heavy" if heavy else "light",
            tenant=params.tenant_id,
            name=params.name,
        )
        return ConfigResult(value=f"{params.tenant_id}:{params.name}:value")


@meta(description="Set config (drops the cached value)", domain=RootDomain)
@check_roles(GuestRole)
class SetConfigAction(BaseAction[ConfigParams, ConfigResult]):
    @cache_invalidate("Drop the changed value", tags=(ConfigCoreEntity,))
    async def config_cache_invalidate(
        self, params: ConfigParams, box: ToolsBox, connections: Connections, result: ConfigResult
    ) -> list[CacheTag] | None:
        print(f"  config_cache_invalidate: drop {params.tenant_id}:{params.name}")
        return [CacheTag(type=ConfigCoreEntity, key=f"{params.tenant_id}:{params.name}")]

    @summary_aspect("Store config")
    async def store_summary(self, params: ConfigParams, state: BaseState, box: ToolsBox, connections: Connections) -> ConfigResult:
        return ConfigResult(value=f"{params.tenant_id}:{params.name}:new-value")


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
        cache_coordinator=CacheCoordinator(),
    )

    print("Sample 06 cache — heavy request\n")
    params = ConfigParams(tenant_id="acme", name="feature-flags")
    await machine.run(Context(), GetConfigAction(), params=params)

    print("\nSample 06 cache — heavy again (cached)\n")
    await machine.run(Context(), GetConfigAction(), params=params)

    print("\nSample 06 cache — light request\n")
    await machine.run(
        Context(),
        GetConfigAction(),
        params=ConfigParams(tenant_id="acme", name="ping"),
    )

    print("\nSample 06 cache — light again (not in cache)\n")
    await machine.run(
        Context(),
        GetConfigAction(),
        params=ConfigParams(tenant_id="acme", name="ping"),
    )

    print("\nSample 06 cache — set the heavy value (drops it)\n")
    await machine.run(Context(), SetConfigAction(), params=params)

    print("\nSample 06 cache — heavy again (runs, cached anew)\n")
    await machine.run(Context(), GetConfigAction(), params=params)


asyncio.run(main())
