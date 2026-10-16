# Changelog

All notable changes to `aoa-demo` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

The demo gained a database-backed domain, and it still runs without a database. `POST
/api/v1/identity/lookup` and the MCP tool `identity.lookup` read a person and record a login
inside one transaction, each call taking its own connection from a pool the service creates at
startup. Two calls that arrive together therefore never meet on one session, and each one's
transaction belongs to it alone.

Nothing about the service changes when there is no database to talk to: with no connection
description the same route answers from an in-memory store, so the demo installs, imports and
runs without the driver. The database driver is an extra, and it is imported only when a
connection description is given. ([#215](https://github.com/bystrovmaxim/aoa/issues/215))

### Added

- **An identity domain in `aoa.demo.model.identity` — the reference for a resource created per call.** `IdentityStore` mixes the domain's two operations with the PostgreSQL resource, `IdentityStoreStub` keeps the same two in memory, and `IdentityLookupAction` declares the connection and never learns which of them it received. ([#215](https://github.com/bystrovmaxim/aoa/issues/215))
- **A pool at startup and the per-call route that uses it.** `AOA_DEMO_POSTGRES_DSN` names the database; when it is set the services create one pool in their lifespan and the route declares a resource per call over it. When it is not set, the route declares the in-memory store. Both services publish the same action over their own transport. ([#215](https://github.com/bystrovmaxim/aoa/issues/215))
- **`CancelOrderAction` in `fastapi_mcp_services.orders_domain` — the full access-control cascade in one action.** Demonstrates `grant(CustomerRole)` (role), `guard=` (a `"LOCKED-"`-prefixed order can't be cancelled by anyone), and `access_decide` (a customer may only cancel their own order) together, exercised via both `machine.run` and `machine.check_access_decide`. ([#65](https://github.com/bystrovmaxim/aoa/issues/65))

## [1.0.0] – 2026-06-27

### Changed

- **Package renamed `aoa-examples` → `aoa-demo`; import namespace `aoa.examples` → `aoa.demo`.** The distribution of reference/demo domain models (`model/billing`, `model/inventory`, `model/store`, …) and the FastAPI + MCP showcase services is now `aoa-demo`. Install `aoa-demo` and update imports (`from aoa.examples.model… ` → `from aoa.demo.model…`). The rename removes the naming collision with the root `examples/` tutorial scripts and makes clear the package is a library of runnable demo domains, not tutorial snippets. The undeclared `aoa-maxitor` → demo coupling was also removed: three demo-dependent `aoa-maxitor` tests were dropped so the `maxitor` package no longer references `demo` in any form. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))
- **Test suite relocated into the package (`packages/aoa-examples/tests/`).** Example model tests moved out of the shared root `tests/examples/` — plus the clean `depends`-modes use-case test from the legacy `aoa_examples_tests/` directory — into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]` (`testpaths`, `asyncio_mode`, `pythonpath`). The OCEL/pm4py coverage was moved out of this package entirely — converted into the runnable example `packages/aoa-ocel/examples/01_ocel_export.py` and covered by tests under `packages/aoa-ocel/tests/`. The root `tests/examples/` zone is now empty; the legacy `aoa_examples_tests/` directory is removed. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

### Removed

- **Store-domain OCEL export sub-feature.** The `PublishOrder*OcelAction` / `RecordOrderOcelAction` trace actions, the `build_store_ocel_machine` / `run_store_ocel_trace_batch` helpers, and `StoreOcelStoreResource` were removed from `aoa.examples.model.store`. The OCEL 2.0 export flow is now demonstrated by the self-contained runnable example `packages/aoa-ocel/examples/01_ocel_export.py` in the `aoa-ocel` package. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [0.1.0] – 2026-06-24

### Added

- **Initial standalone release.** Runnable tutorial and how-to examples distributed as a separate package (`pip install aoa-examples`). Each example ships as both a plain `.py` and a Colab-ready `.ipynb` with `!pip install` cell and top-level `await`. Covers the full tutorial set (steps 00–26) plus how-to, extension, and research examples.
