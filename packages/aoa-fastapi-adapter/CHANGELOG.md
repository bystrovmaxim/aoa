# Changelog

All notable changes to `aoa-fastapi-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] – 2026-10-26

### Changed

- **License and NOTICE travel inside every artifact**, and the tests follow the current entity model. ([#200](https://github.com/bystrovmaxim/aoa/issues/200))


## [1.2.0] – 2026-10-18

### Added

- **A route now runs its connections through the per-call lifecycle.** Every route the adapter builds wraps its `machine.run` in `connection_scope`: a resource declared as `PerCallConnection` is created, opened before the action runs, and finalized exactly once on the way out — on success, on a raised error and on cancellation — instead of being created and handed over unopened. A resource the application created itself is passed through untouched, so a lifespan-owned service or a ready resource behaves exactly as before. A closing failure never replaces the run's own error, it is reported beside it, and a cancellation stays a cancellation. ([#215](https://github.com/bystrovmaxim/aoa/issues/215))

### Changed

- **The package now requires `aoa-action-machine>=1.0.1a4`.** That is the first release carrying `connection_scope`; an older one would leave the adapter unable to import. ([#215](https://github.com/bystrovmaxim/aoa/issues/215))

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
