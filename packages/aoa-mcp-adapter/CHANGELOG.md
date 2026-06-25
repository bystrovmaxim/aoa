# Changelog

All notable changes to `aoa-mcp-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Test suite relocated into the package (`packages/aoa-mcp-adapter/tests/`).** MCP adapter tests moved out of the shared root `tests/action_machine/adapters/mcp/` into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]`. The cross-package dependencies on `tests/action_machine/scenarios` and the shared adapter-fixture modules were replaced by a self-contained `tests/support/` package (`domain_model` + `adapter_fixtures` + facade) — faithful trimmed copies. The graph-node FQN assertions in `test_mcp_handler.py` were updated to the new module path (`tests.support.domain_model.*`) since the sample action moved modules. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `McpAdapter` and `McpRouteRecord` are now distributed under the `aoa.mcp` namespace as a separate package (`pip install aoa-mcp-adapter`). The package depends on `aoa-action-machine` and `mcp`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63))

For the pre-extraction history of `McpAdapter` (originally introduced in the monorepo at `[0.5.5]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
