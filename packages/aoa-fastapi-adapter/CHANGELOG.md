# Changelog

All notable changes to `aoa-fastapi-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`POST /permissions/resolve` — minimal permissions resolver (role-gate only).** New bespoke route registered directly in `FastApiAdapter.build()` (like `_register_health_check`, but always authenticated): takes a list of `{operation, params}` questions and returns a same-order list of `Verdict`s, backed by the existing `machine.check_access_decide`. List-shaped wire protocol (`items`/`verdicts`) from day one — a single question is a batch of one, not a separate code path. `auth_coordinator.process(request)` is always called; a `403` follows only when it returns `None` — a resolved anonymous `Context` (e.g. `NoAuthCoordinator`) flows through normally, so `@check_roles(GuestRole)` actions resolve correctly for unauthenticated callers instead of being special-cased in the resolver. `scope`/`entities`/`reason_code`/`expires_at` are reserved in the wire schema but deliberately unpopulated in this release — see the upcoming object-level verdict and rate-limiting work. `CheckAccessDecideBatchSizeExceededError` now maps to HTTP `413`. New modules: `aoa.fastapi.permissions_schema` (wire models), `aoa.fastapi.permissions` (`operation` name resolution, `AccessVerdict` -> wire projection). No changes to `aoa-action-machine`. ([#134](https://github.com/bystrovmaxim/aoa/issues/134) · part of [#130](https://github.com/bystrovmaxim/aoa/issues/130))
- **Reserved-route-path guard on `FastApiAdapter`.** `_RESERVED_PATHS` (`/health`, `/permissions/resolve`) is checked on every `.post/.get/.put/.delete/.patch(...)` call; registering an action on a reserved path now raises `ReservedRoutePathError` immediately instead of being silently shadowed by the adapter's own bespoke route at `build()` time. ([#134](https://github.com/bystrovmaxim/aoa/issues/134))
- **`POST /permissions/resolve` deduplicates identical items and isolates per-item errors.** New `resolve_verdicts()` (`aoa.fastapi.permissions`) groups a batch's items by `(operation, canonical_key(params))`; only the first occurrence of a key triggers a real `machine.check_access_decide` call — run concurrently across distinct keys via `asyncio.gather`, not a sequential loop — and every later occurrence copies that same verdict, so `verdicts` never shrinks. An unknown `operation` now isolates to its own item (`reason_code: "UNKNOWN_ACTION"`, `200 OK`) instead of failing the whole batch with `400`. `ResolveOutcome.real_call_count` reports the deduplicated call count for tests, deliberately not part of the wire protocol. `ActionProductMachine.max_check_access_decide_batch_size` (`aoa-action-machine`) is now a public read-only property, since the resolver's concurrent per-key calls bypass the list form's own built-in size check and must enforce the same cap themselves, against the batch size after deduplication. ([#135](https://github.com/bystrovmaxim/aoa/issues/135) · part of [#130](https://github.com/bystrovmaxim/aoa/issues/130))

## [1.1.1] – 2026-07-11

### Changed

- **`auth_coordinator` is now typed `AuthCoordinatorProtocol` instead of `Any`.** Applies to `FastApiAdapter.__init__` and the `auth_coordinator=` parameter on `.post/.get/.put/.delete/.patch(...)`. Purely additive typing — structural (`Protocol`), so every coordinator that already works continues to work unchanged; mypy/IDEs now catch a mismatched custom coordinator instead of only failing at runtime. ([#108](https://github.com/bystrovmaxim/aoa/issues/108) · [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md))

## [1.1.0] – 2026-07-10

### Added

- **`auth_coordinator=` on `.post/.get/.put/.delete/.patch(...)` — per-route authentication override.** Overrides the adapter's default coordinator for one route only; falls back to the adapter default when omitted, via the new `BaseAdapter.effective_auth_coordinator`. Lets a route like `/auth/login` opt out of a strict adapter-wide coordinator without weakening it for every other route. ([#66](https://github.com/bystrovmaxim/aoa/issues/66) · [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md))

### Changed

- **Test suite relocated into the package (`packages/aoa-fastapi-adapter/tests/`).** FastAPI adapter tests moved out of the shared root `tests/action_machine/adapters/fastapi/` into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group (adding `httpx` for the FastAPI `TestClient`) and `[tool.pytest.ini_options]`. The cross-package dependencies on `tests/action_machine/scenarios` and the shared adapter-fixture modules were replaced by a self-contained `tests/support/` package (`domain_model`, `connections`, `adapter_fixtures` + facade) — faithful trimmed copies — so the package no longer reaches into another package's test tree. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `FastApiAdapter`, `FastApiRouteRecord`, and `query_field_before` helpers are now distributed under the `aoa.fastapi` namespace as a separate package (`pip install aoa-fastapi-adapter`). The package depends on `aoa-action-machine`, `fastapi`, and `uvicorn[standard]`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63))

For the pre-extraction history of `FastApiAdapter` (originally introduced in the monorepo at `[0.5.5]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
