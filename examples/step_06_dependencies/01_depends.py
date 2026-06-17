"""
01_depends.py — Dependencies (@depends) and connections (@connection)

Two ways to bring the outside world into an Action, both declared in the header:

  @depends(Cls)      — a dependency the machine builds on demand; the aspect gets
                       it via `await box.resolve(Cls)`. Undeclared classes cannot
                       be resolved.
  @connection(Cls,   — an already-open resource passed into machine.run(...) under
              key=)    a string key; the aspect reads it via connections["key"].

When a parent passes a connection into a nested action via box.run(...), the
machine wraps it in a proxy: the nested action may run statements but cannot
commit or rollback — only the owner controls the transaction.

Tutorial: ../../docs/index_draft.md  ·  topic: Dependencies

Run:
    uv run python examples/step_06_dependencies/01_depends.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.transaction_prohibited_error import TransactionProhibitedError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_float
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class BillingDomain(BaseDomain):
    name = "billing"
    description = "Billing domain"


# ---------------------------------------------------------------------------
# A dependency: a stateless pricing service. Declared via @depends, created by
# the factory on box.resolve(...). Resources implement get_wrapper_class();
# stateless ones return None (no transaction proxy needed).
# ---------------------------------------------------------------------------

@meta(description="Stateless pricing service", domain=BillingDomain)
class PricingService(BaseResource):
    PRICES = {"sku-1": 8990.0, "sku-2": 490.0}

    def price(self, sku: str) -> float:
        return self.PRICES.get(sku, 0.0)

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None


# ---------------------------------------------------------------------------
# A connection: a transactional ledger. The owner action can commit; a nested
# action receives a proxy (LedgerProxy) that allows execute() but forbids
# commit()/rollback().
# ---------------------------------------------------------------------------

@meta(description="Append-only transaction ledger", domain=BillingDomain)
class LedgerResource(BaseResource):
    def __init__(self) -> None:
        self._rows: list[str] = []

    async def execute(self, entry: str) -> None:
        self._rows.append(entry)
        print(f"  [ledger] execute: {entry}")

    async def commit(self) -> None:
        print(f"  [ledger] COMMIT ({len(self._rows)} rows)")

    async def rollback(self) -> None:
        print("  [ledger] ROLLBACK")

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return LedgerProxy


@exclude_graph_model
class LedgerProxy(BaseResource):
    """Proxy handed to nested actions: statements yes, transaction control no."""

    def __init__(self, inner: LedgerResource) -> None:
        self._inner = inner

    async def execute(self, entry: str) -> None:
        await self._inner.execute(entry)

    async def commit(self) -> None:
        raise TransactionProhibitedError("commit is not allowed in a nested action")

    async def rollback(self) -> None:
        raise TransactionProhibitedError("rollback is not allowed in a nested action")

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return LedgerProxy  # stays a proxy at deeper nesting levels


# ---------------------------------------------------------------------------
# Nested action: appends an audit entry. It owns no transaction, so its commit
# is blocked by the proxy — it may only run statements.
# ---------------------------------------------------------------------------

class EntryParams(BaseParams):
    entry: str = Field(description="Audit entry text")


class EntryResult(BaseResult):
    written: bool = Field(description="Whether the entry was written")


@meta(description="Append an audit entry", domain=BillingDomain)
@check_roles(NoneRole)
@connection(LedgerResource, key="ledger")
class AppendEntryAction(BaseAction[EntryParams, EntryResult]):

    @summary_aspect("Append audit entry")
    async def append_summary(self, params, state, box, connections):
        ledger = connections["ledger"]
        await ledger.execute(params.entry)          # statements: allowed
        try:
            await ledger.commit()                   # transaction control: blocked
        except TransactionProhibitedError:
            await box.info(Channel.business, "  child: commit blocked (owns no transaction)")
        return EntryResult(written=True)


# ---------------------------------------------------------------------------
# Parent action: resolves a dependency, writes to the ledger it owns, calls the
# nested action (passing the same ledger — now proxied), then commits.
# ---------------------------------------------------------------------------

class ChargeParams(BaseParams):
    sku: str = Field(description="Product SKU")
    qty: int = Field(description="Quantity")


class ChargeResult(BaseResult):
    sku: str = Field(description="Product SKU")
    total: float = Field(description="Charged total")


@meta(description="Charge for a product", domain=BillingDomain)
@check_roles(NoneRole)
@depends(PricingService)
@connection(LedgerResource, key="ledger")
class ChargeAction(BaseAction[ChargeParams, ChargeResult]):

    @regular_aspect("Compute total via the pricing service")
    @result_float("total", required=True, min_value=0)
    async def price_aspect(self, params, state, box, connections):
        pricing = await box.resolve(PricingService)       # declared dependency
        total = pricing.price(params.sku) * params.qty
        await box.info(Channel.business, "parent: total={%var.total}", total=total)
        return {"total": total}

    @regular_aspect("Record to ledger and call nested action")
    @result_float("total", required=True, min_value=0)
    async def record_aspect(self, params, state, box, connections):
        ledger = connections["ledger"]
        await ledger.execute(f"charge {params.sku} = {state['total']}")
        await box.run(                                    # nested call: ledger is proxied
            AppendEntryAction,
            EntryParams(entry=f"audit:{params.sku}"),
            connections={"ledger": ledger},
        )
        return {"total": state["total"]}

    @summary_aspect("Commit and return")
    async def charge_summary(self, params, state, box, connections):
        await connections["ledger"].commit()             # owner: commit allowed
        return ChargeResult(sku=params.sku, total=state["total"])


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    ledger = LedgerResource()
    result = await machine.run(
        Context(),
        ChargeAction(),
        ChargeParams(sku="sku-1", qty=2),
        connections={"ledger": ledger},
    )
    print(f"\nResult: sku={result.sku}, total={result.total}")


asyncio.run(main())
