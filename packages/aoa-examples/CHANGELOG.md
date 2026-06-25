# Changelog

All notable changes to `aoa-examples` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Test suite relocated into the package (`packages/aoa-examples/tests/`).** Example model tests moved out of the shared root `tests/examples/` — plus the clean `depends`-modes use-case test from the legacy `aoa_examples_tests/` directory — into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]` (`testpaths`, `asyncio_mode`, `pythonpath`). The OCEL/pm4py coverage was moved out of this package entirely — converted into the runnable example `packages/aoa-ocel/examples/01_ocel_export.py` and covered by tests under `packages/aoa-ocel/tests/`. The root `tests/examples/` zone is now empty; the legacy `aoa_examples_tests/` directory is removed. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

### Removed

- **Store-domain OCEL export sub-feature.** The `PublishOrder*OcelAction` / `RecordOrderOcelAction` trace actions, the `build_store_ocel_machine` / `run_store_ocel_trace_batch` helpers, and `StoreOcelStoreResource` were removed from `aoa.examples.model.store`. The OCEL 2.0 export flow is now demonstrated by the self-contained runnable example `packages/aoa-ocel/examples/01_ocel_export.py` in the `aoa-ocel` package. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release.** Runnable tutorial and how-to examples distributed as a separate package (`pip install aoa-examples`). Each example ships as both a plain `.py` and a Colab-ready `.ipynb` with `!pip install` cell and top-level `await`. Covers the full tutorial set (steps 00–26) plus how-to, extension, and research examples.
