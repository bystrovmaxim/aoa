"""
Full AOA example: pipeline, roles, saga, on_error, cache, logging.

Run:
    uv run python examples/full_example.py
"""
import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import Channel, ConsoleLogger, Level
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


# ---------------------------------------------------------------------------
# Params & Result
# ---------------------------------------------------------------------------


class CreateOrderParams(BaseParams):
    order_id: str = Field(description="Order ID")
    fail_at: str | None = Field(
        default=None,
        description="Simulated failure: 'charge' or 'summary'",
    )


class CreateOrderResult(BaseResult):
    order_id: str = Field(description="Created order ID")
    reservation_id: str = Field(description="Reservation ID")
    txn_id: str = Field(description="Transaction ID")
    status: str = Field(description="Execution status")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class InsufficientFundsError(Exception):
    pass


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------


@meta(description="Create order", domain=StoreDomain)
@check_roles(NoneRole)
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

    # ── Caching ──────────────────────────────────────────────────────────────

    def cache_key(self, params: CreateOrderParams) -> str | None:
        if params.fail_at:
            return None
        return params.order_id

    async def on_cache_write(
        self,
        result: CreateOrderResult,
        params: CreateOrderParams,
        duration_ms: float,
    ) -> bool:
        return result.status == "ok"

    # ── Pipeline ─────────────────────────────────────────────────────────────

    @regular_aspect("Validate order")
    @result_string("validated_id", required=True, min_length=1)
    async def validate_aspect(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[1] validate: order_id={%var.order_id}",
            order_id=params.order_id,
        )
        return {"validated_id": params.order_id}

    @regular_aspect("Reserve inventory")
    @result_string("validated_id", required=True)
    @result_string("reservation_id", required=True)
    async def reserve_aspect(self, params, state, box, connections):
        reservation_id = f"res-{state['validated_id']}"
        await box.info(
            Channel.business,
            "[2] reserve: reservation_id={%var.rid}",
            rid=reservation_id,
        )
        return {
            "validated_id": state["validated_id"],
            "reservation_id": reservation_id,
        }

    @compensate("reserve_aspect", "Release reservation")
    async def reserve_compensate(self, params, state_before, state_after, box, connections, error):
        rid = (state_after or {}).get("reservation_id", "?")
        await box.warning(
            Channel.business,
            "[compensate] release reservation: reservation_id={%var.rid}",
            rid=rid,
        )

    @regular_aspect("Charge payment")
    @result_string("validated_id", required=True)
    @result_string("reservation_id", required=True)
    @result_string("txn_id", required=True)
    async def charge_aspect(self, params, state, box, connections):
        if params.fail_at == "charge":
            raise InsufficientFundsError("insufficient funds on account")
        txn_id = f"txn-{state['validated_id']}"
        await box.info(
            Channel.business,
            "[3] charge: txn_id={%var.txn}",
            txn=txn_id,
        )
        return {
            "validated_id": state["validated_id"],
            "reservation_id": state["reservation_id"],
            "txn_id": txn_id,
        }

    @compensate("charge_aspect", "Refund payment")
    async def charge_compensate(self, params, state_before, state_after, box, connections, error):
        txn = (state_after or {}).get("txn_id", "?")
        await box.warning(
            Channel.business,
            "[compensate] refund payment: txn_id={%var.txn}",
            txn=txn,
        )

    @summary_aspect("Build result")
    async def create_summary(self, params, state, box, connections):
        if params.fail_at == "summary":
            raise RuntimeError("unexpected summary failure")
        result = CreateOrderResult(
            order_id=state["validated_id"],
            reservation_id=state["reservation_id"],
            txn_id=state["txn_id"],
            status="ok",
        )
        await box.info(
            Channel.business,
            "[4] done: order_id={%var.order_id}, status={%var.status}",
            order_id=result.order_id,
            status=result.status,
        )
        return result

    # ── Error handlers ───────────────────────────────────────────────────────

    @on_error(InsufficientFundsError, description="Insufficient funds")
    async def insufficient_funds_on_error(self, params, state, box, connections, error):
        await box.warning(
            Channel.business,
            "[on_error] insufficient funds: {%var.msg}",
            msg=str(error),
        )
        return CreateOrderResult(
            order_id=params.order_id,
            reservation_id=state.get("reservation_id", ""),
            txn_id="",
            status="insufficient_funds",
        )

    @on_error(Exception, description="Unexpected error")
    async def fallback_on_error(self, params, state, box, connections, error):
        await box.warning(
            Channel.business,
            "[on_error] unexpected: {%var.msg}",
            msg=str(error),
        )
        return CreateOrderResult(
            order_id=params.order_id,
            reservation_id=state.get("reservation_id", ""),
            txn_id="",
            status="error",
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def run(machine: ActionProductMachine, label: str, params: CreateOrderParams) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")
    result = await machine.run(Context(), CreateOrderAction(), params=params)
    print(f"\n  → order_id={result.order_id}, status={result.status}, txn_id={result.txn_id or '—'}\n")


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(
            loggers=[ConsoleLogger().subscribe("console", levels=Level.info | Level.warning)]
        ),
        cache_coordinator=CacheCoordinator(),
    )

    await run(machine, "1. Successful run", CreateOrderParams(order_id="ord-001"))
    await run(machine, "2. Repeat call (from cache)", CreateOrderParams(order_id="ord-001"))
    await run(
        machine,
        "3. Charge failure → saga + on_error",
        CreateOrderParams(order_id="ord-002", fail_at="charge"),
    )
    await run(
        machine,
        "4. Summary failure → saga + fallback on_error",
        CreateOrderParams(order_id="ord-003", fail_at="summary"),
    )


asyncio.run(main())
