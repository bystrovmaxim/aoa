# Changelog

All notable changes to `aoa-otel` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Test suite relocated into the package (`packages/aoa-otel/tests/`).** OpenTelemetry tests moved out of the shared root `tests/otel/` into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]`. The cross-package dependency on `tests/action_machine/scenarios` (a `PingAction` / `TestDomain` sample domain) was replaced by a minimal, self-contained `tests/support/` stub — a faithful trimmed copy — so the package no longer reaches into another package's test tree. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `OpenTelemetryPlugin` is now distributed under the `aoa.otel` namespace as a separate package (`pip install aoa-otel`). The package depends on `aoa-action-machine`, `opentelemetry-api`, and `opentelemetry-sdk`. ([#70](https://github.com/bystrovmaxim/aoa/issues/70))

For the pre-extraction history of `OpenTelemetryPlugin` (originally introduced in the monorepo at `[1.0.0a2]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
