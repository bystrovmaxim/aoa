"""
01_substitution.py — Substituting the environment in tests (one test per topic)

TestBench keeps the Action real and swaps the world around it.

  with_mocks({Cls: value})    — keyed by CLASS; substitutes what an aspect
                                box.resolve()s: a @depends dependency / resource.
                                These mocks reach the WHOLE tree, so a nested
                                Action invoked via box.run() runs for real but
                                with ITS dependencies mocked too.
  connections={key: resource} — keyed by STRING key (the run argument); supplies
                                a @connection resource per call (real or a mock).

Rollup (rollup=True) continues the resource/connection theme: a rollup-capable
resource runs the real pipeline but rolls back on commit; an unsupported one
fails fast via check_rollup_support().

NOTE: box.run(NestedClass) always runs the REAL nested Action — with_mocks does
NOT replace its result wholesale; mock the nested Action's dependencies instead.

All Actions are @check_roles(GuestRole) (context/roles are ch.25).

Tutorial: ../../docs/tutorials/step-24-substitution_draft.md  ·  topic: environment substitution

Run:
    uv run python examples/step_24_substitution/01_substitution.py
"""

import asyncio
from unittest.mock import AsyncMock

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.rollup_not_supported_error import RollupNotSupportedError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.testing import TestBench


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


# ── Two @depends resources (no rollup support → default check_rollup_support raises) ──
@meta(description="Pricing service", domain=ShopDomain)
class PricingService(BaseResource):
    def price(self, sku: str) -> float:
        return {"sku-1": 8990.0}.get(sku, 0.0)

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None


@meta(description="Stock gateway", domain=ShopDomain)
class StockGateway(BaseResource):
    async def reserve(self, sku: str, qty: int) -> str:
        raise NotImplementedError("real gateway — mocked in tests")

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None


# ── 1 — a plain @depends user ────────────────────────────────────────────────
class QuoteParams(BaseParams):
    sku: str = Field(description="SKU")


class QuoteResult(BaseResult):
    price: float = Field(description="Unit price")


@meta(description="Quote a price", domain=ShopDomain)
@check_roles(GuestRole)
@depends(PricingService)
class QuoteAction(BaseAction[QuoteParams, QuoteResult]):
    @summary_aspect("Quote")
    async def quote_summary(self, params, state, box, connections):
        return QuoteResult(price=(await box.resolve(PricingService)).price(params.sku))


# ── 2 — a nested Action (its dependency is what gets mocked) ──────────────────
class ReserveParams(BaseParams):
    sku: str = Field(description="SKU")
    qty: int = Field(gt=0, description="Quantity")


class ReserveResult(BaseResult):
    reservation_id: str = Field(description="Reservation id")


@meta(description="Reserve stock", domain=ShopDomain)
@check_roles(GuestRole)
@depends(StockGateway)
class ReserveStockAction(BaseAction[ReserveParams, ReserveResult]):
    @summary_aspect("Reserve")
    async def reserve_summary(self, params, state, box, connections):
        gateway = await box.resolve(StockGateway)
        return ReserveResult(reservation_id=await gateway.reserve(params.sku, params.qty))


class CheckoutParams(BaseParams):
    sku: str = Field(description="SKU")
    qty: int = Field(gt=0, description="Quantity")


class CheckoutResult(BaseResult):
    reservation_id: str = Field(description="Reservation id")


@meta(description="Checkout", domain=ShopDomain)
@check_roles(GuestRole)
class CheckoutAction(BaseAction[CheckoutParams, CheckoutResult]):
    @summary_aspect("Checkout")
    async def checkout_summary(self, params, state, box, connections):
        reservation = await box.run(ReserveStockAction, ReserveParams(sku=params.sku, qty=params.qty))
        return CheckoutResult(reservation_id=reservation.reservation_id)


# ── 3/5 — a @connection journal that supports rollup ─────────────────────────
@meta(description="Append-only journal", domain=ShopDomain)
class JournalResource(BaseResource):
    def __init__(self, rollup: bool = False) -> None:
        self._rollup = rollup
        self.persisted: list[str] = []
        self._pending: list[str] = []

    async def check_rollup_support(self) -> bool:
        return True

    async def write(self, row: str) -> None:
        self._pending.append(row)

    async def commit(self) -> None:
        if self._rollup:
            self._pending.clear()            # rollback instead of persist
        else:
            self.persisted.extend(self._pending)
            self._pending.clear()

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return None


class RecordParams(BaseParams):
    row: str = Field(description="Row to write")


class RecordResult(BaseResult):
    row: str = Field(description="Row written this call")
    committed: bool = Field(description="Whether commit ran")


@meta(description="Record a row", domain=ShopDomain)
@check_roles(GuestRole)
@connection(JournalResource, key="journal")
class RecordAction(BaseAction[RecordParams, RecordResult]):
    @summary_aspect("Write and commit")
    async def record_summary(self, params, state, box, connections):
        journal = connections["journal"]
        await journal.write(params.row)
        await journal.commit()
        # TestBench.run cross-checks on the async AND sync machine, so the Result
        # must not depend on cumulative side-effects — we assert on the journal after.
        return RecordResult(row=params.row, committed=True)


async def main() -> None:
    # 1. Mock a @depends dependency (class-keyed).
    pricing = AsyncMock(spec=PricingService)
    pricing.price.return_value = 100.0
    r = await TestBench().with_mocks({PricingService: pricing}).run(
        QuoteAction(), QuoteParams(sku="sku-1"), rollup=False,
    )
    print(f"1) mock @depends            -> price={r.price}")

    # 2. Nested Action: box.run runs it for real, but its @depends is mocked.
    gateway = AsyncMock(spec=StockGateway)
    gateway.reserve.return_value = "res-001"
    r = await TestBench().with_mocks({StockGateway: gateway}).run(
        CheckoutAction(), CheckoutParams(sku="sku-1", qty=1), rollup=False,
    )
    print(f"2) nested Action, mocked dep-> reservation={r.reservation_id}  (mock reached the child)")

    # 3. Supply a @connection per run (connections= kwarg, string-keyed).
    journal = JournalResource()
    r = await TestBench().run(
        RecordAction(), RecordParams(row="row-A"), rollup=False, connections={"journal": journal},
    )
    print(f"3) supply @connection       -> committed={r.committed}  (row-A persisted: {'row-A' in journal.persisted})")

    # 4. Rollup fail-fast: the REAL (un-mocked) resource has no rollup support.
    try:
        await TestBench().run(QuoteAction(), QuoteParams(sku="sku-1"), rollup=True)
    except RollupNotSupportedError as exc:
        print(f"4) rollup, unsupported res  -> RollupNotSupportedError: {str(exc).splitlines()[0]}")

    # 5. Rollup commit→rollback: rollup-capable journal persists nothing.
    journal = JournalResource(rollup=True)
    r = await TestBench().run(
        RecordAction(), RecordParams(row="row-B"), rollup=True, connections={"journal": journal},
    )
    print(f"5) rollup, capable res      -> committed={r.committed}  (nothing persisted: {journal.persisted == []})")


if __name__ == "__main__":
    asyncio.run(main())
