# Changelog

All notable changes to `aoa-mcp-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] – 2026-07-11

### Changed

- **`auth_coordinator` is now typed `AuthCoordinatorProtocol` instead of `Any`.** Applies to `McpAdapter.__init__` and the `auth_coordinator=` parameter on `.tool(...)`. Purely additive typing — structural (`Protocol`), so every coordinator that already works continues to work unchanged; mypy/IDEs now catch a mismatched custom coordinator instead of only failing at runtime. ([#108](https://github.com/bystrovmaxim/aoa/issues/108) · [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md))

## [1.1.0] – 2026-07-10

### Added

- **`auth_coordinator=` on `.tool(...)` — per-tool authentication override.** Overrides the adapter's default coordinator for one tool only; falls back to the adapter default when omitted, via the new `BaseAdapter.effective_auth_coordinator`. Same mechanism as the FastAPI adapter's per-route override. ([#66](https://github.com/bystrovmaxim/aoa/issues/66) · [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md))

### Changed

- **Test suite relocated into the package (`packages/aoa-mcp-adapter/tests/`).** MCP adapter tests moved out of the shared root `tests/action_machine/adapters/mcp/` into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]`. The cross-package dependencies on `tests/action_machine/scenarios` and the shared adapter-fixture modules were replaced by a self-contained `tests/support/` package (`domain_model` + `adapter_fixtures` + facade) — faithful trimmed copies. The graph-node FQN assertions in `test_mcp_handler.py` were updated to the new module path (`tests.support.domain_model.*`) since the sample action moved modules. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `McpAdapter` and `McpRouteRecord` are now distributed under the `aoa.mcp` namespace as a separate package (`pip install aoa-mcp-adapter`). The package depends on `aoa-action-machine` and `mcp`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63))

For the pre-extraction history of `McpAdapter` (originally introduced in the monorepo at `[0.5.5]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
