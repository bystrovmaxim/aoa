# Feature Specification: The demo shows the logical data model

**Feature Branch**: `feature/issue-480-demo-logical-model`

**Created**: 2026-11-06

**Status**: Draft

**Input**: Issue #480, "Logical data model 3/4: the demo follows the rules". The rules themselves, and the demo's compliance with them, are #479.

## What this is

After #479 a relation knows no store and every stored entity has one. The demo shows both on top of following the rules: a relation that leaves a data source, and an external service two domains share.

## Requirements

- **FR-001**: `ChargebackTicketCoreEntity` (Billing, `BillingWarehouseDataSource`) has an association `order` to `SalesOrderCoreEntity` (Store, `ShopDataSource`): a relation across two databases.
- **FR-002**: `CardNetworkDataSource`, an external service, is named by two resources of two domains: `CardNetworkGateway` (Billing) and `StorefrontCardGateway` (Store).
- **FR-003**: The demo's graph is rebuilt; `aoa-demo` raises its version.
- **FR-004**: The demo's page on its stores names both; one changelog article.

## Success Criteria

- **SC-001**: A demo test finds the relation from the billing warehouse to the shop database, and the card network with one resource in each of two domains; each test fails when its part is taken away.
- **SC-002**: The closing check run on the pull request is green.
