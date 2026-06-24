# Changelog

All notable changes to `aoa-langgraph-adapter` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0a0] – 2026-06-24

### Added

- **`LangGraphAdapter` for using AOA Actions as LangGraph nodes.** A fluent builder that registers AOA Actions (and plain async functions) as LangGraph nodes and compiles a standard `CompiledGraph`. `.node()` accepts an Action instance or any `async` function (`name=` required for functions). `.edge()`, `.conditional_edge()`, `.route()`, and `.start()` accept an Action class, instance, or string. An unregistered node reference raises `UnregisteredNodeError` immediately — topology errors surface at build time. A missing `@connection` key is caught at `.compile()` via `MissingConnectionError`. The connection pool is filtered per node by declared `@connection` keys automatically. `Params` fields are extracted from `agentstate` by name (strict). The result is merged back via `result.model_dump()`. `.build_graph()` returns an uncompiled `StateGraph` for native LangGraph continuation. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`params_mapper` and `response_mapper` on `LangGraphAdapter.node()`.** Two optional keyword arguments cover the case where `agentstate` field names differ from `Action.Params` / `Action.Result` field names. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`StateFieldMismatchError` raised at `.compile()` when Action Result fields are absent from AgentState.** ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`RouteKeyError` raised when `.route()` returns a key absent from paths.** ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`AgentState(BaseSchema)` — base class for LangGraph agentstate schemas.** Sets `frozen=False, extra="ignore"`; Pydantic field defaults eliminate placeholder values in `ainvoke()`. `LangGraphAdapter` is now `Generic[S]` where `S: AgentState`. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
