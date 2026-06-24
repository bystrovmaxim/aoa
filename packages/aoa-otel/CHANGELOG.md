# Changelog

All notable changes to `aoa-otel` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0a0] – 2026-06-24

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `OpenTelemetryPlugin` is now distributed under the `aoa.otel` namespace as a separate package (`pip install aoa-otel`). The package depends on `aoa-action-machine`, `opentelemetry-api`, and `opentelemetry-sdk`. ([#70](https://github.com/bystrovmaxim/aoa/issues/70))

For the pre-extraction history of `OpenTelemetryPlugin` (originally introduced in the monorepo at `[1.0.0a2]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
