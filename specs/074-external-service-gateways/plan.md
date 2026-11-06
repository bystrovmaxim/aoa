# Implementation Plan: External services become gateways

**Branch**: `feature/issue-485-gateways` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

`src` = `packages/aoa-action-machine/src/aoa/action_machine`, `tests` = `packages/aoa-action-machine/tests/action_machine`.

## Design

- **Removal** — `src/resources/external_service/` loses `external_service_resource.py`, `wrapper_external_service_resource.py` and `protocol_external_service_resource.py`; its `__init__.py` exports only `ExternalServiceDataSource`. Their tests (`tests/resources/test_external_service_resource.py`, `test_wrapper_external_service_resource.py`) go; `tests/resources/__init__.py` and `tests/bench/test_bench_edges.py` drop their mentions.
- **A gateway** — `BaseGateway` is unchanged: `BaseResource.check_rollup_support()` and `get_wrapper_class()` already answer "no rollup" and "no wrapper", so a nested action gets the same gateway. A new test pins both.
- **The pattern** — a gateway takes its client in `__init__`, keeps it private (`self._client`), and has one public `async` method per thing the domain asks of the service, each calling the client:

  ```python
  @meta(description="Payment provider of the orders domain", domain=OrdersDomain)
  class PaymentGateway(BaseGateway):
      def __init__(self, client: PaymentClient) -> None:
          self._client = client

      async def charge(self, amount: float, currency: str) -> str:
          return await self._client.charge(amount, currency)
  ```

  `@depends(PaymentGateway, factory=lambda: PaymentGateway(PaymentClient()))` builds it; an aspect calls `await (await box.resolve(PaymentGateway)).charge(...)`.
- **Test bench** — `testing/bench.py::_reset_mock_tree` resets a mock passed as a resource, or every mock held in the resource's own attributes (`vars(resource)`), so a gateway built around a mock client is reset without naming any attribute; the `.service` and `_inner` branches go. `testing/mock_action.py`'s comment names a gateway.
- **Core test model** — `tests/support/domain_model/services.py`: `PaymentService`, `NotificationService`, `InventoryService` become `PaymentClient`, `NotificationClient`, `InventoryClient`; `PaymentServiceResource`, `NotificationServiceResource`, `InventoryServiceResource` become `PaymentGateway`, `NotificationGateway`, `InventoryGateway` with the clients' methods. Tests that built `XServiceResource(mock)` build `XGateway(mock)`; assertions on the mock client stay. `intents/compensate/__init__.py`'s docstring example follows.
- **Adapters' test models** — `aoa-langgraph` and `aoa-mcp-adapter` `tests/support/domain_model.py` follow the same renames.
- **The demo** — eight resources become gateways with the methods their actions call; their client classes become `…Client`:

  | Today | Gateway | Methods | Client |
  |---|---|---|---|
  | `PaymentGatewayResource` | `PaymentGateway` | `charge`, `refund` | `PaymentClient` |
  | `TaxQuoteServiceResource` | `TaxQuoteGateway` | `rate_for` | `TaxQuoteClient` |
  | `LedgerArchiveServiceResource` | `LedgerArchiveGateway` | `append` | `LedgerArchiveClient` |
  | `IndexSyncClientResource` | `IndexSyncGateway` | `upsert_document` | `IndexSyncClient` |
  | `PricingFeedClientResource` | `PricingFeedGateway` | `list_price` | `PricingFeedClient` |
  | `NotificationGatewayResource` | `NotificationGateway` (keeps `BaseGateway[NotificationGatewayDataSource]`) | `send` | `NotificationClient` |
  | `SmtpTransportStubResource` | `SmtpTransportGateway` | `send_raw` | `SmtpTransportClient` |
  | `WebhookFanoutStubResource` | `WebhookFanoutGateway` | `post` | `WebhookFanoutClient` |

  `invoice_settle.py`, `product_enrichment.py` and `publish_transactional.py` call the gateways' methods, compensators included; their `# type: ignore[attr-defined]` marks go with `.service`.
- **Graphs** — the demo's `graph.json` and every committed graph that holds these resources are rebuilt; their nodes become gateways.
- **Versions** — `aoa-action-machine` and `aoa-demo` raise their versions; any other level whose files change follows the version page.

## Constitution Check

One phase = one commit; adversarial verification on each phase's tests; the tail (check run, documentation, changelog); every changed level raises its version. Nothing is committed without the maintainer's word. No `type: ignore` is added; the removed ones go.
