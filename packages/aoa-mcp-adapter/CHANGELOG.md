# Changelog

All notable changes to `aoa-mcp-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0a0] – 2026-05-07

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `McpAdapter` and `McpRouteRecord` are now distributed under the `aoa.mcp` namespace as a separate package (`pip install aoa-mcp-adapter`). The package depends on `aoa-action-machine` and `mcp`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63))

For the pre-extraction history of `McpAdapter` (originally introduced in the monorepo at `[0.5.5]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
