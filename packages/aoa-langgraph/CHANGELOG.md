# Changelog

All notable changes to `aoa-langgraph` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking changes

- **`LangGraphAdapter` replaced by `LangGraphController`; old import path removed.** `LangGraphAdapter` (with `.node(instance)`, `.conditional_edge()`, `.compile()`) no longer exists. Migrate: replace `LangGraphAdapter(machine=..., context=..., agentstate=...)` with `LangGraphController()`; declare fields via `.inp()/.mid()/.out()`; pass Action **classes** (not instances) to `.node()`; replace `.compile()` with `.build()`, then `await ctrl.ainvoke(data, box)` instead of `await compiled.ainvoke(state)`. `StateFieldMismatchError`, `UnregisteredNodeError`, `MissingConnectionError` from the old adapter are removed. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

### Added

- **`LangGraphController` — standalone fluent graph builder replacing `LangGraphAdapter`.** State schema declared in three tiers: `.inp(name, type, desc)` (input, required), `.mid(name, type, desc)` (intermediate, `UNSET` by default), `.out(name)` (output); `AgentState` is auto-generated — no manual subclass needed. `.node(ActionClass)` registers Action **classes** (not instances); `.node(fn, name="name")` registers plain `async` functions. `.start()` / `.edge()` / `.route()` / `.finish()` define topology. `.build()` validates topology and data-contract statically before the first run. `ctrl.ainvoke(data, box)` compiles a fresh LangGraph per call and returns a `dict` of out-fields. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

- **Topology and data-contract validator (`topology_validator.py`).** Validates the graph at `.build()` time. Errors raised: `NoStartNodeError` (no `.start()` call), `DeadEndNodeError` (leaf node not marked `.finish()`), `UnreachableNodeError` (node unreachable from start), `FinishUnreachableError` (`.finish()` nodes cannot be reached from start), `InconsistentFinishOutputError` (finish nodes disagree on which out-fields are populated), `FieldHasNoProducerError` (required Params-field is neither an inp-field nor written by any predecessor), `OutputHasNoProducerError` (out-field has no producer node), `UnexpectedResultFieldError` (Action Result-field not declared in inp/mid schema). Nodes with `params_mapper` or `response_mapper` are excluded from data-contract checks. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

- **`MissingInputFieldError`.** Raised in `ainvoke()` when a required inp-field is absent from the data dict. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

- **`UNSET` sentinel and `UnsetType`.** Default value for mid-fields in the auto-generated `AgentState`; distinguishes "not yet written" from `None`. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

- **`WrapperLangGraphController`.** Thin wrapper that exposes a built `LangGraphController` as a `BaseController`-compatible resource for `@connection`. Pass the built controller as `connections={"graph": ctrl}` to `machine.run()`. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

- **6 runnable step-14 examples** (`examples/step_14_langgraph/01`–`06`, each as `.py` + `.ipynb`): `01_external_connection` (controller as `@connection`), `02_inline_graph` (controller built inline in the host Action), `03_function_node` (plain `async` function as a graph node), `04_field_mapping` (`params_mapper`/`response_mapper` with mismatched field names), `05_testing` (three testing patterns: structural, stub-Action, mock-box), `06_field_mapping` (all three mapping scenarios: input rename, output rename, side-effect-only node with `response_mapper=lambda r: {}`). ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

### Fixed

- **`_validate_topology()` now correctly excludes `params_mapper` nodes from data-contract checks.** Previously only `response_mapper` was excluded; nodes with `params_mapper` were still validated against state field names, causing false `FieldHasNoProducerError` when state field names differ from `Action.Params` field names. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

### Removed

- **`LangGraphAdapter`, `adapter.py`, `node_wrapper.py` deleted.** The old fluent builder and its node-wrapping internals are fully removed. ([#83](https://github.com/bystrovmaxim/aoa/issues/83))

### Changed

- **Test suite relocated into the package (`packages/aoa-langgraph/tests/`).** Adapter tests moved out of the shared root `tests/langgraph/` into the package's own `tests/` directory, with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]` (including the langgraph deprecation `filterwarnings`). The cross-package dependency on `tests/action_machine/scenarios` (`PingAction` / `FullAction` / `OrdersDbManager`) was replaced by a minimal, self-contained `tests/support/` stub — a faithful trimmed copy — so the package no longer reaches into another package's test tree. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

## [1.0.0] – 2026-06-24

### Added

- **`LangGraphAdapter` for using AOA Actions as LangGraph nodes.** A fluent builder that registers AOA Actions (and plain async functions) as LangGraph nodes and compiles a standard `CompiledGraph`. `.node()` accepts an Action instance or any `async` function (`name=` required for functions). `.edge()`, `.conditional_edge()`, `.route()`, and `.start()` accept an Action class, instance, or string. An unregistered node reference raises `UnregisteredNodeError` immediately — topology errors surface at build time. A missing `@connection` key is caught at `.compile()` via `MissingConnectionError`. The connection pool is filtered per node by declared `@connection` keys automatically. `Params` fields are extracted from `agentstate` by name (strict). The result is merged back via `result.model_dump()`. `.build_graph()` returns an uncompiled `StateGraph` for native LangGraph continuation. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`params_mapper` and `response_mapper` on `LangGraphAdapter.node()`.** Two optional keyword arguments cover the case where `agentstate` field names differ from `Action.Params` / `Action.Result` field names. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`StateFieldMismatchError` raised at `.compile()` when Action Result fields are absent from AgentState.** ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`RouteKeyError` raised when `.route()` returns a key absent from paths.** ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`AgentState(BaseSchema)` — base class for LangGraph agentstate schemas.** Sets `frozen=False, extra="ignore"`; Pydantic field defaults eliminate placeholder values in `ainvoke()`. `LangGraphAdapter` is now `Generic[S]` where `S: AgentState`. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
