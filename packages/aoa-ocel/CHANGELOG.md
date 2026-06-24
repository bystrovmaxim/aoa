# Changelog

All notable changes to `aoa-ocel` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Test suite relocated into the package (`packages/aoa-ocel/tests/`).** OCEL tests (including the `contracts/`, `plugin/`, `resource/` subtrees) moved out of the shared root `tests/ocel/` into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group (adding `pm4py`) and `[tool.pytest.ini_options]`. The cross-package dependency on `tests/action_machine/scenarios` (`SampleEntity` / `TestDomain`) was replaced by a minimal, self-contained `tests/support/` stub, and the `pm4py_validation` helper now lives in `tests/support/`. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release, extracted from `aoa-action-machine`.** `OcelPlugin`, `OcelFrame`, `InMemoryOcelStoreResource`, `OcelStoreResource`, `OCEL_FRAMES_KEY`, and supporting DTOs are now distributed under the `aoa.ocel` namespace as a separate package (`pip install aoa-ocel`). The package depends on `aoa-action-machine` and `xxhash`. ([#71](https://github.com/bystrovmaxim/aoa/issues/71))

For the pre-extraction history of `OcelPlugin` (originally introduced in the monorepo at `[0.12.8]`), see the [aoa-action-machine CHANGELOG](../aoa-action-machine/CHANGELOG.md).
