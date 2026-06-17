"""
Caching: key from params; cache only heavy runs (by duration_ms).

Tutorial: ../../docs/index_draft.md  ·  topic: Cache

Run:
    uv run python examples/step_08_cache/01_cache.py
"""
import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator

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


@meta(description="Get config (cached)", domain=RootDomain)
@check_roles(NoneRole)
class GetConfigAction(BaseAction[ConfigParams, ConfigResult]):

    def cache_key(self, params: ConfigParams) -> str | None:
        return f"{params.tenant_id}:{params.name}"

    async def on_cache_write(
        self,
        result: ConfigResult,
        params: ConfigParams,
        duration_ms: float,
    ) -> bool:
        write = duration_ms >= HEAVY_MIN_MS
        print(
            f"  on_cache_write: duration_ms={duration_ms:.1f}, "
            f"write={'yes' if write else 'no (too light)'}"
        )
        return write

    @summary_aspect("Load config")
    async def load_summary(self, params, state, box, connections):
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


asyncio.run(main())
