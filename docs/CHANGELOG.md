# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.9] – 2026-03-31

### Added

- **ScopedLogger in plugin handlers.** All plugin handlers (`@on` methods) now receive a fourth parameter `log` — a `ScopedLogger` instance bound to the plugin's scope. The scope contains fields `machine`, `mode`, `plugin` (plugin class name), `action` (full action class name), `event` (event name such as `global_finish` or `before:validate`), and `nest_level` (call nesting depth). This enables plugins to log with full execution context using all five template namespaces (`{%scope.plugin}`, `{%var.count}`, `{%context.user.id}`, etc.). The handler signature is `async def handler(self, state, event, log)` — all four parameters are mandatory.

- **Nest level in logging scope and templates.** The `nest_level` field is now included in the `LogScope` for both aspects and plugin handlers. Developers can reference it in log templates via `{%scope.nest_level}` to display the current call depth. Root actions have `nest_level=1`, first-level child actions called via `box.run()` have `nest_level=2`, and so on. This makes it easy to trace nested action execution in log output and distinguish between parent and child action logs.

- **Configurable indentation in ConsoleLogger.** `ConsoleLogger` now accepts `use_indent` (bool, default `True`) and `indent_size` (int, default `2`) parameters. When `use_indent=True`, each log line is prefixed with `nest_level * indent_size` spaces, creating a visual hierarchy of nested action calls. When `use_indent=False`, all lines are printed without indentation — useful for production environments where logs are sent to ELK/Loki and indentation interferes with parsing. The indent is calculated from the `nest_level` passed through the logging pipeline.

- **Business domains (`BaseDomain`).** Introduced the `action_machine.domain` package with `BaseDomain` — an abstract base class for declaring typed business domains. Each domain is a class with a mandatory `name: ClassVar[str]` attribute, validated at class creation time via `__init_subclass__`. Domains serve as typed markers for grouping actions and resources by business area. Unlike string-based identifiers, class-based domains provide IDE autocompletion, import-time error detection for typos, and refactoring support. Domains appear as dedicated nodes in the GateCoordinator graph with `belongs_to` edges from actions and resources.

- **`@meta` decorator for mandatory class descriptions.** Every Action (with aspects) and every ResourceManager must now have a `@meta(description="...", domain=...)` decorator. The `description` parameter is mandatory and must be a non-empty string. The `domain` parameter is optional and accepts a `BaseDomain` subclass. Two gate hosts enforce this requirement: `ActionMetaGateHost` (inherited by `BaseAction`) and `ResourceMetaGateHost` (inherited by `BaseResourceManager`). MetadataBuilder raises `TypeError` if `@meta` is missing. The description and domain are stored in `ClassMetadata.meta` as a frozen `MetaInfo` dataclass and are used by adapters for OpenAPI summaries and MCP tool descriptions.

- **Domain nodes and `belongs_to` edges in the coordinator graph.** When `@meta` specifies a `domain`, GateCoordinator creates a node of type `domain` and a `belongs_to` edge from the class to the domain. Domain nodes are idempotent — multiple actions in the same domain share a single node. Action and dependency node payloads are enriched with `description` and `domain` fields from `@meta`, making the graph self-documenting without requiring access to ClassMetadata.

- **Strict mode for GateCoordinator.** `GateCoordinator` now accepts a `strict: bool = False` parameter. When `strict=True`, the coordinator additionally validates that `domain` is specified in `@meta` for all Actions (with aspects) and ResourceManagers. If `domain=None` in strict mode, a `ValueError` is raised. The `description` field is always validated regardless of strict mode — it is an unconditional invariant. The coordinator is passed as a parameter to `ActionProductMachine`, not created internally, allowing easy configuration of strict mode for production deployments.

- **Pydantic-based `BaseParams` and `BaseResult`.** `BaseParams` now inherits from `pydantic.BaseModel` with `frozen=True`, providing immutable parameters with automatic type validation, constraints (`gt`, `min_length`, `pattern`), and JSON Schema generation via `model_json_schema()`. `BaseResult` inherits from `pydantic.BaseModel` with `extra="allow"`, supporting both declared fields and dynamic extra fields written through `WritableMixin`. Both classes retain full `ReadableMixin` compatibility (`resolve()`, `keys()`, `values()`, `items()`, `__getitem__`). `BaseState` remains a plain class — it is not converted to Pydantic because its fields are dynamic and determined at runtime.

- **`DescribedFieldsGateHost` for mandatory field descriptions.** A marker mixin inherited by `BaseParams` and `BaseResult`. MetadataBuilder validates that every Pydantic field in classes inheriting this mixin has a non-empty `description` in `Field(description="...")`. Fields without descriptions raise `TypeError` at metadata assembly time, ensuring that all API parameters and results are self-documented from the start.

- **`FieldDescriptionMeta` in `ClassMetadata`.** A new frozen dataclass capturing field-level metadata: `field_name`, `field_type`, `description`, `examples`, `constraints` (gt, ge, min_length, max_length, pattern, etc.), `required`, and `default`. ClassMetadata now includes `params_fields` and `result_fields` tuples, populated by collectors that extract generic parameters P and R from `BaseAction[P, R]` and read Pydantic `model_fields`. Adapters use these tuples to generate OpenAPI schemas and MCP inputSchemas without any manual configuration.

- **Base adapter infrastructure (`BaseAdapter`, `BaseRouteRecord`).** `BaseAdapter[R]` is an abstract generic class providing the fluent registration pattern (`_add_route` returns `self`) and abstract `build()` method. `BaseRouteRecord` is an abstract frozen dataclass storing route configuration with automatic extraction of `params_type` and `result_type` from `BaseAction[P, R]` generic parameters via `extract_action_types()`. Mapper invariants are enforced at creation time: `params_mapper` is required when `request_model` differs from `params_type`, and `response_mapper` is required when `response_model` differs from `result_type`. BaseRouteRecord cannot be instantiated directly — only concrete subclasses.

- **FastAPI adapter (`FastApiAdapter`).** Transforms Actions into HTTP endpoints. Protocol methods `post()`, `get()`, `put()`, `delete()`, `patch()` register routes with fluent chaining. `build()` creates a `FastAPI` application with automatic OpenAPI documentation generated from Pydantic Field descriptions, constraints, and examples. Three endpoint generation strategies handle body-based methods (POST/PUT/PATCH), query-based methods (GET/DELETE with path and query parameters), and empty-params methods. Exception handlers map `AuthorizationError` to HTTP 403, `ValidationFieldError` to HTTP 422, and unhandled exceptions to HTTP 500. A `GET /health` endpoint is added automatically.

- **MCP adapter (`McpAdapter`).** Transforms Actions into MCP tools for AI agents (Claude, ChatGPT, Cursor). The `tool()` method registers individual tools; `register_all()` automatically registers all Actions from the coordinator using snake_case names (e.g., `CreateOrderAction` → `create_order`). `build()` creates a `FastMCP` server with `inputSchema` auto-generated from Pydantic models and descriptions from `@meta`. Error mapping returns `PERMISSION_DENIED`, `INVALID_PARAMS`, or `INTERNAL_ERROR` as text content. A `system://graph` resource exposes the full system architecture as JSON with nodes (actions, domains, dependencies) and edges (depends, belongs_to, connection).

- **Mandatory `auth_coordinator` in all adapters.** The `auth_coordinator` parameter in `BaseAdapter` and all concrete adapters is a required positional argument. Passing `None` raises `TypeError` with a clear message suggesting `NoAuthCoordinator()` for open APIs. `NoAuthCoordinator` implements the same interface as `AuthCoordinator` — an async `process()` method returning `Context` — but always returns an anonymous context with `user_id=None` and empty roles. This ensures developers cannot accidentally forget authentication; they must explicitly declare the absence of it.

- **Fluent chain API for adapters.** All protocol methods (`post`, `get`, `put`, `delete`, `patch`, `tool`) return `self`, enabling chained registration: `app = adapter.post("/a", A).get("/b", B).build()`. The `_add_route()` method in `BaseAdapter` returns `Self` to support this pattern.

- **Unified example service (`fastapi_mcp_services`).** A single example package demonstrates the same three Actions (PingAction, CreateOrderAction, GetOrderAction) served simultaneously via FastAPI HTTP endpoints and MCP tools. Shared infrastructure (GateCoordinator, ActionProductMachine, NoAuthCoordinator) is defined once in `infrastructure.py`. Actions use nested Params/Result classes with forward references. Domains (OrdersDomain, SystemDomain) group actions by business area.

## [0.0.8] – 2026-03-28

### Added

- **`metadata` subpackage for structured metadata assembly.** Extracted `MetadataBuilder` from monolithic `core/metadata_builder.py` into a dedicated subpackage `action_machine/metadata/` with four focused modules. `builder.py` contains the `MetadataBuilder` class with a single public method `build(cls)` serving as the only entry point. `collectors.py` provides eight collector functions that read temporary decorator attributes from classes and methods — roles, dependencies, connections, aspects, checkers, subscriptions, sensitive fields, and dependency bound types. `validators.py` contains structural validation functions enforcing invariants that span multiple decorators, such as at most one summary aspect, summary must be declared last, and checkers must reference existing aspects. `cleanup.py` provides `cleanup_temporary_attributes()` for explicit removal of decorator artifacts when needed.

- **Idempotent metadata building.** `MetadataBuilder.build()` no longer auto-cleans temporary attributes from classes. Classes defined at module level are shared across tests and multiple `GateCoordinator` instances, so auto-cleaning caused data loss on subsequent builds. The builder is now fully idempotent — repeated calls on the same class return equivalent `ClassMetadata` objects. Explicit cleanup remains available via `cleanup_temporary_attributes()` for special scenarios.

- **Comprehensive `_extract_bound` test coverage.** Added exhaustive tests for `DependencyGateHost` generic bound type extraction across all inheritance scenarios: explicit bound specification, missing bound fallback to `object`, three-level and four-level inheritance chains, multiple inheritance with mixins, `TypeVar` fallback, bound override in child classes, and diamond inheritance patterns.

## [0.0.7] – 2026-03-21

### Added

- **Gate-based aspect architecture (`AspectGateHost`).** Introduced `AspectGateHost` as a marker mixin for classes that support `@regular_aspect` and `@summary_aspect` decorators. Decorators write `_new_aspect_meta` metadata directly to methods. `MetadataBuilder` scans MRO to collect aspects into `ClassMetadata.aspects`. This replaces the previous magic-based aspect collection with an explicit, type-safe system where aspects are discovered through decorator metadata rather than method name conventions.

- **`ToolsBox` — unified container for aspect tools.** A single object passed to every aspect as the `box` parameter, replacing the previous separate `deps` and `log` parameters. Provides `resolve(cls)` for dependency injection (checking external resources first, then the factory), `info/warning/error/debug` for logging with automatic scope enrichment (machine, mode, action, aspect), and `run(action_class, params, connections)` for launching child actions with automatic connection wrapping to prevent nested transaction control. Reduces aspect parameter count from 5 to 4: `(params, state, box, connections)`.

- **Explicit nesting level tracking.** Removed the global `_nest_level` field from `ActionProductMachine`. Nesting depth is now passed explicitly as `nested_level` through `_run_internal` and stored inside `ToolsBox`. Each child action increments the level, and the value is accessible via `box.nested_level`. This eliminates shared mutable state between concurrent requests and makes the nesting depth available to logging and plugins.

- **`ActionTestMachine` external resource injection.** The test machine now accepts prepared mocks as `resources` in `_run_internal`, making them available throughout the execution pipeline including child actions. When `ToolsBox.resolve()` is called, it checks `resources` first (returning the mock) before falling back to the dependency factory.

- **`RuntimeInfo` (renamed from `EnvironmentInfo`).** The context component storing runtime information (hostname, service name, version, container ID) is now named `RuntimeInfo` to better reflect its purpose. The context attribute is `context.runtime` instead of the previous `context.environment`.

## [0.0.6] – 2026-03-19

### Added

- **`debug()` function for object introspection in log templates.** Returns a formatted multi-line string listing all public fields and properties of any object, including their types and values. For properties decorated with `@sensitive`, the masking configuration is shown. Output is non-recursive by default (`max_depth=1`) to avoid cluttering logs — to inspect nested objects, call `debug` on the nested attribute directly. Available inside `iif` expressions: `{iif(1==1; debug(obj); '')}`.

- **`exists()` function for safe variable presence checks.** `exists('variable.name')` returns `True` if the variable is defined in the current evaluation context, `False` otherwise. Useful for conditional logging when a variable may not be present: `{iif(exists('var.user'); debug(var.user); 'No user')}`. Works both inside `iif` conditions and as a standalone expression evaluating to the string `"True"` or `"False"`.

- **Color filters in log templates.** ANSI colors can be applied to any substituted value using pipe syntax outside `iif` (`{%var.amount|red}`) or color functions inside `iif` (`red('text')`). Supports foreground colors (`red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `grey`, `orange` and bright variants), background colors (prefixed with `bg_`), and combinations (`{%var.text|red_on_blue}`). The coordinator strips ANSI codes for loggers that declare `supports_colors=False`.

- **`@sensitive` decorator for data masking in logs.** Applied to property getters, it causes the value to be partially masked when substituted in log templates. Configurable via `max_chars` (visible characters from start), `char` (replacement character), and `max_percent` (maximum visible percentage). Example: `@sensitive(max_chars=3)` on an email property makes `{%context.user.email}` output `max*****` instead of the full address.

- **Strict underscore rule in log templates.** Any template variable whose last path segment starts with underscore raises `LogTemplateError` immediately. This prevents accidental logging of private or protected fields. Developers must expose data through public properties if it needs to appear in logs.

- **Asynchronous plugin initialization.** `Plugin.get_initial_state()` is now an `async` method, allowing plugins to perform I/O operations (database queries, API calls) during state initialization without blocking the event loop. The `PluginCoordinator` awaits each plugin's initialization directly instead of using `run_in_executor`.

- **Context as a per-request parameter.** `context` is now passed directly to `machine.run(context, action, params, connections)` instead of being stored in the machine constructor. This reflects the architectural reality that the machine is a long-lived singleton while each request carries its own context containing user identity, request metadata, and runtime information. All internal methods receive `context` as an explicit argument.

## [0.0.5] – 2026-03-19

### Added

- **Cross-cutting logging via `ScopedLogger`.** Every aspect now receives a `log` parameter — a `ScopedLogger` instance that automatically enriches log messages with execution context. The scope includes `machine` (machine class name), `mode` (execution mode), `action` (full action class name), and `aspect` (method name). Logging level is added automatically as the `level` key in the `var` namespace. User data is passed via `**kwargs` and appears in `var`. Templates can reference all scope fields: `[{%scope.machine}.{%scope.action}] Processing {%var.amount}`.

- **`mode` parameter in machine constructors.** `ActionProductMachine` requires a mandatory non-empty string `mode` (e.g., `"production"`, `"staging"`). `ActionTestMachine` defaults to `mode="test"`. The mode value is included in every `LogScope`, enabling filtering of logs by environment and distinguishing production from test output.

- **Level-based coloring in `ConsoleLogger`.** Messages are automatically colored based on logging level: `info` — green, `warning` — yellow, `error` — red, `debug` — gray. The level is extracted from the `var["level"]` field set by `ScopedLogger`. Unresolved variable markers are colored red for immediate visibility.

## [0.0.4] – 2026-03-18

### Added

- **PEP 8 file naming convention.** All 18 source files renamed from PascalCase to snake_case (`AuthCoordinator.py` → `auth_coordinator.py`, `ConsoleLogger.py` → `console_logger.py`, etc.). This resolves ruff N999 errors and aligns the project with Python community standards.

- **Centralized linter configuration.** All ruff, pylint, and mypy settings consolidated in `pyproject.toml` with documented reasons for each disabled rule. Added `lint-fix` and `pre-commit` taskipy commands for automatic formatting. Achieved pylint 10.00/10, zero mypy errors, zero vulture warnings.

## [0.0.3] – 2026-03-17

### Added

- **Conditional logic in log templates (`iif`).** Added `{iif(condition; true_value; false_value)}` construct for dynamic text in log messages. Conditions are evaluated safely via the `simpleeval` library — no access to file system or network. Supports comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`), logical operators (`and`, `or`, `not`), arithmetic (`+`, `-`, `*`, `/`), and built-in functions (`len`, `upper`, `lower`, `format_number`). Variables from all five namespaces are substituted as literals before evaluation, and invalid expressions raise `LogTemplateError` immediately.

- **`VariableSubstitutor` — extracted substitution engine.** All variable resolution and `iif` processing logic moved from `LogCoordinator` into a dedicated `VariableSubstitutor` class. The coordinator now only delegates substitution and broadcasts results to loggers. Supports five namespaces: `{%var.*}`, `{%context.*}`, `{%params.*}`, `{%state.*}`, `{%scope.*}`. Each namespace resolves through dot-path traversal supporting nested objects via `ReadableMixin`, plain dictionaries, and generic `getattr` fallback.

- **`PluginCoordinator` — extracted plugin management.** Plugin lifecycle management (state initialization, handler discovery, concurrent execution) moved from `ActionProductMachine` into a separate stateless `PluginCoordinator`. The coordinator creates isolated `PluginRunContext` for each `run()` call, ensuring complete state isolation between requests. Supports two execution strategies: parallel (`asyncio.gather`) when all handlers have `ignore_exceptions=True`, and sequential when any handler requires strict error propagation.

- **Connection validation chain.** The monolithic `_check_connections` method in `ActionProductMachine` decomposed into four focused validators, each checking one invariant: no declarations but connections passed, declarations but no connections, extra keys, and missing keys. A fifth validator checks that each value is an instance of `BaseResourceManager`. The main method calls validators in sequence with clear error messages.

## [0.0.2] – 2026-03-16

### Added

- **Unified data access protocols (`ReadableDataProtocol`, `WritableDataProtocol`).** Runtime-checkable protocols defining dict-like interfaces for reading (`__getitem__`, `get`, `keys`, `values`, `items`, `__contains__`) and writing (`__setitem__`). Any object implementing these methods can serve as `Params`, `Result`, or plugin state, enabling the use of TypedDict, Pydantic models, and custom classes without framework-specific base classes.

- **`ReadableMixin` and `WritableMixin`.** Mixins that automatically implement the data protocols via `getattr`/`setattr`/`vars()`. Adding `ReadableMixin` to any class gives it dict-like read access; adding `WritableMixin` gives write access with optional key validation via `write(key, value, allowed_keys)`. Used by `BaseParams`, `BaseResult`, `BaseState`, `Context`, `UserInfo`, `RequestInfo`, `RuntimeInfo`.

- **`resolve()` method for dot-path navigation.** `ReadableMixin` provides `resolve("user.roles")` for traversing nested objects through a chain of keys separated by dots. Supports three navigation strategies: `ReadableMixin` objects (via `__getitem__`), plain dictionaries (via key access), and generic objects (via `getattr`). Results are cached lazily in `_resolve_cache`, compatible with frozen Pydantic models via `object.__setattr__`.

- **Asynchronous authentication pipeline.** `CredentialExtractor`, `Authenticator`, `ContextAssembler`, and `AuthCoordinator` — all methods are `async def`, enabling I/O operations (token verification, database lookups) without blocking the event loop. `AuthCoordinator.process()` orchestrates the three-step pipeline: extract credentials, authenticate user, assemble request metadata into `Context`.

- **Dict-like access for context components.** `UserInfo`, `RequestInfo`, and `RuntimeInfo` inherit `ReadableMixin`, enabling access as `user["user_id"]`, `request["trace_id"]`, `runtime["hostname"]` in addition to attribute access. This unifies data access patterns across plugins, logging templates, and business logic.

## [0.0.1] – 2026-03-15

### Added

- **Action-Oriented Architecture (AOA) core.** Actions are atomic business operations consisting of a linear sequence of aspects (processing steps). Each action is a class inheriting `BaseAction[P, R]` where `P` is the params type and `R` is the result type. Aspects are async methods decorated with `@regular_aspect` (intermediate steps returning dict) and `@summary_aspect` (final step returning Result). The machine executes aspects sequentially, merging intermediate results into shared state.

- **Declarative dependency injection (`@depends`).** Actions declare dependencies on external services via class-level decorators: `@depends(PaymentService)`. Dependencies are resolved at runtime through `DependencyFactory` — each `resolve()` call creates a new instance via the factory function or default constructor. Singleton pattern is supported through lambda closures: `@depends(Service, factory=lambda: shared_instance)`. A generic bound `DependencyGateHost[T]` restricts which types are allowed as dependencies.

- **Connection management (`@connection`).** Actions declare required resource managers (database connections, caches, queues) via `@connection(PostgresManager, key="db")`. The machine validates that passed connections exactly match declared keys — extra keys, missing keys, and non-`BaseResourceManager` values are rejected with descriptive errors. `WrapperConnectionManager` wraps connections passed to child actions, preventing nested transaction control (open/commit/rollback) while allowing query execution.

- **`ActionProductMachine` — production execution engine.** Fully async machine that orchestrates action execution: role checking via `@CheckRoles`, connection validation, dependency factory creation via `GateCoordinator`, sequential aspect execution with checker validation, plugin event emission, and nested action support. Stateless between requests — all per-request data flows through explicit parameters.

- **`ActionTestMachine` — test execution engine with mocking.** Accepts a `mocks` dictionary mapping dependency types to mock values. Supports four mock formats: `MockAction` instances, `BaseAction` instances (executed through full pipeline), `BaseResult` instances (wrapped in `MockAction`), and callables (wrapped as `side_effect`). Provides `run_with_context()` returning both result and `PluginRunContext` for asserting plugin states in tests.

- **Plugin system (`Plugin`, `@on`, `PluginCoordinator`).** Plugins subscribe to machine events (`global_start`, `global_finish`, `before:{aspect}`, `after:{aspect}`) via `@on` decorators with regex-based action filtering. Each `run()` call creates an isolated `PluginRunContext` with per-plugin state initialized via `get_initial_state()`. Plugin handlers receive `(self, state, event, log)` and return updated state. `ignore_exceptions` controls whether handler errors propagate or are silently absorbed.

- **Role-based access control (`@CheckRoles`).** Mandatory decorator for every action. Supports four modes: `CheckRoles.NONE` (no authentication required), `CheckRoles.ANY` (any authenticated user), a single role string (`"admin"`), or a list of roles (`["admin", "manager"]`). The machine compares the role spec against `context.user.roles` and raises `AuthorizationError` on mismatch.

- **Result field checkers.** Validation decorators applied to aspect methods: `ResultStringChecker`, `ResultIntChecker`, `ResultFloatChecker`, `ResultBoolChecker`, `ResultDateChecker`, `ResultInstanceChecker`. Each checker validates field presence, type, and constraints (min/max length, value range, date format, instance type). Aspects returning non-empty dicts must have checkers for all returned fields — undeclared fields cause `ValidationFieldError`.

- **`GateCoordinator` — central metadata and graph registry.** Lazily builds and caches `ClassMetadata` for any class on first access. Recursively discovers dependencies and connections. Maintains a directed acyclic graph (rustworkx `PyDiGraph`) with nodes for actions, dependencies, connections, aspects, checkers, plugins, subscriptions, sensitive fields, roles, and domains. Detects cyclic dependencies via `is_directed_acyclic_graph()` after each edge addition.

- **Logging subsystem.** `LogCoordinator` broadcasts messages to registered `BaseLogger` instances. `ConsoleLogger` outputs to stdout with configurable colors and indentation. `VariableSubstitutor` resolves five namespaces (`var`, `state`, `params`, `context`, `scope`) with dot-path traversal. `ExpressionEvaluator` handles `{iif(condition; true; false)}` via `simpleeval`. `@sensitive` decorator masks property values in logs. Strict error policy: invalid templates raise `LogTemplateError` immediately.

- **Exception hierarchy.** `AuthorizationError` (role mismatch), `ValidationFieldError` (checker failure), `HandleError` (resource manager errors), `TransactionError` (base for connection errors), `ConnectionAlreadyOpenError`, `ConnectionNotOpenError`, `TransactionProhibitedError` (wrapper prevents nested transactions), `ConnectionValidationError` (key mismatch), `LogTemplateError` (invalid template syntax), `CyclicDependencyError` (graph cycle detected).