# Feature Specification: External services become gateways

**Feature Branch**: `feature/issue-485-gateways`

**Created**: 2026-11-06

**Status**: Draft

**Input**: Issue #485, "External services become gateways; ExternalServiceResource is removed". Step 2 of the root issue #488: a resource is a database, and the model knows no store.

## What this is

A resource is the point that controls what leaves a store or a service. An external service is reached through a gateway — "I ask someone else's service to do something", as the constitution defines it — and the gateway says, by its own methods, what the domain asks of that service. An action calls those methods; it never holds the service's raw client. So the machine can see every answer a resource gives, which the check of #487 relies on.

## Clarifications

### Session 2026-11-06

- Q: What is removed? → A: `ExternalServiceResource`, `WrapperExternalServiceResource` and `ProtocolExternalServiceResource`, with their tests and exports. `ExternalServiceDataSource` stays where it is until #487 removes every data source; the package keeps only it.
- Q: What does a gateway answer to the machine? → A: The defaults of `BaseResource`: no rollup support, and no wrapper class, so a nested action gets the same gateway. A gateway holds no transaction that a nested action could end.
- Q: How does a gateway reach the service? → A: Through a client it is given when it is built, kept private. Its public methods are what the domain asks of the service.
- Q: Which demo resources move? → A: The eight external services: payment, tax quote, ledger archive (Billing); index sync, pricing feed (Catalog); notifications, SMTP transport, webhook fan-out (Messaging). Each becomes a gateway named `…Gateway` with the methods its actions call; each client class becomes `…Client`. The notification gateway keeps naming its data source until #487.
- Q: What does the test bench substitute? → A: A gateway's methods, the same way it substitutes any resource's; it no longer unwraps `.service` or a wrapper's `_inner`.
- Q: Do the graphs change? → A: The eight resources become gateways: their nodes keep their place, change their kind from controller to gateway, and are renamed. The demo's graph and the adapters' test graphs are rebuilt.

## User Scenarios & Testing

### User Story 1 - Ask an external service through a gateway (Priority: P1)

A developer reaches a payment provider. They write a `PaymentGateway(BaseGateway)` with a `charge` method that calls the provider's client, declare it with `@depends`, and call `await gateway.charge(...)` in an aspect.

**Acceptance Scenarios**:

1. **Given** a gateway with its own methods declared with `@depends(..., factory=...)`, **When** an aspect resolves it and calls a method, **Then** the method's answer reaches the aspect.
2. **Given** that gateway, **When** a nested action resolves it, **Then** it gets the same gateway, and the root run's rollup check refuses it as before.
3. **Given** the AOA package, **When** a developer imports `ExternalServiceResource`, `WrapperExternalServiceResource` or `ProtocolExternalServiceResource`, **Then** the import fails: none of them exists.

### User Story 2 - Test an action that uses a gateway (Priority: P1)

A developer tests an action whose aspect calls `gateway.charge(...)`. They substitute the gateway in the test bench with a mock whose `charge` answers a fixed transaction id.

**Acceptance Scenarios**:

1. **Given** a bench with a substituted gateway, **When** the action runs, **Then** the aspect gets the mock's answer, and the bench's run report names the call.
2. **Given** the bench, **When** it walks a substituted resource, **Then** it reads the resource's own methods; it has no `.service` or `_inner` path.

### User Story 3 - The demo reaches its services through gateways (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the demo, **When** its actions settle an invoice, enrich a product or publish a message, **Then** they call the gateways' methods, and no aspect reads `.service`.
2. **Given** the demo's graph, **When** it is rebuilt, **Then** the eight services are gateways.

### Edge Cases

- A gateway that names a data source (the notification gateway, the card network's two gateways) keeps naming it until #487.
- A compensator that calls a gateway (the payment refund, the index tombstone, the notification undo) calls its method the same way an aspect does.

## Requirements

### Functional Requirements

- **FR-001**: `ExternalServiceResource`, `WrapperExternalServiceResource` and `ProtocolExternalServiceResource` are removed from AOA, with their exports, tests and every mention in the API's examples.
- **FR-002**: `ExternalServiceDataSource` stays, alone in its package, until #487.
- **FR-003**: A gateway keeps the defaults of `BaseResource` for rollup support and the wrapper class; tests show a nested action gets the same gateway and a rollup run refuses it.
- **FR-004**: The test bench substitutes a gateway's methods; its `.service` and `_inner` paths are removed; its tests say so.
- **FR-005**: The demo's eight external services are gateways with their own methods (`PaymentGateway.charge` and `refund`, `TaxQuoteGateway.rate_for`, `LedgerArchiveGateway.append`, `IndexSyncGateway.upsert_document`, `PricingFeedGateway.list_price`, `NotificationGateway.send`, `SmtpTransportGateway.send_raw`, `WebhookFanoutGateway.post`); their clients are `…Client`; their actions and compensators call the gateways' methods.
- **FR-006**: The test models of `aoa-action-machine`, `aoa-langgraph` and `aoa-mcp-adapter` follow FR-005's pattern.
- **FR-007**: The graph files are rebuilt; every changed level raises its version.
- **FR-008**: Documentation: the architectural constitution page, the resource tutorial and the getting-started page show a gateway with its own methods; the testing page shows substituting one. One changelog article.

## Success Criteria

- **SC-001**: No file outside `specs/` names `ExternalServiceResource`, `WrapperExternalServiceResource`, `ProtocolExternalServiceResource` or reads `.service` of a resource.
- **SC-002**: The tests of FR-003 and FR-004 fail when the behaviour they guard is broken, and no other test of the phase does.
- **SC-003**: The demo's tests and graph build pass; the demo's graph has eight gateways in place of the eight controllers.
- **SC-004**: The closing check run on the pull request is green.

## Assumptions

- Naming rules for resource kinds come in #486; the names chosen here already end with their kind, so #486 does not rename them again.
- The notification gateway's data source and the card network's data source are removed by #487, with every other data source.
