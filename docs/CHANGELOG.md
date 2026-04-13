# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Terminology

Older entries below may use the legacy names **GateHost** / `*GateHostInspector` /
`BaseGateHostInspector`. The current public API uses **Intent** mixins and
**IntentInspector** classes (e.g. `RoleIntent`, `AspectIntent`, `BaseIntentInspector`).
The coordinator class name **`GateCoordinator`** is unchanged.

## Unreleased

### BREAKING

- **`IConnectionManager` → `SqlConnectionManager`.** The abstract transactional SQL
  connection base class and module were renamed: ``iconnection_manager`` →
  ``sql_connection_manager``. Update imports and type hints; there is no alias.

- **`WrapperConnectionManager` → `WrapperSqlConnectionManager`.** The nested-run SQL
  proxy class and module were renamed: ``wrapper_connection_manager`` →
  ``wrapper_sql_connection_manager``. Update imports; there is no alias.

- **`SqlConnectionManager.begin()`.** Transactional connection managers must implement
  `async def begin(self) -> None` (start one DB transaction after `open()`, before
  mutating `execute` calls so rollup and `commit`/`rollback` are meaningful with
  asyncpg). `WrapperSqlConnectionManager.begin()` raises `TransactionProhibitedError`
  (same as `open`/`commit`/`rollback`). `PostgresConnectionManager` runs `BEGIN`.

- **Resource managers: distinguish decorator vs TypedDict modules.** Renamed
  ``resource_managers.connection`` → ``connection_decorator`` (``@connection``,
  ``ConnectionInfo``) and ``resource_managers.connections`` →
  ``connections_typed_dict`` (``Connections``). Update deep imports; the package
  ``action_machine.resource_managers`` still re-exports ``connection``,
  ``ConnectionInfo``, and now ``Connections`` in ``__all__``.

- **Decorator modules: `*_decorator.py` filenames.** Renamed
  ``aspects/regular_aspect.py`` → ``regular_aspect_decorator.py``,
  ``aspects/summary_aspect.py`` → ``summary_aspect_decorator.py``,
  ``auth/check_roles.py`` → ``check_roles_decorator.py``,
  ``auth/role_mode.py`` → ``role_mode_decorator.py``,
  ``dependencies/depends.py`` → ``depends_decorator.py``,
  ``plugins/decorators.py`` → ``on_decorator.py``. Exported decorator callables
  (``regular_aspect``, ``check_roles``, ``on``, …) are unchanged; update any
  deep imports from old module paths.

- **GateHost → Intent (public API and module layout).** Marker mixins and
  inspectors were renamed for consistent «grammar of intents» language:
  `*GateHost` → `*Intent`, `*GateHostInspector` → `*IntentInspector`,
  `BaseGateHostInspector` → `BaseIntentInspector`. Files follow
  `*_intent.py` / `*_intent_inspector.py`. Imports and MRO references must be
  updated; there are no compatibility aliases in this release line.

| Legacy (removed) | Replacement |
|------------------|-------------|
| `ActionMetaGateHost` | `ActionMetaIntent` |
| `ResourceMetaGateHost` | `ResourceMetaIntent` |
| `RoleGateHost` | `RoleIntent` |
| `DependencyGateHost` | `DependencyIntent` |
| `CheckerGateHost` | `CheckerIntent` |
| `AspectGateHost` | `AspectIntent` |
| `CompensateGateHost` | `CompensateIntent` |
| `ConnectionGateHost` | `ConnectionIntent` |
| `OnErrorGateHost` | `OnErrorIntent` |
| `ContextRequiresGateHost` | `ContextRequiresIntent` |
| `DescribedFieldsGateHost` | `DescribedFieldsIntent` |
| `EntityGateHost` | `EntityIntent` |
| `OnGateHost` | `OnIntent` |
| `RoleModeGateHost` | `RoleModeIntent` |
| `BaseGateHostInspector` | `BaseIntentInspector` |
| `RoleGateHostInspector` | `RoleIntentInspector` |
| (same pattern) | `*IntentInspector` for each facet |
| `SensitiveGateHostInspector` | `SensitiveIntentInspector` |

### Compatibility (PR-3)

- **No deprecation aliases** (e.g. `RoleGateHost = RoleIntent`) and no
  `action_machine.compat` shim are provided. The API surface uses **Intent**
  names only; this keeps imports and documentation unambiguous while the
  project is pre-`1.0.0`. If temporary aliases are ever needed for a major
  migration, they would be introduced in a dedicated release with explicit
  removal timeline and `DeprecationWarning` on each alias.

### Documentation (PR-3)

- **Glossary** — end of `README.md` and `README-2.md`: Intent, IntentInspector,
  `GateCoordinator`, decorator, scratch, and distinction from «business intent»
  in prose.
- **Repository verification (2026-04-12):** `GateHost`, `gate_host`, and
  `*gate_host*` filenames — **no matches** in `src/**/*.py` and `tests/**/*.py`;
  no `*gate_host*` files under `src/` or `tests/`. Historical names remain only
  in this changelog (Terminology + migration table + older release bullets where
  not yet rewritten).

### Changed (facet graph — described fields)

- **`DescribedFieldsIntentInspector` now follows `DescribedFieldsIntent`.** It walks schema classes (``BaseParams`` / ``BaseResult`` / ``BaseEntity`` subtrees), not ``BaseAction``. Graph nodes ``described_fields:<module.Schema>`` carry per-model field metadata; ``node_meta`` uses key ``schema_fields`` (not ``params_fields`` / ``result_fields``).
- **`ActionTypedSchemasInspector` (new).** Registered after ``DescribedFieldsIntentInspector``. For each action class it resolves ``BaseAction[P, R]`` via ``extract_action_params_result_types`` and emits an ``action_schemas`` node with informational edges ``uses_params`` / ``uses_result`` to the corresponding ``described_fields`` targets. Facet snapshot key: ``"action_schemas"``.
- **`extract_action_params_result_types`** lives in ``action_machine.core.action_generic_params`` (single place for generic extraction).
- **Validation API:** removed ``validate_described_fields(action_cls, params_fields, result_fields)``. Use ``validate_described_schema(model_cls | None)`` for one schema, or ``validate_described_schemas_for_action(action_cls)`` to validate both ``P`` and ``R`` after resolving them from the action class.

### BREAKING (GateCoordinator rustworkx nodes)

- **`GateCoordinator.get_graph()` node dicts** store only ``node_type``, ``name``, and ``class_ref``. Facet wire ``meta`` is not duplicated on the graph node. Use ``hydrate_graph_node(dict(graph[idx]))`` or ``get_node`` / ``get_nodes_by_type`` / ``get_nodes_for_class``.

### Added (GateCoordinator hydration)

- **`GateCoordinator.hydrate_graph_node`** rebuilds ``meta`` from facet snapshots. Phase 1 registers each graph key’s snapshot storage key from ``facet_snapshot_storage_key()``; two different keys on the same merged structural ``action`` node (``depends`` + ``connections``) yield empty hydrated ``meta``. Unregistered stub nodes fall back to ``get_snapshot(cls, node_type)`` (except ``action``).
- **MCP system graph JSON:** edges include ``source_key`` and ``target_key`` (``node_type:name``); ``type`` is the string ``edge_type`` from edge payloads.
- **Tests:** ``tests/metadata/test_graph_skeleton_and_hydrate.py``, ``tests/metadata/test_graph_execution_adapters.py``; MCP graph JSON coverage in ``tests/adapters/mcp/test_mcp_handler.py``.

### Changed (docs — coordinator graph)

- **README / README-2 glossary:** clarify skeleton graph nodes, snapshots, and hydration.

### BREAKING (facet snapshots)

- **``get_snapshot(SomeAction, "described_fields")`` is removed.** Described-field snapshots are stored per schema class: ``get_snapshot(OrderParams, "described_fields")``, ``get_snapshot(OrderResult, "described_fields")``. Use ``get_snapshot(SomeAction, "action_schemas")`` for the action’s resolved ``P``/``R`` types and graph linkage.

### Changed

- **Machine-owned plugin lifecycle events** — all six types (`GlobalStartEvent`,
  `GlobalFinishEvent`, `BeforeRegularAspectEvent`, `AfterRegularAspectEvent`,
  `BeforeSummaryAspectEvent`, `AfterSummaryAspectEvent`) are emitted through async helpers on
  `PluginEmitSupport` (`emit_global_start`, `emit_global_finish`, `emit_before_regular_aspect`,
  `emit_after_regular_aspect`, `emit_before_summary_aspect`, `emit_after_summary_aspect`).
  `ActionProductMachine` no longer calls `plugin_ctx.emit_event` or constructs those event
  classes directly. `PluginRunContext` is always passed into each helper; it is not stored on
  `PluginEmitSupport` (per-run isolation, no reset between runs).

### Fixed

- **`ActionProductMachine` — saga rollback on summary contract failures.** If regular aspects have run and pushed `SagaFrame`s, then the pipeline fails with `ActionResultTypeError`, `MissingSummaryAspectError`, or `ActionResultDeclarationError` (wrong summary return type, missing `@summary_aspect` for a custom `Result`, or unresolvable `BaseAction[P, R]`), the machine now runs **`SagaCoordinator.execute`** (same unwind as other failures) **before** re-raising. Previously these exceptions bypassed compensation and could leave side effects unrolled. **`@on_error` is not invoked** for these cases — they are treated as developer contract violations, not recoverable business errors.

### Added

- **Adapter mapper runtime checks (`BaseRouteRecord`).** `ensure_machine_params` and `ensure_protocol_response` validate that `params_mapper` / `response_mapper` return instances of `params_type` and `effective_response_model`; FastAPI and MCP adapters call them at the protocol boundary (`TypeError` on mismatch). Tests: `test_base_route_record.py` (unit), `test_fastapi_mapper_guards.py`, MCP handler tests.
- **Runtime action result typing.** Summary and `@on_error` return values are checked against the action’s declared `R` (`action_machine.core.action_result_binding`, exceptions `ActionResultTypeError`, `MissingSummaryAspectError`, `ActionResultDeclarationError`). Forward-ref `P`/`R` resolution is centralized in `action_machine.core.action_generic_params`.

## [0.9.0] – 2026-04-07

### Added

- **Saga compensation (`@compensate`).** Added a compensation mechanism (Saga pattern) to roll back side effects when an error occurs in the regular aspect pipeline. Any regular aspect can have a compensator method declared with `@compensate(target_aspect_name, description)`. When an error occurs in any aspect, all previously completed aspects are rolled back in reverse order. Compensators can use `@context_requires` and receive two states: `state_before` (state before the aspect) and `state_after` (state after the aspect, `None` if a checker rejected the result). The return value of a compensator is ignored.

- **Local compensation stacks.** Each `_run_internal()` call creates its own local `SagaFrame` stack. There is no global stack, ensuring correct isolation for nested `box.run()` calls. If a parent aspect catches a child action exception via `try/except`, the child stack is already unwound, and the parent aspect is added to the parent stack – subsequent errors in the parent cause only the parent stack to be rolled back.

- **Silent compensator errors.** Exceptions raised inside a compensator are completely suppressed and do not interrupt stack unwinding. All remaining compensators still get a chance to execute. Failure information is available only through the new typed event `CompensateFailedEvent`, which monitoring plugins can subscribe to. This guarantees that a rollback error does not mask the original business error and does not break consistency.

- **New typed compensation events.** Added two levels of events:
  - **Whole‑rollback level:** `SagaRollbackStartedEvent` (contains `stack_depth`, `compensator_count`, `aspect_names`) and `SagaRollbackCompletedEvent` (contains `total_frames`, `succeeded`, `failed`, `skipped`, `duration_ms`, `failed_aspects`).
  - **Single compensator level:** `BeforeCompensateAspectEvent` (contains `error`, `compensator_name`, `state_before`, `state_after`), `AfterCompensateAspectEvent` (contains `duration_ms`), and `CompensateFailedEvent` (contains `original_error`, `compensator_error`, `failed_for_aspect`).

- **`SagaFrame` – compensation stack frame.** An immutable dataclass that stores, for each successfully executed regular aspect: a reference to its compensator (`CompensatorMeta`), the aspect name, and the state before and after the aspect. The stack is accumulated in `_execute_regular_aspects()` and consumed by `_rollback_saga()`.

- **`CompensatorMeta` in `ClassMetadata`.** Added field `compensators: tuple[CompensatorMeta, ...]` and helper methods `has_compensators()`, `get_compensator_for_aspect(aspect_name)`. Compensators are collected from `vars(cls)` (not inherited). Invariants are validated in `MetadataBuilder.build()`: target aspect must exist, must be a regular aspect, and at most one compensator per aspect.

- **Compensator graph in `GateCoordinator`.** New node type `"compensator"` and edge type `"has_compensator"` (leaf edge, no cycle check). Compensator nodes store metadata `target_aspect`, `description`, `method_name`. If a compensator uses `@context_requires`, additional `"requires_context"` edges are added to `context_field` nodes.

- **`TestBench.run_compensator()` method.** Allows unit‑testing a compensator in isolation by passing `params`, `state_before`, `state_after`, `error`, and optionally `box`, `connections`, `context`. Unlike production, compensator errors are **not** suppressed – this makes it easy to test boundary conditions and verify that a compensator behaves correctly when it must fail. The API is symmetric with `run_aspect()`: method lookup by name, validation of the `@compensate` decorator, and support for `@context_requires`.

- **Naming rule for compensators.** Compensator method names must end with `_compensate` (enforced by `@compensate`, violation raises `ValueError`). The suffix ensures visual identification of compensators in action classes.

- **`rollup=True` skips compensation.** When `box.rollup is True`, the compensation stack is not built and `_rollback_saga()` is never called. Transactional rollback in that mode is handled by `SqlConnectionManager` (which executes `rollback()` instead of `commit()`), while non‑transactional side effects (HTTP requests, email sending) are not compensated in rollup mode.

### Changed

- **`ActionProductMachine._execute_regular_aspects()` now returns a tuple `(state, saga_stack)`.** This allows `_execute_aspects_with_error_handling()` to obtain the stack for later unwinding when an exception occurs.

- **Error handling order:** compensation stack unwinding (`_rollback_saga()`) now happens **before** calling an `@on_error` handler (if any). This guarantees that the error handler works with consistent data after all side effects of previously completed aspects have been rolled back.

- **`ActionProductMachine._execute_aspects_with_error_handling()` declares `saga_stack` before the `try` block.** The stack is accessible in the `except` clause even if the exception originates inside `_execute_regular_aspects()`. Frames for the failed aspect are not added, but frames for all previous successful aspects remain.

- **`_rollback_saga()` never raises exceptions.** Compensator errors are caught, logged via `CompensateFailedEvent`, and the unwinding continues. After the loop, a `SagaRollbackCompletedEvent` is emitted with the final counters. The original aspect error is then propagated (or passed to `@on_error`).

### Fixed

- **Nested `try/except` with `box.run()` now works correctly.** Previously, if a parent aspect caught an exception from a child action, the parent aspect was not added to the parent stack, causing missing compensation for the parent when a later aspect failed. Now the child’s internal stack is unwound independently, and the parent aspect is added to the parent stack as if the child call succeeded (from the parent’s perspective).

- **Compensator `state_after=None` handling.** When a checker rejects an aspect’s result, the aspect may still have performed a side effect (e.g., an HTTP request was already sent). The compensator now receives `state_after=None` and can choose to skip compensation or perform a best‑effort rollback based on available data from `state_before` or other sources.

- **`rollup=True` no longer causes compensator stack to be built.** Previously the stack was built but not used; now the entire stack creation is skipped, improving performance and avoiding misleading `skipped` counters in events.

### Removed

- **`CompensateIntent` (no extra mixin required for compensators).** Compensators rely on `AspectIntent` (already inherited by `BaseAction`). No separate intent mixin is required.

### Security

- **Compensator errors never expose internal state to `@on_error` handlers.** The original business exception is preserved; compensator failures are isolated to monitoring events, preventing information leakage or unexpected error masking.

## [0.8.0] – 2026-04-07

### Added

- **Frozen `BaseState` and `BaseResult`.** Both types are now fully immutable after creation. `BaseState` uses `__setattr__` override to forbid any writes; the only way to modify state is to create a new instance via `BaseState({**old.to_dict(), **new_data})`. `BaseResult` is a frozen Pydantic model (`frozen=True`, `extra="forbid"`), ensuring that result fields are strictly declared and cannot be mutated after the summary aspect returns. This eliminates entire classes of bugs where aspects could silently bypass checkers or mutate results.

- **`@context_requires` decorator for controlled context access.** Aspects and error handlers can now declare exactly which context fields they need using dot‑path strings (e.g., `@context_requires(Ctx.User.user_id, Ctx.Request.trace_id)`). The machine provides a `ContextView` object that only grants access to the requested fields; any attempt to read an undeclared field raises `ContextAccessError`. Without the decorator, an aspect receives **no** context access at all. This implements the principle of least privilege and makes context dependencies explicit and statically verifiable.

- **`Ctx` constant hierarchy.** A structured set of constants (`Ctx.User.user_id`, `Ctx.Request.trace_id`, `Ctx.Runtime.hostname`, etc.) providing IDE autocompletion and compile‑time checks for standard context fields. Custom fields can be passed as plain strings, e.g., `"user.billing_plan"`.

- **`DotPathNavigator` – unified dot‑path navigation.** Centralised the navigation logic previously duplicated between `BaseSchema.resolve()` and `VariableSubstitutor`. The navigator uses duck typing (`__getitem__` detection) to support `BaseSchema`, `LogScope`, `dict`, and any custom object with a dict‑like interface, without creating circular dependencies between core and logging.

- **Strict underscore rule in log templates.** Any template variable whose **any** path segment starts with an underscore now raises `LogTemplateError`. Previously only the last segment was checked, which allowed bypassing private attributes through intermediate segments (`{%context._internal.public_key}`). All segments are now validated.

- **`@on_error` decorator for action‑level error handling.** Actions can declare handlers for exceptions raised by any aspect. Handlers receive the error and can return an alternative `Result`, effectively replacing the action’s outcome. Handlers are checked in declaration order; the first matching exception type (via `isinstance`) is executed. Handlers can also request context via `@context_requires`, receiving their own `ContextView`. Cyclic exception type coverage (e.g., `Exception` before `ValueError`) is detected at metadata build time and raises `TypeError`.

- **`OnErrorHandlerError` exception.** Wraps exceptions that occur inside an `@on_error` handler, preserving the original exception as `__cause__`. Distinguishes between business logic errors (original aspect exception) and bugs in error handling code.

- **Naming invariants (suffix checks).** The framework now enforces naming conventions via `__init_subclass__` and decorator validations:
  - Action classes must end with `Action`.
  - Domain classes must end with `Domain`.
  - Methods with `@regular_aspect` must end with `_aspect`.
  - Methods with `@summary_aspect` must end with `_summary`.
  - Methods with `@on_error` must end with `_on_error`.
  - Plugin methods with `@on` must start with `on_`.
  - Checker classes must end with `Checker`.
  Violations raise `NamingSuffixError` or `NamingPrefixError`.

- **`check_roles` as a function (decorator).** Replaced the old `CheckRoles` class with a plain function `check_roles(spec)`. The `desc` parameter (previously ignored) has been removed entirely. Special values `ROLE_NONE` and `ROLE_ANY` are now module‑level constants.

- **Result checkers as function decorators.** Each checker now has a dedicated function decorator: `result_string`, `result_int`, `result_float`, `result_bool`, `result_date`, `result_instance`. The old class‑based invocation has been removed. Decorators no longer accept a `description` parameter, keeping the API minimal.

- **`SyncActionProductMachine` – synchronous production machine.** A synchronous counterpart to `ActionProductMachine` that wraps the async pipeline in `asyncio.run()`. The public `run()` method is synchronous. Designed for CLI scripts, Celery tasks, and Django views without async support. Both production machines always pass `rollup=False` internally.

- **`TestBench` – immutable fluent testing API.** A single entry point for testing actions across both async and sync machines. Supports `.with_user()`, `.with_mocks()`, `.with_runtime()`, etc., each returning a new immutable instance. Terminal methods (`run`, `run_aspect`, `run_summary`) accept a mandatory `rollup: bool` parameter (no default). Automatically resets mock state between the async and sync runs so that `assert_called_once_with()` works correctly.

- **`validate_state_for_aspect` and `validate_state_for_summary`.** Helper functions that verify that a manually provided `state` dictionary contains all required fields (according to checkers of preceding aspects) before executing a single aspect or summary in tests. Produces clear error messages indicating which aspect should have written which field.

- **`compare_results` for multi‑machine result comparison.** Compares results from async and sync machines, showing field‑level differences when results diverge. Used internally by `TestBench` and available for custom test assertions.

- **Context stub helpers.** `UserInfoStub`, `RuntimeInfoStub`, `RequestInfoStub`, `ContextStub` provide reasonable defaults for testing, reducing boilerplate.

- **`rollup` support in dependency resolution and connection managers.** The `rollup` flag now propagates through `ToolsBox.resolve()` and into connection managers. When `rollup=True`, any `SqlConnectionManager` will execute `rollback()` instead of `commit()`, enabling safe testing on production databases. Managers that do not support rollup raise `RollupNotSupportedError`.

- **`BaseResourceManager.check_rollup_support()`.** A new method that concrete managers can override to declare rollup support (default raises `RollupNotSupportedError`). `SqlConnectionManager` overrides it to return `True`.

- **Context field nodes in the coordinator graph.** `GateCoordinator` now creates nodes of type `context_field` for every unique dot‑path requested by `@context_requires`. Edges of type `requires_context` connect aspect nodes (or error handler nodes) to these fields. This closes the last gap in the system graph, allowing full introspection of context dependencies.

- **Documentation of graph node key format.** Public methods `get_node()`, `get_children()`, `get_dependency_tree()` now have docstrings explaining the `"type:full_name"` key format, with examples for `context_field`, `action`, `domain`, etc.

### Changed

- **`BaseParams` and `BaseResult` now strictly require `Field(description=...)` for every field** (via `DescribedFieldsIntent`). Previously descriptions were optional; now a missing or empty description raises `TypeError` during metadata assembly. This ensures that all API parameters and results are self‑documented from the start.

- **`@on` decorator now accepts typed event classes instead of strings.** The old string‑based `event_type` and `action_filter` are removed. New signature: `@on(event_class, *, action_class=None, action_name_pattern=None, aspect_name_pattern=None, nest_level=None, domain=None, predicate=None, ignore_exceptions=True)`. Filter order follows cheapest‑first (`isinstance` → regex → predicate). Multiple `@on` decorators on the same method produce OR semantics.

- **`PluginEvent` replaced by a hierarchy of event classes.** `BasePluginEvent` → `GlobalLifecycleEvent` → `GlobalStartEvent`/`GlobalFinishEvent`, `AspectEvent` → `RegularAspectEvent` → `BeforeRegularAspectEvent`/`AfterRegularAspectEvent`, etc. Each class contains only the fields relevant to that event, eliminating the “bag of optional None” anti‑pattern.

- **`Plugin.get_handlers()` now filters by type (`isinstance`) instead of string matching.** The `event_name` string parameter is replaced by the event class itself.

- **`PluginRunContext.emit_event()` now accepts a concrete event object instead of a list of parameters.** The method applies the filter chain described above and executes matching handlers in parallel or sequentially depending on `ignore_exceptions` flags.

- **`ToolsBox` does not store `Context` on the instance.** Aspects cannot access execution context via `box` at all (including mangled attributes). `ContextView` from `@context_requires` is the only aspect-visible path to context data. `ScopedLogger` still receives `Context` for template substitution; nested runs use a machine closure that captures `Context` for `_run_internal`.

- **`ActionProductMachine.gate_coordinator` (read-only property).** Public access to the built `GateCoordinator` for adapters, tooling, and tests. Prefer this over reading `machine._coordinator`.

- **`BaseAdapter` optional `gate_coordinator` (keyword-only) and `gate_coordinator` property.** Defaults to `machine.gate_coordinator`. `McpAdapter` and `FastApiAdapter` forward the same parameter. MCP graph JSON helpers take a `GateCoordinator` directly instead of reaching into private machine fields.

- **`PluginEmitSupport` and coordinator decoupling.** `ActionProductMachine` builds a `PluginEmitSupport` instance (public `plugin_emit_support` property) for `base_fields` / `emit_extra_kwargs` used with `PluginRunContext.emit_event`. `SagaCoordinator` takes `PluginEmitSupport` instead of `LogCoordinator` and no longer receives the machine in `execute()`. `ErrorHandlerExecutor` takes `PluginEmitSupport` in its constructor and `handle()` no longer takes the machine as the first argument. Removed private `_base_event_fields` / `_build_plugin_emit_kwargs` from the machine (logic lives on `PluginEmitSupport`).

- **`DependencyFactoryResolver`, `ToolsBoxFactory`, and `AspectExecutor` without `_MachineLike`.** New protocol `DependencyFactoryResolver` with `dependency_factory_for(action_cls)`; `ActionProductMachine` implements it publicly. `ToolsBoxFactory` takes only `LogCoordinator` and `create(..., factory_resolver=..., mode=..., machine_class_name=..., ...)`. `AspectExecutor` is constructed with `log_coordinator`, `machine_class_name`, and `mode`; `call` / `execute_regular` / `execute_summary` no longer accept a machine-shaped first argument.

- **`BaseAction` generic parameters `P` and `R` are now bound to `BaseSchema` instead of `ReadableDataProtocol`.** This reflects the architectural shift: all data structures inherit `BaseSchema`.

- **`WritableMixin` and `WritableDataProtocol` removed.** After freezing `BaseState` and `BaseResult`, there are no remaining consumers of write‑able dict‑like access. The read‑only protocol `ReadableDataProtocol` remains for compatibility.

- **`CheckRoles` class removed; use `check_roles` function.** Old code: `@CheckRoles("admin", desc="...")` → new: `@check_roles("admin")`. The `desc` parameter is no longer accepted.

- **Checker decorators no longer accept a `description` parameter.** Use `@result_string("txn_id", required=True)` instead of `@result_string("txn_id", "Transaction ID", required=True)`.

- **`ResultFieldChecker.__init__` signature changed:** removed `description`, now only `field_name` and `required`. All checkers follow the same pattern.

- **`RoleMeta` and `CheckerMeta` dataclasses no longer contain a `description` field.** The `description` was dead code (never used) and has been removed from metadata.

- **`ActionProductMachine._check_action_roles()` now expects `ROLE_NONE` and `ROLE_ANY` as module‑level constants, not class attributes.**

- **`ActionProductMachine._call_aspect()` and `_handle_aspect_error()` now create `ContextView` and pass it as the last argument when `context_keys` is non‑empty.** The number of parameters in aspect methods is now validated based on the presence of `@context_requires` (5 without, 6 with).

- **`SyncActionProductMachine` moved from `core/` to its own file and made a proper subclass of `ActionProductMachine`.** Previously it was a separate class; now it inherits all pipeline logic and only overrides `run()` to be synchronous.

- **`ActionTestMachine` moved to `testing/async_test_machine.py` and renamed to `AsyncTestMachine`.** A corresponding `SyncTestMachine` was added. Both are instantiated by `TestBench`.

- **`MockAction` moved to `testing/mock_action.py`.** Its behaviour remains unchanged.

### Removed

- **`WritableMixin` and `WritableDataProtocol`.** Completely removed from the codebase. The framework no longer provides any dict‑like write interface for core data types.

- **`CheckRoles` class.** Replaced by `check_roles` function.

- **`regular_aspect` and `summary_aspect` no longer accept a `desc` parameter.** Description is now mandatory and passed as the first positional argument.

- **`PluginEvent` monolithic class.** Replaced by the typed event hierarchy.

- **String‑based event types in `@on`.** All subscriptions must use event classes.

- **`description` parameter from all result checker decorators.**

- **`ResultFieldChecker._build_meta()` inclusion of `description`.**

- **Dead code from `core/action_test_machine.py` and `core/mock_action.py` (moved).**

- **`extra="allow"` and `arbitrary_types_allowed=True` from `BaseResult`.** Results are now strictly typed and forbid extra fields.

- **`__setitem__`, `__delitem__`, `write`, `update` from `BaseState`.** The class is now fully immutable.

- **`ReadableDataProtocol` and `ReadableMixin` are still present** (not removed), but all references in docstrings have been updated to reflect that `BaseSchema` is the primary interface.

### Security

- **Access to private attributes in log templates is now blocked for any path segment, not only the last one.** This prevents bypassing the underscore rule via intermediate segments (`{%context._internal.public_key}`).


## [0.7.0] – 2026-03-31

### Added

- **ScopedLogger in plugin handlers.** All plugin handlers (`@on` methods) now receive a fourth parameter `log` — a `ScopedLogger` instance bound to the plugin's scope. The scope contains fields `machine`, `mode`, `plugin` (plugin class name), `action` (full action class name), `event` (event name such as `global_finish` or `before:validate`), and `nest_level` (call nesting depth). This enables plugins to log with full execution context using all five template namespaces (`{%scope.plugin}`, `{%var.count}`, `{%context.user.id}`, etc.). The handler signature is `async def handler(self, state, event, log)` — all four parameters are mandatory.

- **Nest level in logging scope and templates.** The `nest_level` field is now included in the `LogScope` for both aspects and plugin handlers. Developers can reference it in log templates via `{%scope.nest_level}` to display the current call depth. Root actions have `nest_level=1`, first-level child actions called via `box.run()` have `nest_level=2`, and so on. This makes it easy to trace nested action execution in log output and distinguish between parent and child action logs.

- **Configurable indentation in ConsoleLogger.** `ConsoleLogger` now accepts `use_indent` (bool, default `True`) and `indent_size` (int, default `2`) parameters. When `use_indent=True`, each log line is prefixed with `nest_level * indent_size` spaces, creating a visual hierarchy of nested action calls. When `use_indent=False`, all lines are printed without indentation — useful for production environments where logs are sent to ELK/Loki and indentation interferes with parsing. The indent is calculated from the `nest_level` passed through the logging pipeline.

- **Business domains (`BaseDomain`).** Introduced the `action_machine.domain` package with `BaseDomain` — an abstract base class for declaring typed business domains. Each domain is a class with a mandatory `name: ClassVar[str]` attribute, validated at class creation time via `__init_subclass__`. Domains serve as typed markers for grouping actions and resources by business area. Unlike string-based identifiers, class-based domains provide IDE autocompletion, import-time error detection for typos, and refactoring support. Domains appear as dedicated nodes in the GateCoordinator graph with `belongs_to` edges from actions and resources.

- **`@meta` decorator for mandatory class descriptions.** Every Action (with aspects) and every ResourceManager must now have a `@meta(description="...", domain=...)` decorator. The `description` parameter is mandatory and must be a non-empty string. The `domain` parameter is optional and accepts a `BaseDomain` subclass. Two intent markers enforce this requirement: `ActionMetaIntent` (inherited by `BaseAction`) and `ResourceMetaIntent` (inherited by `BaseResourceManager`). MetadataBuilder raises `TypeError` if `@meta` is missing. The description and domain are stored in `ClassMetadata.meta` as a frozen `MetaInfo` dataclass and are used by adapters for OpenAPI summaries and MCP tool descriptions.

- **Domain nodes and `belongs_to` edges in the coordinator graph.** When `@meta` specifies a `domain`, GateCoordinator creates a node of type `domain` and a `belongs_to` edge from the class to the domain. Domain nodes are idempotent — multiple actions in the same domain share a single node. Action and dependency node payloads are enriched with `description` and `domain` fields from `@meta`, making the graph self-documenting without requiring access to ClassMetadata.

- **Strict mode for GateCoordinator.** `GateCoordinator` now accepts a `strict: bool = False` parameter. When `strict=True`, the coordinator additionally validates that `domain` is specified in `@meta` for all Actions (with aspects) and ResourceManagers. If `domain=None` in strict mode, a `ValueError` is raised. The `description` field is always validated regardless of strict mode — it is an unconditional invariant. The coordinator is passed as a parameter to `ActionProductMachine`, not created internally, allowing easy configuration of strict mode for production deployments.

- **Pydantic-based `BaseParams` and `BaseResult`.** `BaseParams` now inherits from `pydantic.BaseModel` with `frozen=True`, providing immutable parameters with automatic type validation, constraints (`gt`, `min_length`, `pattern`), and JSON Schema generation via `model_json_schema()`. `BaseResult` inherits from `pydantic.BaseModel` with `extra="allow"`, supporting both declared fields and dynamic extra fields written through `WritableMixin`. Both classes retain full `ReadableMixin` compatibility (`resolve()`, `keys()`, `values()`, `items()`, `__getitem__`). `BaseState` remains a plain class — it is not converted to Pydantic because its fields are dynamic and determined at runtime.

- **`DescribedFieldsIntent` for mandatory field descriptions.** A marker mixin inherited by `BaseParams` and `BaseResult`. MetadataBuilder validates that every Pydantic field in classes inheriting this mixin has a non-empty `description` in `Field(description="...")`. Fields without descriptions raise `TypeError` at metadata assembly time, ensuring that all API parameters and results are self-documented from the start.

- **`FieldDescriptionMeta` in `ClassMetadata`.** A new frozen dataclass capturing field-level metadata: `field_name`, `field_type`, `description`, `examples`, `constraints` (gt, ge, min_length, max_length, pattern, etc.), `required`, and `default`. ClassMetadata now includes `params_fields` and `result_fields` tuples, populated by collectors that extract generic parameters P and R from `BaseAction[P, R]` and read Pydantic `model_fields`. Adapters use these tuples to generate OpenAPI schemas and MCP inputSchemas without any manual configuration.

- **Base adapter infrastructure (`BaseAdapter`, `BaseRouteRecord`).** `BaseAdapter[R]` is an abstract generic class providing the fluent registration pattern (`_add_route` returns `self`) and abstract `build()` method. `BaseRouteRecord` is an abstract frozen dataclass storing route configuration with automatic extraction of `params_type` and `result_type` from `BaseAction[P, R]` generic parameters via `extract_action_types()`. Mapper invariants are enforced at creation time: `params_mapper` is required when `request_model` differs from `params_type`, and `response_mapper` is required when `response_model` differs from `result_type`. BaseRouteRecord cannot be instantiated directly — only concrete subclasses.

- **FastAPI adapter (`FastApiAdapter`).** Transforms Actions into HTTP endpoints. Protocol methods `post()`, `get()`, `put()`, `delete()`, `patch()` register routes with fluent chaining. `build()` creates a `FastAPI` application with automatic OpenAPI documentation generated from Pydantic Field descriptions, constraints, and examples. Three endpoint generation strategies handle body-based methods (POST/PUT/PATCH), query-based methods (GET/DELETE with path and query parameters), and empty-params methods. Exception handlers map `AuthorizationError` to HTTP 403, `ValidationFieldError` to HTTP 422, and unhandled exceptions to HTTP 500. A `GET /health` endpoint is added automatically.

- **MCP adapter (`McpAdapter`).** Transforms Actions into MCP tools for AI agents (Claude, ChatGPT, Cursor). The `tool()` method registers individual tools; `register_all()` automatically registers all Actions from the coordinator using snake_case names (e.g., `CreateOrderAction` → `create_order`). `build()` creates an MCP server with `inputSchema` auto-generated from Pydantic models and descriptions from `@meta`. Error mapping returns `PERMISSION_DENIED`, `INVALID_PARAMS`, or `INTERNAL_ERROR` as text content. A `system://graph` resource exposes the full system architecture as JSON with nodes (actions, domains, dependencies) and edges (depends, belongs_to, connection).

- **Mandatory `auth_coordinator` in all adapters.** The `auth_coordinator` parameter in `BaseAdapter` and all concrete adapters is a required positional argument. Passing `None` raises `TypeError` with a clear message suggesting `NoAuthCoordinator()` for open APIs. `NoAuthCoordinator` implements the same interface as `AuthCoordinator` — an async `process()` method returning `Context` — but always returns an anonymous context with `user_id=None` and empty roles. This ensures developers cannot accidentally forget authentication; they must explicitly declare the absence of it.

- **Fluent chain API for adapters.** All protocol methods (`post`, `get`, `put`, `delete`, `patch`, `tool`) return `self`, enabling chained registration: `app = adapter.post("/a", A).get("/b", B).build()`. The `_add_route()` method in `BaseAdapter` returns `Self` to support this pattern.

- **Unified example service (`fastapi_mcp_services`).** A single example package demonstrates the same three Actions (PingAction, CreateOrderAction, GetOrderAction) served simultaneously via FastAPI HTTP endpoints and MCP tools. Shared infrastructure (GateCoordinator, ActionProductMachine, NoAuthCoordinator) is defined once in `infrastructure.py`. Actions use nested Params/Result classes with forward references. Domains (OrdersDomain, SystemDomain) group actions by business area.

## [0.6.0] – 2026-03-28

### Added

- **`metadata` subpackage for structured metadata assembly.** Extracted `MetadataBuilder` from monolithic `core/metadata_builder.py` into a dedicated subpackage `action_machine/metadata/` with four focused modules. `builder.py` contains the `MetadataBuilder` class with a single public method `build(cls)` serving as the only entry point. `collectors.py` provides eight collector functions that read temporary decorator attributes from classes and methods — roles, dependencies, connections, aspects, checkers, subscriptions, sensitive fields, and dependency bound types. `validators.py` contains structural validation functions enforcing invariants that span multiple decorators, such as at most one summary aspect, summary must be declared last, and checkers must reference existing aspects. `cleanup.py` provides `cleanup_temporary_attributes()` for explicit removal of decorator artifacts when needed.

- **Idempotent metadata building.** `MetadataBuilder.build()` no longer auto-cleans temporary attributes from classes. Classes defined at module level are shared across tests and multiple `GateCoordinator` instances, so auto-cleaning caused data loss on subsequent builds. The builder is now fully idempotent — repeated calls on the same class return equivalent `ClassMetadata` objects. Explicit cleanup remains available via `cleanup_temporary_attributes()` for special scenarios.

- **Comprehensive `_extract_bound` test coverage.** Added exhaustive tests for `DependencyIntent` generic bound type extraction across all inheritance scenarios: explicit bound specification, missing bound fallback to `object`, three-level and four-level inheritance chains, multiple inheritance with mixins, `TypeVar` fallback, bound override in child classes, and diamond inheritance patterns.

## [0.5.0] – 2026-03-21

### Added

- **Intent-based aspect architecture (`AspectIntent`).** Introduced `AspectIntent` as a marker mixin for classes that support `@regular_aspect` and `@summary_aspect` decorators. Decorators write `_new_aspect_meta` metadata directly to methods. `MetadataBuilder` scans MRO to collect aspects into `ClassMetadata.aspects`. This replaces the previous magic-based aspect collection with an explicit, type-safe system where aspects are discovered through decorator metadata rather than method name conventions.

- **`ToolsBox` — unified container for aspect tools.** A single object passed to every aspect as the `box` parameter, replacing the previous separate `deps` and `log` parameters. Provides `resolve(cls)` for dependency injection (checking external resources first, then the factory), `info/warning/error/debug` for logging with automatic scope enrichment (machine, mode, action, aspect), and `run(action_class, params, connections)` for launching child actions with automatic connection wrapping to prevent nested transaction control. Reduces aspect parameter count from 5 to 4: `(params, state, box, connections)`.

- **Explicit nesting level tracking.** Removed the global `_nest_level` field from `ActionProductMachine`. Nesting depth is now passed explicitly as `nested_level` through `_run_internal` and stored inside `ToolsBox`. Each child action increments the level, and the value is accessible via `box.nested_level`. This eliminates shared mutable state between concurrent requests and makes the nesting depth available to logging and plugins.

- **`ActionTestMachine` external resource injection.** The test machine now accepts prepared mocks as `resources` in `_run_internal`, making them available throughout the execution pipeline including child actions. When `ToolsBox.resolve()` is called, it checks `resources` first (returning the mock) before falling back to the dependency factory.

- **`RuntimeInfo` (renamed from `EnvironmentInfo`).** The context component storing runtime information (hostname, service name, version, container ID) is now named `RuntimeInfo` to better reflect its purpose. The context attribute is `context.runtime` instead of the previous `context.environment`.

## [0.4.] – 2026-03-19

### Added

- **`debug()` function for object introspection in log templates.** Returns a formatted multi-line string listing all public fields and properties of any object, including their types and values. For properties decorated with `@sensitive`, the masking configuration is shown. Output is non-recursive by default (`max_depth=1`) to avoid cluttering logs — to inspect nested objects, call `debug` on the nested attribute directly. Available inside `iif` expressions: `{iif(1==1; debug(obj); '')}`.

- **`exists()` function for safe variable presence checks.** `exists('variable.name')` returns `True` if the variable is defined in the current evaluation context, `False` otherwise. Useful for conditional logging when a variable may not be present: `{iif(exists('var.user'); debug(var.user); 'No user')}`. Works both inside `iif` conditions and as a standalone expression evaluating to the string `"True"` or `"False"`.

- **Color filters in log templates.** ANSI colors can be applied to any substituted value using pipe syntax outside `iif` (`{%var.amount|red}`) or color functions inside `iif` (`red('text')`). Supports foreground colors (`red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `grey`, `orange` and bright variants), background colors (prefixed with `bg_`), and combinations (`{%var.text|red_on_blue}`). The coordinator strips ANSI codes for loggers that declare `supports_colors=False`.

- **`@sensitive` decorator for data masking in logs.** Applied to property getters, it causes the value to be partially masked when substituted in log templates. Configurable via `max_chars` (visible characters from start), `char` (replacement character), and `max_percent` (maximum visible percentage). Example: `@sensitive(max_chars=3)` on an email property makes `{%context.user.email}` output `max*****` instead of the full address.

- **Strict underscore rule in log templates.** Any template variable whose last path segment starts with underscore raises `LogTemplateError` immediately. This prevents accidental logging of private or protected fields. Developers must expose data through public properties if it needs to appear in logs.

- **Asynchronous plugin initialization.** `Plugin.get_initial_state()` is now an `async` method, allowing plugins to perform I/O operations (database queries, API calls) during state initialization without blocking the event loop. The `PluginCoordinator` awaits each plugin's initialization directly instead of using `run_in_executor`.

- **Context as a per-request parameter.** `context` is now passed directly to `machine.run(context, action, params, connections)` instead of being stored in the machine constructor. This reflects the architectural reality that the machine is a long-lived singleton while each request carries its own context containing user identity, request metadata, and runtime information. All internal methods receive `context` as an explicit argument.

## [0.3.0] – 2026-03-19

### Added

- **Cross-cutting logging via `ScopedLogger`.** Every aspect now receives a `log` parameter — a `ScopedLogger` instance that automatically enriches log messages with execution context. The scope includes `machine` (machine class name), `mode` (execution mode), `action` (full action class name), and `aspect` (method name). Logging level is added automatically as the `level` key in the `var` namespace. User data is passed via `**kwargs` and appears in `var`. Templates can reference all scope fields: `[{%scope.machine}.{%scope.action}] Processing {%var.amount}`.

- **`mode` parameter in machine constructors.** `ActionProductMachine` requires a mandatory non-empty string `mode` (e.g., `"production"`, `"staging"`). `ActionTestMachine` defaults to `mode="test"`. The mode value is included in every `LogScope`, enabling filtering of logs by environment and distinguishing production from test output.

- **Level-based coloring in `ConsoleLogger`.** Messages are automatically colored based on logging level: `info` — green, `warning` — yellow, `error` — red, `debug` — gray. The level is extracted from the `var["level"]` field set by `ScopedLogger`. Unresolved variable markers are colored red for immediate visibility.

## [0.2.5] – 2026-03-18

### Added

- **PEP 8 file naming convention.** All 18 source files renamed from PascalCase to snake_case (`AuthCoordinator.py` → `auth_coordinator.py`, `ConsoleLogger.py` → `console_logger.py`, etc.). This resolves ruff N999 errors and aligns the project with Python community standards.

- **Centralized linter configuration.** All ruff, pylint, and mypy settings consolidated in `pyproject.toml` with documented reasons for each disabled rule. Added `lint-fix` and `pre-commit` taskipy commands for automatic formatting. Achieved pylint 10.00/10, zero mypy errors, zero vulture warnings.

## [0.2.0] – 2026-03-17

### Added

- **Conditional logic in log templates (`iif`).** Added `{iif(condition; true_value; false_value)}` construct for dynamic text in log messages. Conditions are evaluated safely via the `simpleeval` library — no access to file system or network. Supports comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`), logical operators (`and`, `or`, `not`), arithmetic (`+`, `-`, `*`, `/`), and built-in functions (`len`, `upper`, `lower`, `format_number`). Variables from all five namespaces are substituted as literals before evaluation, and invalid expressions raise `LogTemplateError` immediately.

- **`VariableSubstitutor` — extracted substitution engine.** All variable resolution and `iif` processing logic moved from `LogCoordinator` into a dedicated `VariableSubstitutor` class. The coordinator now only delegates substitution and broadcasts results to loggers. Supports five namespaces: `{%var.*}`, `{%context.*}`, `{%params.*}`, `{%state.*}`, `{%scope.*}`. Each namespace resolves through dot-path traversal supporting nested objects via `ReadableMixin`, plain dictionaries, and generic `getattr` fallback.

- **`PluginCoordinator` — extracted plugin management.** Plugin lifecycle management (state initialization, handler discovery, concurrent execution) moved from `ActionProductMachine` into a separate stateless `PluginCoordinator`. The coordinator creates isolated `PluginRunContext` for each `run()` call, ensuring complete state isolation between requests. Supports two execution strategies: parallel (`asyncio.gather`) when all handlers have `ignore_exceptions=True`, and sequential when any handler requires strict error propagation.

- **Connection validation chain.** The monolithic `_check_connections` method in `ActionProductMachine` decomposed into four focused validators, each checking one invariant: no declarations but connections passed, declarations but no connections, extra keys, and missing keys. A fifth validator checks that each value is an instance of `BaseResourceManager`. The main method calls validators in sequence with clear error messages.

## [0.1.5] – 2026-03-16

### Added

- **Unified data access protocols (`ReadableDataProtocol`, `WritableDataProtocol`).** Runtime-checkable protocols defining dict-like interfaces for reading (`__getitem__`, `get`, `keys`, `values`, `items`, `__contains__`) and writing (`__setitem__`). Any object implementing these methods can serve as `Params`, `Result`, or plugin state, enabling the use of TypedDict, Pydantic models, and custom classes without framework-specific base classes.

- **`ReadableMixin` and `WritableMixin`.** Mixins that automatically implement the data protocols via `getattr`/`setattr`/`vars()`. Adding `ReadableMixin` to any class gives it dict-like read access; adding `WritableMixin` gives write access with optional key validation via `write(key, value, allowed_keys)`. Used by `BaseParams`, `BaseResult`, `BaseState`, `Context`, `UserInfo`, `RequestInfo`, `RuntimeInfo`.

- **`resolve()` method for dot-path navigation.** `ReadableMixin` provides `resolve("user.roles")` for traversing nested objects through a chain of keys separated by dots. Supports three navigation strategies: `ReadableMixin` objects (via `__getitem__`), plain dictionaries (via key access), and generic objects (via `getattr`). Results are cached lazily in `_resolve_cache`, compatible with frozen Pydantic models via `object.__setattr__`.

- **Asynchronous authentication pipeline.** `CredentialExtractor`, `Authenticator`, `ContextAssembler`, and `AuthCoordinator` — all methods are `async def`, enabling I/O operations (token verification, database lookups) without blocking the event loop. `AuthCoordinator.process()` orchestrates the three-step pipeline: extract credentials, authenticate user, assemble request metadata into `Context`.

- **Dict-like access for context components.** `UserInfo`, `RequestInfo`, and `RuntimeInfo` inherit `ReadableMixin`, enabling access as `user["user_id"]`, `request["trace_id"]`, `runtime["hostname"]` in addition to attribute access. This unifies data access patterns across plugins, logging templates, and business logic.

## [0.1.0] – 2026-03-15

### Added

- **Action-Oriented Architecture (AOA) core.** Actions are atomic business operations consisting of a linear sequence of aspects (processing steps). Each action is a class inheriting `BaseAction[P, R]` where `P` is the params type and `R` is the result type. Aspects are async methods decorated with `@regular_aspect` (intermediate steps returning dict) and `@summary_aspect` (final step returning Result). The machine executes aspects sequentially, merging intermediate results into shared state.

- **Declarative dependency injection (`@depends`).** Actions declare dependencies on external services via class-level decorators: `@depends(PaymentService)`. Dependencies are resolved at runtime through `DependencyFactory` — each `resolve()` call creates a new instance via the factory function or default constructor. Singleton pattern is supported through lambda closures: `@depends(Service, factory=lambda: shared_instance)`. A generic bound `DependencyIntent[T]` restricts which types are allowed as dependencies.

- **Connection management (`@connection`).** Actions declare required resource managers (database connections, caches, queues) via `@connection(PostgresManager, key="db")`. The machine validates that passed connections exactly match declared keys — extra keys, missing keys, and non-`BaseResourceManager` values are rejected with descriptive errors. `WrapperSqlConnectionManager` wraps connections passed to child actions, preventing nested transaction control (open/commit/rollback) while allowing query execution.

- **`ActionProductMachine` — production execution engine.** Fully async machine that orchestrates action execution: role checking via `@CheckRoles`, connection validation, dependency factory creation via `GateCoordinator`, sequential aspect execution with checker validation, plugin event emission, and nested action support. Stateless between requests — all per-request data flows through explicit parameters.

- **`ActionTestMachine` — test execution engine with mocking.** Accepts a `mocks` dictionary mapping dependency types to mock values. Supports four mock formats: `MockAction` instances, `BaseAction` instances (executed through full pipeline), `BaseResult` instances (wrapped in `MockAction`), and callables (wrapped as `side_effect`). Provides `run_with_context()` returning both result and `PluginRunContext` for asserting plugin states in tests.

- **Plugin system (`Plugin`, `@on`, `PluginCoordinator`).** Plugins subscribe to machine events (`global_start`, `global_finish`, `before:{aspect}`, `after:{aspect}`) via `@on` decorators with regex-based action filtering. Each `run()` call creates an isolated `PluginRunContext` with per-plugin state initialized via `get_initial_state()`. Plugin handlers receive `(self, state, event, log)` and return updated state. `ignore_exceptions` controls whether handler errors propagate or are silently absorbed.

- **Role-based access control (`@CheckRoles`).** Mandatory decorator for every action. Supports four modes: `CheckRoles.NONE` (no authentication required), `CheckRoles.ANY` (any authenticated user), a single role string (`"admin"`), or a list of roles (`["admin", "manager"]`). The machine compares the role spec against `context.user.roles` and raises `AuthorizationError` on mismatch.

- **Result field checkers.** Validation decorators applied to aspect methods: `ResultStringChecker`, `ResultIntChecker`, `ResultFloatChecker`, `ResultBoolChecker`, `ResultDateChecker`, `ResultInstanceChecker`. Each checker validates field presence, type, and constraints (min/max length, value range, date format, instance type). Aspects returning non-empty dicts must have checkers for all returned fields — undeclared fields cause `ValidationFieldError`.

- **`GateCoordinator` — central metadata and graph registry.** Lazily builds and caches `ClassMetadata` for any class on first access. Recursively discovers dependencies and connections. Maintains a directed acyclic graph (rustworkx `PyDiGraph`) with nodes for actions, dependencies, connections, aspects, checkers, plugins, subscriptions, sensitive fields, roles, and domains. Detects cyclic dependencies via `is_directed_acyclic_graph()` after each edge addition.

- **Logging subsystem.** `LogCoordinator` broadcasts messages to registered `BaseLogger` instances. `ConsoleLogger` outputs to stdout with configurable colors and indentation. `VariableSubstitutor` resolves five namespaces (`var`, `state`, `params`, `context`, `scope`) with dot-path traversal. `ExpressionEvaluator` handles `{iif(condition; true; false)}` via `simpleeval`. `@sensitive` decorator masks property values in logs. Strict error policy: invalid templates raise `LogTemplateError` immediately.

- **Exception hierarchy.** `AuthorizationError` (role mismatch), `ValidationFieldError` (checker failure), `HandleError` (resource manager errors), `TransactionError` (base for connection errors), `ConnectionAlreadyOpenError`, `ConnectionNotOpenError`, `TransactionProhibitedError` (wrapper prevents nested transactions), `ConnectionValidationError` (key mismatch), `LogTemplateError` (invalid template syntax), `CyclicDependencyError` (graph cycle detected).