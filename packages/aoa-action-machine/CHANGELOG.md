# Changelog

All notable changes to `aoa-action-machine` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Conventions.** Release headings use `## [version] – YYYY-MM-DD` (en dash). Use `### Breaking changes`, `### Added`, `### Changed`, `### Fixed`, `### Removed`, and `### Documentation` as needed. Each bullet starts with a **bold title** followed by a period and the body.

## [Unreleased]

### Added

- **`CookieCredentialExtractor` — pull a JWT out of a named HTTP cookie.** New `CredentialExtractor` under `aoa.action_machine.auth.jwt_auth`, alongside `BearerCredentialExtractor`. Unblocks same-site SSO across subdomains: a central login service sets a domain-wide, `httpOnly` session cookie that browsers attach automatically to every subdomain request, but that `httpOnly`-ness makes the token invisible to JavaScript, so it can never reach an `Authorization` header. `CookieCredentialExtractor(cookie_name=...)` reads it straight from `request_data.cookies` instead — `cookie_name` is required, with no default, since it's part of the cross-service contract between the issuer and every verifier. Missing, empty, or whitespace-only cookie → `{}` (no credentials); `request_data` with no `.cookies` at all → `TypeError` (a wiring error — the same contract `BearerCredentialExtractor` uses for `.headers`). Duck-types a plain `dict[str, str]`, no Starlette import. Purely additive; pairs with the follow-up issue that parameterizes the extractor on `JwtAuthCoordinator`. ([#118](https://github.com/bystrovmaxim/aoa/issues/118))
- **`JwtAuthCoordinator(credential_extractor=...)` — pluggable credential transport.** New keyword, symmetric with the existing `context_assembler=`: `None` (the default) preserves today's behavior byte-for-byte (`BearerCredentialExtractor()`), any other `CredentialExtractor` — e.g. `CookieCredentialExtractor` — replaces it. Previously, any transport other than the `Authorization` header forced abandoning the wrapper entirely and re-plumbing `JwtAuthenticator` by hand via `AuthCoordinator`; now it's one keyword. Non-breaking — no existing call site needs to change. ([#119](https://github.com/bystrovmaxim/aoa/issues/119))

## [1.0.1a1] – 2026-07-10

### Added

- **`BaseRouteRecord.auth_coordinator` — optional per-route authentication override.** Adapters resolve the coordinator for a request via the new `BaseAdapter.effective_auth_coordinator(record)`: returns `record.auth_coordinator` when set, else the adapter's default. Lets one route (e.g. a login endpoint) opt out of a strict default coordinator without weakening it for every other route. Concrete adapters (`aoa-fastapi-adapter`, `aoa-mcp-adapter`) expose this as an `auth_coordinator=` keyword on their route-registration methods. ([#66](https://github.com/bystrovmaxim/aoa/issues/66))
- **`aoa-action-machine[jwt]` — ready-made Bearer/JWT `AuthCoordinator`.** New optional extra (`pip install "aoa-action-machine[jwt]"`, adds `PyJWT`) under `aoa.action_machine.auth.jwt_auth`: `BearerCredentialExtractor` (parses `Authorization: Bearer <jwt>`; raises `TypeError` with an actionable message when `request_data` has no `.headers` at all — a wiring error, not "no credentials"; this is exactly what happens if wired into `aoa-mcp-adapter`, which always calls `process(None)` — see [#113](https://github.com/bystrovmaxim/aoa/issues/113)), `JwtAuthenticator` (verifies signature/expiry/audience via PyJWT; `exp` is mandatory — a token without it is rejected; unknown role-claim strings are dropped, not rejected), `HttpContextAssembler` (default `RequestInfo` projection for HTTP requests), and `JwtAuthCoordinator` — a thin `AuthCoordinator` subclass wiring the three together (`JwtAuthCoordinator(secret_key=..., role_registry={"admin": AdminRole})`). Works with `aoa-fastapi-adapter`; does **not** work with `aoa-mcp-adapter` (tracked in #113). Issuing tokens (login) is out of scope — an application's own `LoginAction` signs tokens with PyJWT directly; this coordinator only verifies them on every subsequent request. Never imported from the core `aoa.action_machine.auth` namespace, so installing without the extra never pulls in PyJWT. Documented in `docs/extensions/jwt_draft.md`. ([#66](https://github.com/bystrovmaxim/aoa/issues/66))

## [1.0.1a0] – 2026-07-09

### Breaking changes

- **`NoAuthCoordinator` now requires an explicit `context` argument.** `NoAuthCoordinator()` is no longer valid; pass the `Context` explicitly: `NoAuthCoordinator(context=Context())`. The change makes the context visible at the call site instead of hiding an implicit anonymous default. Semantically `process()` now returns the **same** `Context` instance on every call (was: a new instance each time). Any code that relied on identity (`ctx1 is not ctx2`) must be updated. The class is otherwise compatible — it still satisfies the `AuthCoordinator` protocol and can be swapped with a real coordinator without touching the `Action`. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`AuthCoordinator` now raises `AuthorizationError` when `process()` returns `None`.** Previously `FastApiAdapter` and `McpAdapter` silently fell back to a plain anonymous `Context()` when the coordinator returned `None` (unauthenticated request). This masked auth failures: operations decorated with `@check_roles(GuestRole)` would succeed for any unrecognised credential. Now `None` from `process()` immediately raises `AuthorizationError("Authentication required")`, which the adapters convert to HTTP 403 / MCP `PERMISSION_DENIED` envelope. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`FastApiAdapter` and `McpAdapter` extracted into separate packages; old import paths removed.** `aoa.action_machine.adapters.fastapi` and `aoa.action_machine.adapters.mcp` no longer exist. The `[fastapi]` and `[mcp]` extras on `aoa-action-machine` are also removed. Install the new dedicated packages and update all imports: `pip install aoa-fastapi-adapter` → `from aoa.fastapi import FastApiAdapter`; `pip install aoa-mcp-adapter` → `from aoa.mcp import McpAdapter`. ([#63](https://github.com/bystrovmaxim/aoa/issues/63))
- **OCEL plugin extracted into a separate package; old import paths removed.** `aoa.action_machine.plugin.ocel` no longer exists. The `[ocel]` extra on `aoa-action-machine` is removed. Install the new package and update all imports: `pip install aoa-ocel` → `from aoa.ocel import OcelPlugin, OcelFrame, InMemoryOcelStoreResource, OCEL_FRAMES_KEY`. ([#71](https://github.com/bystrovmaxim/aoa/issues/71))
- **OpenTelemetry plugin extracted into a separate package; old import paths removed.** `aoa.action_machine.plugin.open_telemetry` no longer exists. The `[otel]` extra on `aoa-action-machine` is removed. Install the new package and update all imports: `pip install aoa-otel` → `from aoa.otel import OpenTelemetryPlugin`. ([#70](https://github.com/bystrovmaxim/aoa/issues/70))
- **`@compensate` now accepts a callable reference instead of a string.** `@compensate("aspect_name", description)` is no longer valid; pass the method object directly: `@compensate(aspect_name, description)`. The target aspect must be defined before the compensator in the class body — the reference is resolved at class definition time, enabling IDE rename support and eliminating stringly-typed coupling. Internally, `_compensate_meta["target_aspect"]` now stores the callable (was: `"target_aspect_name"` string); `CompensatorGraphNode.target_aspect` carries the callable directly; `ActionGraphNode.compensator_graph_node_for_aspect` accepts a callable and matches by identity (`is`). ([#64](https://github.com/bystrovmaxim/aoa/issues/64))

### Added

- **`@env` decorator for declarative environment providers on `Context`.** `@env(key, value_or_callable, ttl=0)` registers a lazy provider on a `Context` subclass. Constants are auto-wrapped; any `Callable[[], T]` is accepted as-is. `ttl=0` caches the value forever; `ttl>0` re-calls the provider after N seconds; `ttl<0` raises `ValueError` at declaration. Subclasses inherit all parent entries and can override individual keys without touching the parent dict. Aspects declare needed keys via `@context_requires("env.<key>")` and read them through `ctx.get(...)` — the same path as `user.*`, `request.*`, and `runtime.*` fields. An undeclared key raises `ContextAccessError`; a key registered in `@env` but absent from `@context_requires` is simply inaccessible, not missing. ([#60](https://github.com/bystrovmaxim/aoa/issues/60))
- **`TestBench.with_env(key, value, ttl=0)` for env constants in tests.** Registers a constant (not a callable) as the env value for `key` on the bench-built context. Successive calls merge by key; the last call for the same key wins. `TestBench` is immutable — each `.with_env(...)` returns a new object. Under the hood a dynamic `Context` subclass is created with `__env_entries__` set so the action receives the same interface it would with a production `AppContext`. ([#60](https://github.com/bystrovmaxim/aoa/issues/60))
- **`context_class` parameter on `AuthCoordinator` for custom `Context` subclasses with `@env`.** `AuthCoordinator(..., context_class=AppContext)` makes `process()` instantiate your `Context` subclass instead of the base `Context`. This is the only way to get `@env`-decorated entries into the context when using real authentication (not `NoAuthCoordinator`): `@env` entries live on the class, not on the instance, so passing `context_class=AppContext` is sufficient — `AppContext(user=..., request=...)` works without any constructor changes. ([#62](https://github.com/bystrovmaxim/aoa/issues/62))
- **`CacheCoordinator` created by default in `ActionProductMachine`.** Constructing `ActionProductMachine()` without a `cache_coordinator` argument now creates an in-memory `CacheCoordinator` automatically — caching is available out of the box without any explicit configuration. Pass `cache_coordinator=None` to opt out of caching entirely; pass an explicit `CacheCoordinator` instance to use a custom one. ([#56](https://github.com/bystrovmaxim/aoa/issues/56))
- **Tag-based cache invalidation.** `on_cache_write(result, params, duration_ms)` now returns `list[CacheTag] | None` instead of `bool` — `None` skips the write, a non-empty list writes the entry and indexes it under those tags. A new hook `on_cache_invalidate(params, result)` returns `list[CacheTag] | None`; called after every successful pipeline run regardless of `cache_key`, it evicts all cached entries whose stored tags match any of the returned matchers (wildcard-aware: a `None` field in a `CacheTag` matches any value — e.g. `CacheTag(type=Order)` evicts all orders). Invalidation happens before the write. `CacheCoordinator` gains a tag index (`_tag_to_keys`, `_key_to_tags`) and `evict_by_tags(directive_tags: frozenset[CacheTag])`. `CacheTag` is a frozen dataclass with `type: type[Any] | None` and `key: str | int | None`; at least one field must be non-`None`. `cache_key` remains `str | None` — tags are declared at write time when the result is available, not in `cache_key`. ([#58](https://github.com/bystrovmaxim/aoa/issues/58))
- **`BaseCoordinator` marker base class introduced.** Empty base class formalising the coordinator role in the AOA primitive language. `AuthCoordinator`, `NoAuthCoordinator`, `CacheCoordinator`, `SagaCoordinator`, `NodeGraphCoordinator`, `PluginCoordinator`, and `LogCoordinator` now inherit `BaseCoordinator`; `DebugNodeGraphCoordinator` inherits it transitively. ([#87](https://github.com/bystrovmaxim/aoa/issues/87))
- **`BaseObserver` marker base class introduced.** Root for all AOA observer primitives. Side-effects only — never modifies result, never aborts execution; removing any `BaseObserver` leaves system behaviour unchanged. `BaseLogger` and `Plugin` now inherit `BaseObserver`. ([#87](https://github.com/bystrovmaxim/aoa/issues/87))
- **`BaseIntent` marker base class introduced.** Root for all AOA intent primitives. Declarative mixin only; carries no runtime behaviour. All 13 `*Intent` marker classes (`CheckerIntent`, `ConnectionIntent`, `ContextRequiresIntent`, `EntityIntent`, `MetaIntent`, `OnErrorIntent`, `SensitiveIntent`, `CompensateIntent`, `OnIntent`, `RoleModeIntent`, `CheckRolesIntent`, `AspectIntent`, `DependsIntent`) now inherit `BaseIntent`. ([#87](https://github.com/bystrovmaxim/aoa/issues/87))
- **`BaseStorage`, `BaseGateway`, and `BaseController(BaseResource)` subtypes introduced.** Three marker classes specialise `BaseResource` by lifecycle ownership: `BaseStorage` (external data stores; `SqlResource` and `WrapperSqlResource` now inherit it), `BaseGateway` (external services the process delegates work to; no concrete classes yet), and `BaseController` (internal long-lived dependencies whose lifecycle the process owns; `ExternalServiceResource` and `WrapperExternalServiceResource` now inherit it). `BaseController` lives in `resources/` — not `runtime/`. ([#87](https://github.com/bystrovmaxim/aoa/issues/87))
- **`Lifecycle` is a standalone primitive — no base class.** `Lifecycle` carries no parent class and is not a resource, coordinator, or controller. State graph is declared declaratively; an inconsistent graph is a startup error. ([#87](https://github.com/bystrovmaxim/aoa/issues/87))

### Changed

- **Test suite relocated into the package (`packages/aoa-action-machine/tests/`).** The `action_machine` and `graph` test trees moved out of the shared root `tests/` into the package's own `tests/` directory (subtree preserved: `tests/action_machine/…`, `tests/graph/…`), with a per-package `[dependency-groups]` dev group and `[tool.pytest.ini_options]` (declaring `asyncio_mode="auto"` and the custom `benchmark`/`graph_coverage` markers). The shared sample domain model moved from `tests/action_machine/scenarios/domain_model/` to `tests/support/domain_model/`, and all 112 import sites were rewritten from `tests.action_machine.scenarios.domain_model` to `tests.support.domain_model`. As the owner of the sample domain, no cross-package test-tree imports remain. ([#82](https://github.com/bystrovmaxim/aoa/issues/82))

### Removed

- **`CacheKeyMixin` removed.** The mixin (added in [#56](https://github.com/bystrovmaxim/aoa/issues/56)) produced cache entries with no tags, making them impossible to invalidate. With the new tag-based design every action that participates in caching must implement `cache_key` explicitly and declare the tags relevant to its domain. ([#58](https://github.com/bystrovmaxim/aoa/issues/58))
- **`ConsoleLogger` added by default to `ActionProductMachine`.** Constructing `ActionProductMachine()` without any logging arguments now attaches a `ConsoleLogger` automatically. Pass `loggers=[]` for silent mode or `loggers=[MyLogger()]` to use a custom logger instead. When an explicit `log_coordinator` is passed, no default logger is added — the coordinator is used as-is.
- **`loggers` parameter on `ActionProductMachine`.** A new `loggers: list[BaseLogger] | None` keyword argument lets you supply one or more loggers without constructing a `LogCoordinator` manually. Loggers are appended via `add_logger` and compose with an explicit `log_coordinator` when both are provided.
- **`plugins` and `loggers` no longer compete with their coordinators.** Passing both `plugin_coordinator` and `plugins` (or both `log_coordinator` and `loggers`) previously silenced the content arguments. Both coordinators now expose `add_plugin` / `add_logger` and the machine calls them after coordinator resolution, so all arguments take effect regardless of combination.
- **`PluginCoordinator.add_plugin`.** New method appends a plugin to an existing coordinator instance. `plugins` constructor argument is now optional (defaults to empty list).

### Fixed

- **`F841` false positives suppressed in Jupyter notebooks.** Extended the `"**/*.ipynb"` ruff per-file-ignores to include `F841` (unused variable), which fires on cell-scoped names referenced in later cells — a pattern ruff cannot see across cell boundaries. ([#52](https://github.com/bystrovmaxim/aoa/issues/52))
- **Mypy `no-untyped-def` warnings silenced for example scripts.** The `typecheck` task now targets `src/` directories only (`mypy packages/aoa-action-machine/src packages/aoa-maxitor/src packages/aoa-examples/src`). Standalone scripts in `packages/aoa-action-machine/examples/` are demonstration code and are no longer included in the strict mypy pass. ([#52](https://github.com/bystrovmaxim/aoa/issues/52))

## [1.0.0a5] – 2026-06-20

### Breaking changes

- **`NoneRole` removed; use `GuestRole`.** `NoneRole` expressed absence ("no role"); `GuestRole` expresses intent ("guest / public access, declared explicitly"). The class `aoa.action_machine.auth.none_role.NoneRole` and the file `none_role.py` are deleted. Replace every import and every `@check_roles(NoneRole)` with `GuestRole`. `GuestRole` is exported from `aoa.action_machine.auth` and `aoa.action_machine.intents.check_roles`. ([#46](https://github.com/bystrovmaxim/aoa/issues/46))

## [1.0.0a4] – 2026-06-20

### Fixed

- **`Level.info` no longer forces white foreground in `ConsoleLogger`.** Removed the explicit `#FFFFFF` truecolor entry from `DEFAULT_LEVEL_FG_PREFIX`. The terminal (or notebook environment) now decides the foreground color for info messages, making them readable on both dark terminals and light-background environments such as Google Colab. `warning` (#FFCC00) and `critical` (#FF2222) colors are unaffected.
- **Ruff false positives in Jupyter notebooks.** Added `"**/*.ipynb" = ["F404", "E402", "F401", "RUF005"]` under `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`. Notebook cells share cross-cell scope that ruff cannot see, producing 42 spurious import errors in `examples/`. After the fix `ruff check examples/` passes clean.

## [1.0.0a3] – 2026-06-17

### Documentation

- **First complete documentation set for the whole project.** Introduced a full [Diátaxis](https://diataxis.fr/) documentation tree under `docs/`, navigated from a single hub (`docs/index.md`): a step-by-step **tutorial** (getting started through Maxitor, steps 00–26), **how-to guides** (choosing Action / aspect / resource, migrating a legacy codebase, and eight extension-authoring guides), **reference** (FAQ, glossary, formal model, intents & invariants), **explanation** (philosophy / IOP, comparison with other frameworks, system altitudes, "questions AOA answers with code"), **ready-extension cards** (ConsoleLogger, FastAPI, MCP, OCEL 2.0, OpenTelemetry, PostgreSQL), and a **research note** (what the system knows about itself).
- **Runnable examples in two forms.** Every example under `examples/` now ships both as a plain `.py` and as a Colab `.ipynb` (English, identical logic, `!pip install` cell + top-level `await`), covering the full tutorial set plus the non-tutorial how-to / extension / research examples. Tutorial chapters carry a dual-form "Try in Colab · Open in project" link line.
- **README rework.** `packages/aoa-action-machine/README.md` becomes a focused quick-start that leads into the tutorial; the root `README.md` links are repointed to the new `docs/` chapters and to current example paths.

## [1.0.0a2] – 2026-06-15

### Added

- **OpenTelemetry Traces support (`tracer_provider`).** `OpenTelemetryPlugin(tracer_provider=tp)` emits one root span per `machine.run()` and child spans per aspect, `@on_error` handler, and compensator. Saga rollback events are recorded as timed span events on the root span. Requires `aoa-otel`.
- **OpenTelemetry Logs support (`logger_provider`).** `OpenTelemetryPlugin(logger_provider=lp)` emits a structured log record for every lifecycle event. After-aspect records carry `aoa.state.<field>` attributes with per-field serialization of `aspect_result` (state x-ray). Self-sufficient without `tracer_provider`; when both providers are configured, logs carry OTel-native `trace_id`/`span_id` for automatic backend correlation.
- **`opaque=True` on checkers — exclude complex objects from state x-ray.** All `result_*` decorators (`result_string`, `result_int`, `result_float`, `result_bool`, `result_date`, `result_instance`) accept `opaque: bool = False`. Fields marked `opaque=True` are excluded from `aoa.state.*` log attributes. `CheckerGraphPayload` and `CheckerGraphNode` carry `opaque` as a named field symmetric with `required`; the machine computes `opaque_fields` from the graph at emit time and delivers it on `AfterRegularAspectEvent.opaque_fields` — no runtime introspection in the plugin.
- **`watch_actions` filter on `Plugin`.** `watch_actions=frozenset({MyAction})` limits plugin delivery to the given action classes and their subclasses (`issubclass` check). Implemented in `Plugin` base class; available to all plugins.
- **`watch_events` filter on `Plugin`.** `watch_events=frozenset({GlobalFinishEvent})` limits plugin delivery to the given event types. Implemented in `Plugin` base class; available to all plugins.

## [1.0.0a1] – 2026-06-14

### Fixed

- **`DuplicateNodeError` on Action class re-definition in interactive environments.** `BaseGraphNodeInspector._all_descendant_types` now silently drops stale class objects that `BaseAction.__subclasses__()` keeps alive after a Jupyter / Colab cell re-run. A class is filtered only when its module is present in `sys.modules`, its `__qualname__` resolves to a *different* object in that module, and no `<locals>` segment appears in the qualname (i.e. not a local class). In every other case the class is kept — making the filter a no-op in production and purely additive for notebook environments.

## [1.0.0a0] – 2026-05-22

### Breaking changes

- **Remove standalone `aoa-graph` wheel.** Interchange primitives and coordinators now ship only inside `aoa-action-machine`. The workspace builds **four** wheels (`aoa-action-machine`, `aoa-ocel`, `aoa-maxitor`, `aoa-examples`); `pip install aoa-graph` is gone. Migrate `from aoa.graph…` → `from aoa.action_machine.graph.core…` (e.g. `NodeGraphCoordinator`, `InvalidGraphError`, `exclude_graph_model`, edge relationship constants).
- **Fold `graph_model` into `aoa.action_machine.graph`.** Domain projection modules move under one tree: `graph/core/` (former `aoa.graph`), `graph/nodes/`, `graph/edges/`, `graph/inspectors/`, plus leaf modules `graph/node_graph_coordinator_factory.py` and `graph/graph_json_schema.py`. Replace `aoa.action_machine.graph_model.*` imports with the matching `aoa.action_machine.graph.*` path.
- **Rename `integrations/` to `adapters/` and relocate Postgres.** FastAPI and MCP transport code is `aoa.action_machine.adapters.fastapi` / `adapters.mcp` (was `integrations.*`). `PostgresResource` is `aoa.action_machine.resources.postgres` (was under `integrations.postgres`). Optional extras `[fastapi]`, `[mcp]`, and `[postgres]` are unchanged — only import paths move.
- **Graph package facade is core-only.** `aoa.action_machine.graph` re-exports interchange primitives from `graph.core` only. Import `create_node_graph_coordinator` from `aoa.action_machine.graph.node_graph_coordinator_factory` and `GRAPH_JSON_SCHEMA` from `aoa.action_machine.graph.graph_json_schema` — lazy `__getattr__` re-exports on the package `__init__` are removed.

### Changed

- **Monorepo layout and boundaries.** `scripts/package_boundaries.toml`, packaging smoke, publish workflow, and `task build-packages` no longer reference `packages/aoa-graph`. `action_machine` is self-contained for graph code; cross-package rules for `ocel`, `maxitor`, and `examples` are updated accordingly.
- **Root README repositioned as AOA / IOP.** Installation table lists four wheels; quick-start covers OCEL export and Maxitor; link to `docs/intents-and-invariants.md` for decorator semantics and structural invariants.

### Fixed

- **CI import-boundary checks after graph merge.** Test layer rules for `tests/action_machine/graph/` are satisfied by moving runtime-dependent generalization tests to `graph_host/` and lazy graph export smoke to `tests/action_machine/smoke/`; narrow allowlist entries cover `exclude_graph_model` in model-layer cleanup tests.
- **Maxitor samples public API.** `aoa.examples.model` may import coordinator types from `aoa.action_machine.graph.core.{debug_node_graph_coordinator,exceptions,node_graph_coordinator}` and the factory leaf module — aligned with post-merge paths.

### Removed

- **`packages/aoa-graph`.** Standalone graph wheel and `aoa.graph` namespace package deleted; all graph runtime code lives under `aoa.action_machine.graph`.
- **`aoa.action_machine.integrations`.** Directory removed after adapter/resource relocation; update any out-of-tree imports before upgrading.

## [0.12.8] – 2026-05-22

### Documentation

- **OCEL export policy (v1).** `packages/aoa-ocel/src/aoa/ocel/README.md` documents E2O-only export, loaded-relation reachability, one-hop peer materialization, and aspect-controlled participation via partial entity loading.

### Breaking changes

- **`@depends` on concrete actions requires `mode`.** Host actions that depend on another `BaseAction` subclass must pass `mode=UseCase.include` or `mode=UseCase.extend`. Dependencies on `BaseResource` must omit `mode`. Call sites that only `box.resolve` a peer action should use `extend` until an unconditional `await box.run(...)` / `machine.run` path exists; then `include` is appropriate where the peer must always run in that root session.

### Added

- **OCEL 2.0 export (`aoa-ocel`).** New wheel `aoa-ocel` with `OcelFrame` aspect contract, `OcelPlugin` on `GlobalFinishEvent`, and E2O-only v1 policy (loaded one-hop FK relations, composite peer qualifiers, no O2O). `InMemoryOcelStoreResource` / `OcelStoreResource` accumulate `OcelEvent` DTOs and persist OCEL 2.0 JSON on `close()`; nested actions receive `OcelStoreWrapper`. `ActionProductMachine` exposes `all_aspect_states` on finish events so plugins can scan aspect pipeline state without mutating it. PM4Py smoke validation helpers live under `tests/ocel/`.
- **Store domain OCEL example.** `aoa-examples` ships StoreDomain lifecycle trace actions (`PublishOrder*OcelAction`), `build_store_ocel_machine` / `run_store_ocel_trace_batch`, and integration coverage writing `archive/logs/ocel.json` with OCPM-friendly `short_names` type labels.
- **UML generalization edges in the interchange graph.** Direct superclass links on the Action, Role, and Domain axes are exported as `parent_action`, `parent_role`, and `parent_domain` edges with relationship `Generalization` (`GENERALIZATION.archimate_name`). `GeneralizationGraphEdge.collect_direct_parents` in `aoa-graph` is the single parent-resolution algorithm; coordinator `to_json()` and `get_edges_by_type` expose the full edge set with no `include_generalization` flag. Maxitor DuckDB stores these in `parent_action_edges` / `parent_role_edges` / `parent_domain_edges` and in the unified `edges` view. **Exception:** `FullGraphAction` omits generalization links in the G6 full-graph payload only, filtering SQL by `relationship <> 'Generalization'` so the visualization stays sparse while data exports remain complete.
- **UML-style `@depends` mode (Use Case stereotypes).** `UseCase` / `VALID_USE_CASE_MODES`, `DependencyInfo.mode`, decorator validation, `DependsGraphEdge` and `resolved_dependency_infos` round-trip, and interchange JSON Schema (`optional` `mode` enum `include` / `extend` on `@depends` edges). `DependsIntentResolver.resolve_include_dependency_types` lists declared `include` targets. Package docs and READMEs describe semantics; **Maxitor DuckDB `depends_edges` in the default v1 path does not add a `mode` column** — consumers read `mode` from the full graph JSON.
- **Include contract on successful root runs.** `ActionProductMachine` tracks action classes that enter `_run_internal` for the current root session (`ContextVar`) and runs `IncludeContractChecker` before `emit_global_finish` when the aspect pipeline ran (including success paths that return only from `@on_error`). Missing `UseCase.include` executions raise `IncludeContractViolationError` with `missing_include_types`. Root cache hits that skip the pipeline skip this check.
- **Entity lifecycle (finite-state) diagram in Maxitor.** The operator SPA can open an entity's **Lifecycle view**: Graphviz `dot` renders the automaton as SVG with pan/zoom, LR/TB rank direction, and a **Fit to window** control. The backend exposes the lifecycle payload for the viewer (`GET /api/v1/lifecycle-finite-automaton`).
- **UML use-case diagram in Maxitor.** The operator SPA can render a domain-scoped UML-style use-case slice (actions in the Domain boundary, roles, `@check_roles` associations, action/role generalizations, and `@depends` edges including `UseCase.include` / `UseCase.extend` stereotypes) as Graphviz SVG with pan/zoom, Dot LR/TB and Neato/FDP layout presets, **Fit to window**, optional one-hop narrowing, and a sidebar entry per domain (`use_case_domain`). The payload is produced by `GetDomainUseCaseDiagramAction` from the DuckDB graph snapshot (`GET /api/v1/domain-use-case-diagram`).

### Fixed

- **Lifecycle Graphviz auto-fit.** Initial fit, resize refit, and LR/TB toggles now measure the correct SVG geometry (no stale markup, no `visibility: hidden` measurement trap), align `hasFittedRef` with successful fits, and apply a follow-up frame fit to match manual **Fit to window** without visible snapping.

## [0.12.5] – 2026-05-08

### Added

- **Optional action result cache.** `ActionProductMachine` accepts an injected `CacheCoordinator` (in-memory store, namespaced keys, optional `max_size` eviction). `BaseAction` gains `cache_key`, `read_cache`, and `on_cache_write`; the machine orchestrates reads after role/connection gates and `emit_global_start`, and writes only after a clean summary path (handled `@on_error` results are never cached). `CacheContractError` enforces hook return contracts; hook or coordinator failures propagate without `emit_global_finish` in v1.
- **JSON Schema fields in results.** Result schemas can declare explicit JSON-shaped fields so adapters expose the intended wire contract instead of relying on implicit Python object structure.
- **Entity JSON Schema projections in results.** `BaseEntity` classes can be referenced from result fields through an explicit JSON Schema projection, preserving the entity relationship while returning only the declared wire fields.
- **Node graph JSON serialization.** `NodeGraphCoordinator.to_json()` exports a stable JSON payload with linear `nodes` and `edges` lists, including node ids/types/labels/properties and edge source/target/type/relationship metadata, so downstream tools can reconstruct the coordinator graph without touching Python runtime objects.
- **NetworkX-friendly graph payloads.** Node and edge JSON is shaped for direct reconstruction into `networkx.DiGraph`: nodes are keyed by stable ids, edges carry `source_node_id` and `target_node_id`, and empty `nodes` / `edges` payloads are valid.

### Changed

- **Maxitor operator UI: React SPA instead of generated HTML as the primary surface.** The main Maxitor experience is now a **Vite** + **React** app (`packages/aoa-maxitor/client`) talking to the Maxitor FastAPI backend, rather than treating standalone Python-built HTML pages as the default workflow. Server-side HTML visualizers remain available where documented for specific interchange exports, but day-to-day graph exploration and diagrams are intended through the SPA.

### Removed

- **rustworkx from the interchange graph stack.** The live coordinator graph is no longer a rustworkx `PyDiGraph`; `aoa-graph` does not depend on rustworkx. Topology uses typed interchange nodes/edges with in-tree DAG checks (`aoa.graph._dag`); **NetworkX** is used where consumers need a `DiGraph` view (e.g. JSON export), not as an embedded rustworkx runtime.

### Breaking changes

- **Multiple PyPI packages and `aoa.*` layout.** Runtime code lives under `packages/aoa-*/src/aoa/{graph,action_machine,maxitor,examples}`. Public imports are `aoa.graph`, `aoa.action_machine`, `aoa.maxitor`, and `aoa.examples` only. Install `aoa-graph`, `aoa-action-machine`, `aoa-maxitor`, or `aoa-examples` as needed; there are no legacy top-level shims (`graph.*`, `action_machine.*`, …). `aoa-examples` does not pull `aoa-maxitor` as a dependency.

## [0.11.5] – 2026-05-08

### Changed

- **Interchange graph as the canonical topology.** Coordinators and tooling now pivot on `NodeGraphCoordinator` and typed interchange vertices (`BaseGraphNode`) and edges (`BaseGraphEdge`) — domains, lifecycle/entity meshes, declarative facets, propagated domain membership, and stable edge payloads (DAG flags, attachment / line-style metadata) replace ad-hoc graph sketches for visualization and serializers.

### Added

- **Interchange graph HTML visualizer.** `maxitor.visualizer.graph_visualizer` exports standalone **AntV G6** HTML from an already-built coordinator — forced layout seeded from domains, legends and hull overlays, interchange chrome (legend + tooling), hover affordances, **shared right-hand detail drawer** (`InterchangeDetailPanel`), and default artefact `archive/logs/graph_node.html`.
- **ERD HTML visualizer from the coordinator graph.** `maxitor.visualizer.erd_visualizer` builds relational diagrams per bounded context from the live graph (`erd_graph_data` / `erd_html`): standalone HTML with **Graphviz** wasm, **Cytoscape** + dagre, and **Mermaid** `erDiagram`, plus blended domains and UX aligned with the graph viewer (**shared interchange chrome**, same detail-drawer semantics for entity keys).

### Removed

- **Legacy ERD package split.** Drops the old `erd_visualizer_1` / `erd_visualizer_2` layout; `erd_visualizer` is now the single graph-backed viewer entry point.

## [0.10.0] – 2026-04-12

### Breaking changes

- **MCP tool `TextContent` bodies.** Responses are JSON objects with a uniform envelope: success uses `ok`, `code`, and `data`; errors use `ok`, `code`, `message`, and `details`. Plain action JSON and legacy prefixed strings (`PERMISSION_DENIED: …`, `INVALID_PARAMS: …`, `INTERNAL_ERROR: …`) are removed. Clients must parse the envelope. Unexpected failures return `message: "Unexpected failure"` without echoing exception text; operators use server logs.

### Changed

- **`ValidationFieldError`.** Optional keyword-only `details` (`dict`) for structured context; existing `ValidationFieldError(message)` and `ValidationFieldError(message, field)` calls behave as before. `str(exc)` remains the human `message` only.
- **MCP adapter.** Pydantic tool-arg validation lives in `_validate_tool_request_kwargs`, called from `_execute_tool_call`, so mapping to `ValidationFieldError` is defined in one place and covered by direct unit tests.

### Fixed

- **MCP tool kwargs validation.** Pydantic `model_validate` failures are surfaced as `ValidationFieldError` with `details.errors` and map to `INVALID_PARAMS`, not `INTERNAL_ERROR`.
- **Saga frame when result validation fails.** If a regular aspect `call()` returns but checkers (or declared-field rules) reject the dict, `AspectExecutor` still appends a `SagaFrame` with `state_after=None` when the action has compensators, so rollback invokes that aspect's compensator (then earlier frames) before surfacing the validation error.

## [0.9.0] – 2026-04-12

### Breaking changes

- **`SqlConnectionManager` renames.** `IConnectionManager` → `SqlConnectionManager` (`sql_connection_manager`); `WrapperConnectionManager` → `WrapperSqlConnectionManager` (`wrapper_sql_connection_manager`). No compatibility aliases.
- **Transactional `begin()`.** SQL connection managers implement `async def begin() -> None` after `open()`; `WrapperSqlConnectionManager.begin()` raises `TransactionProhibitedError` (same as `open`/`commit`/`rollback`). `PostgresConnectionManager` runs `BEGIN`.
- **Resource manager modules.** `resource_managers.connection` → `connection_decorator`; `resource_managers.connections` → `connections_typed_dict`. Canonical package: `aoa.action_machine.resources`. The old `resource_managers` package directory was removed; imports use `aoa.action_machine.resources` only.
- **Decorator modules (`*_decorator.py`).** e.g. `regular_aspect_decorator`, `check_roles_decorator`, `depends_decorator`, `on_decorator`; public decorator callables unchanged.
- **GateHost → Intent.** `*GateHost` → `*Intent`, `*GateHostInspector` → `*IntentInspector`, `BaseGateHostInspector` → `BaseIntentInspector`; files `*_intent.py` / `*_intent_inspector.py`.

## [0.8.0] – 2026-04-07

### Added

- **Saga compensation (`@compensate`).** Added a compensation mechanism (Saga pattern) to roll back side effects when an error occurs in the regular aspect pipeline. Any regular aspect can have a compensator method declared with `@compensate(target_aspect, description)`. When an error occurs in any aspect, all previously completed aspects are rolled back in reverse order. Compensators can use `@context_requires` and receive two states: `state_before` (state before the aspect) and `state_after` (state after the aspect, `None` if a checker rejected the result). The return value of a compensator is ignored.
- **Local compensation stacks.** Each `_run_internal()` call creates its own local `SagaFrame` stack. There is no global stack, ensuring correct isolation for nested `box.run()` calls.
- **Silent compensator errors.** Exceptions raised inside a compensator are completely suppressed and do not interrupt stack unwinding. All remaining compensators still get a chance to execute. Failure information is available only through the new typed event `CompensateFailedEvent`.
- **New typed compensation events.** `SagaRollbackStartedEvent`, `SagaRollbackCompletedEvent`, `BeforeCompensateAspectEvent`, `AfterCompensateAspectEvent`, `CompensateFailedEvent`.
- **`TestBench.run_compensator()` method.** Allows unit-testing a compensator in isolation.
- **Naming rule for compensators.** Compensator method names must end with `_compensate`.

## [0.7.0] – 2026-04-07

### Added

- **Frozen `BaseState` and `BaseResult`.**
- **`@context_requires` decorator for controlled context access.**
- **`Ctx` constant hierarchy.**
- **`DotPathNavigator` — unified dot-path navigation.**
- **`@on_error` decorator for action-level error handling.**
- **Naming invariants (suffix checks).**
- **`check_roles` as a function (decorator).**
- **Result checkers as function decorators.**
- **`SyncActionProductMachine` — synchronous production machine.**
- **`TestBench` — immutable fluent testing API.**

## [0.5.5] – 2026-03-31

### Added

- **ScopedLogger in plugin handlers.**
- **Nest level in logging scope and templates.**
- **Configurable indentation in ConsoleLogger.**
- **Business domains (`BaseDomain`).**
- **`@meta` decorator for mandatory class descriptions.**
- **FastAPI adapter (`FastApiAdapter`).**
- **MCP adapter (`McpAdapter`).**

## [0.4.5] – 2026-03-28

### Added

- **`metadata` subpackage for structured metadata assembly.**
- **Idempotent metadata building.**

## [0.4.0] – 2026-03-21

### Added

- **Intent-based aspect architecture (`AspectIntent`).**
- **`ToolsBox` — unified container for aspect tools.**
- **Explicit nesting level tracking.**

## [0.3.5] – 2026-03-19

### Added

- **`debug()` function for object introspection in log templates.**
- **`exists()` function for safe variable presence checks.**
- **Color filters in log templates.**
- **`@sensitive` decorator for data masking in logs.**

## [0.3.0] – 2026-03-19

### Added

- **Cross-cutting logging via `ScopedLogger`.**
- **`mode` parameter in machine constructors.**
- **Level-based coloring in `ConsoleLogger`.**

## [0.2.5] – 2026-03-18

### Added

- **PEP 8 file naming convention.**
- **Centralized linter configuration.**

## [0.2.0] – 2026-03-17

### Added

- **Conditional logic in log templates (`iif`).**
- **`VariableSubstitutor` — extracted substitution engine.**
- **`PluginCoordinator` — extracted plugin management.**
- **Connection validation chain.**

## [0.1.5] – 2026-03-16

### Added

- **Unified data access protocols (`ReadableDataProtocol`, `WritableDataProtocol`).**
- **`ReadableMixin` and `WritableMixin`.**
- **`resolve()` method for dot-path navigation.**
- **Asynchronous authentication pipeline.**

## [0.1.0] – 2026-03-15

### Added

- **Action-Oriented Architecture (AOA) core.** Initial release.
