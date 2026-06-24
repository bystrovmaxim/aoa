# Changelog

All notable changes to `aoa-ocel` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0a0] – 2026-05-22

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `OcelPlugin`, `OcelFrame`, `InMemoryOcelStoreResource`, `OcelStoreResource`, `OCEL_FRAMES_KEY`, and supporting DTOs are now distributed under the `aoa.ocel` namespace as a separate package (`pip install aoa-ocel`). The package depends on `aoa-action-machine` and `xxhash`. ([#71](https://github.com/bystrovmaxim/aoa/issues/71))

For the pre-extraction history of `OcelPlugin` (originally introduced in the monorepo at `[0.12.8]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
