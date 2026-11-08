# Tasks: External services become gateways

One phase = one commit, referencing (#485). After a phase only its own tests run; every new test is broken once on purpose.

- [x] T001 [US1] Phase 1: remove `ExternalServiceResource`, `WrapperExternalServiceResource` and `ProtocolExternalServiceResource` from `src/resources/external_service/` (its `__init__.py` exports only `ExternalServiceDataSource`) with their tests; a test pins that a gateway answers no rollup and no wrapper class, so a nested action gets the same gateway; the core test model `tests/support/domain_model/services.py` gets `PaymentGateway`, `NotificationGateway`, `InventoryGateway` around `PaymentClient`, `NotificationClient`, `InventoryClient`, and every core test that used the old resources follows; the `intents/compensate/__init__.py` example follows
- [x] T002 [US2] Phase 2: `testing/bench.py::_reset_mock_tree` resets a mock resource or the mocks in a resource's own attributes, without `.service` or `_inner`; `testing/mock_action.py`'s comment names a gateway; bench tests of a gateway around a mock client
- [x] T003 [US3] Phase 3: the demo's eight external services become gateways (`PaymentGateway`, `TaxQuoteGateway`, `LedgerArchiveGateway`, `IndexSyncGateway`, `PricingFeedGateway`, `NotificationGateway`, `SmtpTransportGateway`, `WebhookFanoutGateway`) around `…Client` classes; `invoice_settle.py`, `product_enrichment.py`, `publish_transactional.py` call their methods, compensators included, without `.service`; a demo test of each gateway method
- [x] T004 Phase 4: the test models of `aoa-langgraph` and `aoa-mcp-adapter` (`tests/support/domain_model.py`) follow; `scripts/check_maxitor_samples_public_api.py` and every example and notebook that names the removed classes
- [x] T005 Phase 5: rebuild the graph files, raise the versions
- [x] T006 Phase 6: the closing check run on the pull request, taken to zero
- [x] T007 Phase 7: documentation — `docs/explanation/architectural-constitution.md`, `docs/tutorials/step-21-resource.md` and `docs/tutorials/step-00-get-started.md` show a gateway with its own methods; the testing page shows substituting one
- [x] T008 Phase 8: changelog

## Dependencies

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008. T002 needs the gateways of T001's test model; T003 and T004 are independent of each other but share the version phase.
