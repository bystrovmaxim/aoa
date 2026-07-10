# Changelog

All notable changes to `aoa-fastapi-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] – 2026-07-10

### Added

- **`auth_coordinator=` on `.post/.get/.put/.delete/.patch(...)` — per-route authentication override.** Overrides the adapter's default coordinator for one route only; falls back to the adapter default when omitted, via the new `BaseAdapter.effective_auth_coordinator`. Lets a route like `/auth/login` opt out of a strict adapter-wide coordinator without weakening it for every other route. ([#66](https://github.com/bystrovmaxim/aoa/issues/66) · [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md))

### Changed

- **Test suite relocated into the package (`packages/aoa-fastapi-adapter/tests/`).** FastAPI adapter tests moved out of the shared root `tests/action_machine/adapters/fastapi/` into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group (adding `httpx` for the FastAPI `TestClient`) and `[tool.pytest.ini_options]`. The cross-package dependencies on `tests/action_machine/scenarios` and the shared adapter-fixture modules were replaced by a self-contained `tests/support/` package (`domain_model`, `connections`, `adapter_fixtures` + facade) — faithful trimmed copies — so the package no longer reaches into another package's test tree. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `FastApiAdapter`, `FastApiRouteRecord`, and `query_field_before` helpers are now distributed under the `aoa.fastapi` namespace as a separate package (`pip install aoa-fastapi-adapter`). The package depends on `aoa-action-machine`, `fastapi`, and `uvicorn[standard]`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63))

For the pre-extraction history of `FastApiAdapter` (originally introduced in the monorepo at `[0.5.5]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
