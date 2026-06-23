"""
01_connections.py — Supply a @connection at the adapter boundary (two modes)

An operation declares the open resources it needs with @connection; the adapter
supplies them per request through the keyword-only `connections=` argument on a
route (FastAPI) or tool (MCP). There are exactly two modes for a connection value:

  1. a ready BaseResource     -> the SAME instance is reused on every request
                                 (app-scoped: pool, client, in-memory store)
  2. PerCallConnection(factory)-> factory() runs on EVERY request -> a FRESH
                                 instance per request (per-request lifetime)

The adapter calls resolve_connections(...) before machine.run, so the operation
just reads connections["ledger"] — it never sees how the resource was supplied.

This example uses FastAPI's in-process TestClient; the same `connections=`
argument exists on McpAdapter.tool(...).

Tutorial: ../../docs/tutorials/step-17-connections_draft.md  ·  topic: connections at the boundary

Run:
    uv run python examples/step_17_connections/01_connections.py
"""

import itertools

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.adapters.fastapi import FastApiAdapter
from aoa.action_machine.auth import GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.per_call_connection import PerCallConnection
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class LedgerDomain(BaseDomain):
    name = "ledger"
    description = "Ledger domain"


@meta(description="In-memory ledger resource", domain=LedgerDomain)
class LedgerResource(BaseResource):
    """A stand-in open resource that remembers which instance handled the call."""

    _counter = itertools.count(1)

    def __init__(self) -> None:
        self.instance_id = next(LedgerResource._counter)
        self.entries: list[str] = []

    def get_wrapper_class(self):  # None -> direct pass-through into nested actions
        return None

    def record(self, note: str) -> None:
        self.entries.append(note)


class RecordParams(BaseParams):
    note: str = Field(description="Entry to append")


class RecordResult(BaseResult):
    ledger_id: int = Field(description="Which LedgerResource instance handled the request")
    entries: int = Field(description="How many entries that instance now holds")


@meta(description="Append an entry to the ledger", domain=LedgerDomain)
@check_roles(GuestRole)
@connection(LedgerResource, key="ledger")
class RecordAction(BaseAction[RecordParams, RecordResult]):

    @summary_aspect("Record entry")
    async def record_summary(self, params, state, box, connections):
        ledger = connections["ledger"]            # read the supplied resource by key
        ledger.record(params.note)
        return RecordResult(ledger_id=ledger.instance_id, entries=len(ledger.entries))


def build_app():
    machine = ActionProductMachine()
    shared_ledger = LedgerResource()              # built ONCE, at app-build time (instance #1)
    return (
        FastApiAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), title="Ledger API")
        # Mode 1: one ready resource, reused on every request to this route
        .post("/record/shared", RecordAction, connections={"ledger": shared_ledger})
        # Mode 2: a factory that runs per request -> a fresh resource each call
        .post("/record/percall", RecordAction,
              connections={"ledger": PerCallConnection(factory=lambda: LedgerResource())})
        .build()
    )


def main() -> None:
    client = TestClient(build_app())

    print("Mode 1 — ready BaseResource (shared, one instance):")
    for i in (1, 2):
        r = client.post("/record/shared", json={"note": f"call-{i}"})
        print(f"  POST /record/shared  call {i} -> {r.json()}")

    print("\nMode 2 — PerCallConnection (factory per request):")
    for i in (1, 2):
        r = client.post("/record/percall", json={"note": f"call-{i}"})
        print(f"  POST /record/percall call {i} -> {r.json()}")


if __name__ == "__main__":
    main()
