# Changelog

All notable changes to `aoa-examples` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Test suite relocated into the package (`packages/aoa-examples/tests/`).** Example model tests moved out of the shared root `tests/examples/` — plus the clean `depends`-modes use-case test from the legacy `aoa_examples_tests/` directory — into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]` (`testpaths`, `asyncio_mode`, `pythonpath`). The two OCEL/pm4py tests that import the shared `tests/ocel/pm4py_validation` helper stay in the root `tests/examples/` zone (they need the repo-root test tree on `sys.path`, which a self-contained package `tests/` shadows) until the shared test-support helpers are extracted; the legacy `aoa_examples_tests/` directory is removed. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **Initial standalone release.** Runnable tutorial and how-to examples distributed as a separate package (`pip install aoa-examples`). Each example ships as both a plain `.py` and a Colab-ready `.ipynb` with `!pip install` cell and top-level `await`. Covers the full tutorial set (steps 00–26) plus how-to, extension, and research examples.
