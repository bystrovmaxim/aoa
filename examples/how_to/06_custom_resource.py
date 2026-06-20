"""
06_custom_resource.py — Write your own resource

A resource is the long-lived TRANSPORT to an external world (DB, queue, API
client, store) — open, execute, return. No business rules; the decisions live in
the Action. To add a new source of data behind the same contract, subclass
`BaseResource`, declare `@meta`, and implement one abstract method:

    get_wrapper_class() -> type[BaseResource] | None

The wrapper is the distinctive part. When a resource is propagated to a NESTED
action, the machine substitutes `get_wrapper_class()(...)` so child code can
*use* the resource but not *control* its transaction. Three shapes:

  - None                -> direct pass-through (simple, non-transactional; see step-19)
  - delegating wrapper  -> passes the same client/handle deeper (external services)
  - blocking wrapper    -> delegates `execute`, raises TransactionProhibitedError
                           on open/begin/commit/rollback (transactional resources)

This example builds a transactional in-memory ledger and proves the blocking
wrapper: a nested action may `execute`, but `commit` is refused.

How-to: ../../docs/how-to/authoring-resource_draft.md

Run:
    uv run python examples/how_to/06_custom_resource.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import TransactionProhibitedError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class LedgerDomain(BaseDomain):
    name = "ledger"
    description = "Ledger domain"


# ── Wrapper: nested actions execute, but never control the transaction ───────
@meta(description="Ledger handle for nested actions (no txn control)", domain=LedgerDomain)
class LedgerWrapper(BaseResource):
    def __init__(self, inner: "LedgerResource") -> None:
        self._inner = inner

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return LedgerWrapper                              # deeper nesting keeps the guarantee

    async def execute(self, entry: str) -> int:
        return await self._inner.execute(entry)          # delegated — execution is allowed

    async def open(self) -> None:
        raise TransactionProhibitedError("nested actions cannot open the transaction")

    async def begin(self) -> None:
        raise TransactionProhibitedError("nested actions cannot begin the transaction")

    async def commit(self) -> None:
        raise TransactionProhibitedError("nested actions cannot commit the owner's transaction")

    async def rollback(self) -> None:
        raise TransactionProhibitedError("nested actions cannot roll back the owner's transaction")


# ── Manager: full transport — owns the transaction, returns the wrapper ──────
@meta(description="In-memory ledger (transport only)", domain=LedgerDomain)
class LedgerResource(BaseResource):
    def __init__(self) -> None:
        self._entries: list[str] = []
        self.committed: list[str] | None = None

    def get_wrapper_class(self) -> type[BaseResource] | None:
        return LedgerWrapper                              # nested actions get the blocking proxy

    async def open(self) -> None:
        self._entries = []

    async def begin(self) -> None:
        self._entries = []

    async def execute(self, entry: str) -> int:
        self._entries.append(entry)
        return len(self._entries)

    async def commit(self) -> None:
        self.committed = list(self._entries)

    async def rollback(self) -> None:
        self._entries = []


# ── A normal Action — the decision lives here, transport in the resource ─────
class PostParams(BaseParams):
    entry: str = Field(description="Ledger entry")


class PostResult(BaseResult):
    count: int = Field(description="Entries in the open transaction")


@meta(description="Post a ledger entry", domain=LedgerDomain)
@check_roles(GuestRole)
@connection(LedgerResource, key="ledger")
class PostEntryAction(BaseAction[PostParams, PostResult]):
    @summary_aspect("Post entry")
    async def post_summary(self, params, state, box, connections):
        count = await connections["ledger"].execute(params.entry)   # transport, supplied per call
        return PostResult(count=count)


async def main() -> None:
    machine = ActionProductMachine()

    ledger = LedgerResource()
    await ledger.open()
    result = await machine.run(Context(), PostEntryAction(), PostParams(entry="debit 100"),
                               {"ledger": ledger})
    await ledger.commit()
    print(f"root: posted entry, count={result.count}, committed={ledger.committed}")

    # What a NESTED action would receive — the wrapper the runtime substitutes:
    wrapper = ledger.get_wrapper_class()(ledger)
    print("nested: execute ->", await wrapper.execute("credit 100"))     # delegated, works
    try:
        await wrapper.commit()
    except TransactionProhibitedError as exc:
        print(f"nested: commit refused -> {type(exc).__name__}")


if __name__ == "__main__":
    asyncio.run(main())
