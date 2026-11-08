# packages/aoa-demo/src/aoa/demo/model/billing/resources/ledger_archive.py
"""Accounting journal: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway


class LedgerArchiveClient:
    async def append(self, event_type: str, payload: str) -> str:
        return "LEDGER-ROW-1"


@meta(
    description="Ledger archive gateway (stub)",
)
class LedgerArchiveGateway(BaseGateway):
    """The gateway to the ledger archive: its methods are what the domain asks of it."""

    def __init__(self, client: LedgerArchiveClient) -> None:
        self._client = client

    async def append(self, event_type: str, payload: str) -> str:
        """Ask the ledger archive: append."""
        return await self._client.append(event_type, payload)
