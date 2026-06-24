# Changelog

All notable changes to `aoa-fastapi-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0a0] – 2026-05-07

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `FastApiAdapter`, `FastApiRouteRecord`, and `query_field_before` helpers are now distributed under the `aoa.fastapi` namespace as a separate package (`pip install aoa-fastapi-adapter`). The package depends on `aoa-action-machine`, `fastapi`, and `uvicorn[standard]`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63))

For the pre-extraction history of `FastApiAdapter` (originally introduced in the monorepo at `[0.5.5]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
