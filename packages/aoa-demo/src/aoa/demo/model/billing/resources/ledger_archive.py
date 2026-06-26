# packages/aoa-demo/src/aoa/demo/model/billing/resources/ledger_archive.py
"""Accounting journal stub for ``@depends`` and ``connections`` resource manager."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service import ExternalServiceResource
from aoa.demo.model.billing.domain import BillingDomain


class LedgerArchiveService:
    async def append(self, event_type: str, payload: str) -> str:
        return "LEDGER-ROW-1"


@meta(
    description="Ledger archive client for aspects/connections (stub)",
    domain=BillingDomain,
)
class LedgerArchiveServiceResource(ExternalServiceResource[LedgerArchiveService]):
    pass
