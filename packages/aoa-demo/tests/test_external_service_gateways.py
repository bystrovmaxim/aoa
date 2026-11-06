# packages/aoa-demo/tests/test_external_service_gateways.py
"""The demo reaches each external service through a gateway that has its own methods."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.resources import BaseGateway
from aoa.demo.model.billing.resources.ledger_archive import LedgerArchiveClient, LedgerArchiveGateway
from aoa.demo.model.billing.resources.payment_gateway import PaymentClient, PaymentGateway
from aoa.demo.model.billing.resources.tax_quote import TaxQuoteClient, TaxQuoteGateway
from aoa.demo.model.catalog.resources.index_sync import IndexSyncClient, IndexSyncGateway
from aoa.demo.model.catalog.resources.pricing_feed import PricingFeedClient, PricingFeedGateway
from aoa.demo.model.messaging.resources.notification_gateway import NotificationClient, NotificationGateway
from aoa.demo.model.messaging.resources.smtp_transport import SmtpTransportClient, SmtpTransportGateway
from aoa.demo.model.messaging.resources.webhook_fanout import WebhookFanoutClient, WebhookFanoutGateway

# gateway, its client, one method, the arguments it takes, the answer the client gives
CALLS: list[tuple[type[Any], type, str, tuple[Any, ...], Any]] = [
    (PaymentGateway, PaymentClient, "charge", (12.5,), "TXN-1"),
    (PaymentGateway, PaymentClient, "refund", ("TXN-1",), None),
    (TaxQuoteGateway, TaxQuoteClient, "rate_for", ("EU",), 0.2),
    (LedgerArchiveGateway, LedgerArchiveClient, "append", ("captured", "{}"), "ROW-1"),
    (IndexSyncGateway, IndexSyncClient, "upsert_document", ("doc-1", {"sku": "A"}), "IDX-doc-1"),
    (PricingFeedGateway, PricingFeedClient, "list_price", ("A",), 9.9),
    (NotificationGateway, NotificationClient, "send", ("hello",), None),
    (SmtpTransportGateway, SmtpTransportClient, "send_raw", ("ops@example.com", "hello"), "250 OK"),
    (WebhookFanoutGateway, WebhookFanoutClient, "post", ("https://example.com/hook", "{}"), 202),
]


@pytest.mark.parametrize(
    ("gateway", "client", "method", "args", "answer"), CALLS, ids=lambda v: getattr(v, "__name__", None)
)
async def test_a_gateway_method_asks_its_client(
    gateway: type[Any], client: type, method: str, args: tuple[Any, ...], answer: Any
) -> None:
    """Each gateway method passes its arguments to the client's method and returns its answer."""
    mock = AsyncMock(spec=client)
    getattr(mock, method).return_value = answer
    assert await getattr(gateway(mock), method)(*args) == answer
    getattr(mock, method).assert_awaited_once_with(*args)


GATEWAYS: list[type[Any]] = [
    PaymentGateway,
    TaxQuoteGateway,
    LedgerArchiveGateway,
    IndexSyncGateway,
    PricingFeedGateway,
    NotificationGateway,
    SmtpTransportGateway,
    WebhookFanoutGateway,
]


@pytest.mark.parametrize("gateway", GATEWAYS, ids=[g.__name__ for g in GATEWAYS])
def test_each_external_service_is_a_gateway_without_a_raw_client(gateway: type[Any]) -> None:
    """A gateway, and no public way to the raw client."""
    assert issubclass(gateway, BaseGateway)
    assert not hasattr(gateway, "service")
