# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [0.0.7] – 2026-03-28

### Added
- **`metadata` subpackage** – extracted `MetadataBuilder` from monolithic `core/metadata_builder.py` into a dedicated subpackage `action_machine/metadata/` with four focused modules:
  - `builder.py` – `MetadataBuilder` class with the single public method `build(cls)`, serving as the only entry point for metadata assembly.
  - `collectors.py` – eight collector functions that read temporary decorator attributes from classes and methods: roles, dependencies, connections, aspects, checkers, subscriptions, sensitive fields, and dependency bound types.
  - `validators.py` – structural validation functions enforcing invariants that cannot be checked by individual decorators (e.g., at most one summary aspect, summary must be last, checkers must be attached to existing aspects).
  - `cleanup.py` – `cleanup_temporary_attributes()` function for explicit removal of decorator artifacts from classes and methods, available for special scenarios such as finalization or memory optimization.
- **`_extract_bound` test coverage** – comprehensive tests for `DependencyGateHost` bound type extraction across multiple inheritance scenarios: explicit bound, no bound, three-level inheritance, multiple inheritance with mixins, `TypeVar` fallback to `object`, bound override in child classes, and diamond inheritance.
- **New test files** –
  - `tests/metadata/test_builder_integration.py` – integration tests for the new builder, including import verification, idempotency, validation, and coordinator compatibility.
  - `tests/metadata/test_cleanup.py` – tests for explicit cleanup function covering class-level and method-level attributes, inheritance isolation, idempotency, and confirmation that `build()` does not auto-clean.
  - `tests/metadata/test_extract_bound.py` – exhaustive tests for generic bound extraction from `DependencyGateHost[T]`.
  - `tests/metadata/test_gate_coordinator_graph.py` – graph tests relocated to metadata test directory.
  - `tests/metadata/test_metadata_and_coordinator.py` – updated tests with new import paths.

### Changed
- **`MetadataBuilder.build()` no longer auto-cleans temporary attributes** – classes defined at module level are shared across tests and multiple `GateCoordinator` instances. Auto-cleaning after the first `build()` caused subsequent builds to return empty metadata when tests ran in arbitrary order. `build()` is now idempotent: repeated calls on the same class return equivalent `ClassMetadata` objects. Cleanup is available as an explicit opt-in via `cleanup_temporary_attributes()`.
- **All imports updated** – `gate_coordinator.py` and all test files now import `MetadataBuilder` from `action_machine.metadata` instead of the deleted `action_machine.core.metadata_builder`.
- **`core/__init__.py` updated** – documents that `MetadataBuilder` is no longer part of the `core` package and must be imported from `action_machine.metadata`.
- **Type annotations in `collectors.py`** – all return types now use explicit generic parameters (`dict[str, Any]`, `list[Any]`) instead of bare `dict` and `list`, resolving five mypy `type-arg` errors.

### Removed
- **`src/action_machine/core/metadata_builder.py`** – deleted entirely. All functionality moved to the `action_machine/metadata/` subpackage. Any remaining `__pycache__` artifacts from the old module should be cleared.

### Fixed
- **Test isolation for module-level classes** – tests that use `@CheckRoles`, `@connection`, `@depends`, and other decorators on module-level classes now work correctly regardless of test execution order. Previously, cleanup removed `_role_info` and `_connection_info` after the first `GateCoordinator` registered a class, causing all subsequent coordinators to see empty metadata for that class.
- **`FakeDependencyInfo` in tests** – added missing `factory` field to test helper dataclass, resolving `AttributeError: 'FakeDependencyInfo' object has no attribute 'factory'` when `DependencyFactory.resolve()` accessed the field.

### Technical Notes
- **757 tests pass** after the refactoring, with no functionality broken.
- All checks clean: ruff, pylint (10.00/10), mypy, vulture, radon complexity (average A, 2.34), radon maintainability (all files grade A).
- The `cleanup.py` module and `cleanup_temporary_attributes()` function remain in the codebase for potential future use but are not called automatically by the framework.

## [0.0.6] – 2026-03-21

### Added
- **New aspect architecture based on gates** – introduced `AspectGate` and `AspectGateHost` for explicit, type‑safe management of aspects.  
  - `AspectGate` stores regular and summary aspects, providing methods to register, unregister, and retrieve them.  
  - `AspectGateHost` is a mixin that attaches an aspect gate to any class, automatically collects methods decorated with `@regular_aspect` and `@summary_aspect` during class creation, and supports inheritance (copies aspects from parent classes).  
  - The new system is completely independent from the old magic aspect system, allowing gradual migration of actions.
- **New aspect decorators** – `@regular_aspect(description)` and `@summary_aspect(description)` now replace the deprecated `@aspect_old` and `@summary_aspect_old`.  
  These decorators only add temporary metadata; registration is handled centrally by `AspectGateHost`.
- **Copy‑on‑write for aspect gates** – each instance of an action can safely modify its own set of aspects (add, remove, replace summary) without affecting other instances or the class‑level gate.  
  This is implemented by lazily copying the class gate when the first modification is made.
- **CheckerGate now supports multiple checkers per field** – the gate stores lists of checkers for each field, preserving registration order. This enables combining several validation rules (e.g., `StringFieldChecker` + `InstanceOfChecker`) on the same field.  
  - `get_class_checkers(field_name)` returns a list of all class‑level checkers for the field.  
  - `get_method_checkers(method, field_name)` returns a list of all method‑level checkers for the field.  
  - The general principle for all gates has been documented: when multiple components can be attached to the same key, they are stored as lists to preserve order.
- **`ToolsBox` class** – a new container that bundles all tools an aspect may need:  
  - `resolve(cls)` – obtains dependencies, respecting both external resources and the dependency factory.  
  - `info`, `warning`, `error`, `debug` – logging methods that automatically add the correct scope (machine, mode, action, aspect) and nesting level.  
  - `run(action_class, params, connections)` – runs a child action, automatically wrapping connections to prevent nested transaction control.  
  - `nested_level` property gives access to the current nesting depth.
- **`box` parameter in aspects** – all aspects now receive a single `box: ToolsBox` instead of separate `deps` and `log` parameters. This reduces the number of aspect parameters from 5 to 4 (`params, state, box, connections`).
- **Explicit nesting level handling** – removed the global `_nest_level` from `ActionProductMachine`. Nesting level is now passed explicitly as `nested_level` through `_run_internal` and is stored inside `ToolsBox`.
- **`ActionTestMachine` support for external resources** – the test machine now accepts a `resources` dictionary in its `run` method (via `_run_internal`), allowing tests to inject mocks directly.
- **`RuntimeInfo` renamed from `EnvironmentInfo`** – the class and all references have been renamed to better reflect its purpose (information about the runtime environment, not the “environment” concept).  
  The attribute `context.environment` is replaced with `context.runtime`.

### Changed
- **Aspect signatures** – all aspects (both regular and summary) now have the signature:  
  `async def method(params, state, box, connections)`.
- **BaseAction now inherits `AspectGateHost`** – every action gains the new aspect gate infrastructure while remaining compatible with existing code.
- **DependencyFactory improvements** –  
  - Method `get()` renamed to `resolve()` for consistency.  
  - Removed `machine` parameter from constructor.  
  - Removed `_external_resources` – external resources are now provided directly to `ToolsBox` and take precedence in `resolve()`.  
  - Removed `run_action()` – child action execution is now handled by `ToolsBox.run()`.
- **`ActionProductMachine` internal changes** –  
  - Public `run()` no longer accepts `resources` (they are passed implicitly via the dependency factory).  
  - Added private `_run_internal(context, action, params, resources, connections, nested_level)`.  
  - Removed `_nest_level` field.  
  - Removed old aspect collection methods (`_collect_aspects`, `_get_aspects`, `_process_method_for_aspect`, `_aspect_cache`).  
  - `_call_aspect` and `_execute_regular_aspects` now receive `box` instead of `factory` and `log`.
- **`ActionTestMachine`** – its `run` method now passes the prepared mocks as `resources` to `_run_internal`, ensuring mocks are available during child action execution.
- **Logging** – the `ActionBoundLogger` is now created only once per `_run_internal` call and reused for all aspects, improving performance.  
  Aspect‑specific loggers are still created for each aspect but now inherit the correct nesting level from the parent box.
- **`Context` components** – `EnvironmentInfo` is renamed to `RuntimeInfo`. All tests and references have been updated.

### Removed
- **Old aspect decorators** – `@aspect_old` and `@summary_aspect_old` are removed from `Core/AspectMethod.py`.  
  The new `@regular_aspect` and `@summary_aspect` from the `aspects` package must be used instead.
- **Aspect collection logic** – the old magic methods `_collect_aspects`, `_get_aspects`, `_process_method_for_aspect`, and the `_aspect_cache` dictionary have been removed from `ActionProductMachine`.
- **`_external_resources` and `machine` parameter** from `DependencyFactory` – these are no longer needed as external resources are passed through `ToolsBox`.
- **`DependencyFactory.run_action()`** – replaced by `ToolsBox.run()`.
- **`context.environment` attribute** – replaced by `context.runtime`.
- **Global `_nest_level`** – removed from `ActionProductMachine`; nesting is now tracked per call via explicit argument.

### Fixed
- **Type‑safety in `ToolsBox.run`** – added a `cast(R, result)` to satisfy mypy, as the return type from `__run_child` is `BaseResult`, but the method is generic.
- **All tests** – updated to use the new aspect signatures, `ToolsBox`, and renamed `RuntimeInfo`.  
  Tests that previously relied on old aspect decorators or the removed `_nest_level` have been rewritten.  
  **549 tests pass** after the refactoring, with no functionality broken.

### Security
- No direct security changes in this release, but the cleaner separation of concerns and explicit resource handling reduces the risk of accidental mis‑use in tests and production code.

## [0.0.5] - 2026-03-19

### Added
- **`debug()` function for object introspection** – now you can inspect any object in log templates by using `{iif(1==1; debug(obj); '')}` (must be wrapped in `iif`).  
  The function returns a formatted string listing all public fields and properties of the object, including their types. For properties decorated with `@sensitive`, the masking configuration (`max_chars`, `char`, `max_percent`) is shown.  
  The output is **non‑recursive by default** (`max_depth=1`), showing only immediate fields. To inspect nested objects, call `debug` on the nested attribute directly.  
  Example output:
  ```
  UserInfo:
    user_id: str = "bystrov.maxim"
    roles: list[str] = ["user", "admin"]
    extra: dict = {"org": "acme"}
    email: str (sensitive: max_chars=3, char='*', max_percent=50) = "max*****"
  ```
- **`exists()` function for safe variable presence checks** – `exists('variable.name')` returns `True` if the variable is defined in the current evaluation context, otherwise `False`.  
  It can be used both inside `iif` conditions and as a standalone expression (e.g., `{iif(exists('var.user'); debug(var.user); 'No user')}`).  
  When used alone, it evaluates to the string `"True"` or `"False"`.
- **Removed truncation limit in `_format_value`** – values are now displayed fully without any length restrictions, making it easier to debug complex structures. (Previously, values longer than 60 characters were truncated.)
- **English‑only error messages** – all exception messages and user‑facing strings have been translated to English. This ensures consistency and aligns with the project’s internationalization goals.
- **Asynchronous plugin initialization** – `Plugin.get_initial_state()` is now an `async` method. This eliminates the need for `run_in_executor` and allows plugins to perform async I/O during state initialization.
- **Context as a per‑request parameter** – `context` is now passed directly to the `run()` method of all action machines (`BaseActionMachine`, `ActionProductMachine`, `ActionTestMachine`) instead of being stored in the constructor.  
  This change reflects the fact that the machine is a long‑lived singleton, while each request carries its own context (user, request, environment).  
  All internal methods that previously accessed `self._context` now receive `context` as an explicit argument.
- **Color filters in log templates** – now you can apply ANSI colors to any substituted value using the syntax:
  - `{%var.amount|red}` – outside `iif`
  - `red('text')` – inside `iif` (color functions)
  - Background only: `{%var.text|bg_red}`
  - Foreground + background: `{%var.text|red_on_blue}`
  - All common colors are supported: `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `grey`, `orange`, and their bright variants, as well as background versions (prefixed with `bg_`). Any combination of foreground and background is possible via `foreground_on_background`.
- **Sensitive data masking** – new decorator `@sensitive` for property getters. When applied, the value is partially masked in logs according to parameters (`max_chars`, `char`, `max_percent`).  
  Example:
  ```python
  @property
  @sensitive(max_chars=3)
  def email(self):
      return self._email
  ```
  In a template, `{%context.user.email}` will output something like `max*****`.
- **Strict underscore rule** – any template variable whose last segment starts with an underscore (`_` or `__`) now raises `LogTemplateError`. This prevents accidental logging of protected/private fields. Developers must explicitly expose data via public properties.
- **ConsoleLogger now supports two modes** – `use_colors=True` (default) preserves ANSI codes; `use_colors=False` strips them (handled by the coordinator).
- **BaseLogger improvements** – added `supports_colors` property and `strip_ansi_codes` static method for ANSI removal.
- **Integration test** (`test_full_flow.py`) now demonstrates all new features: scope variables, colored variables and literals, `iif` with colored branches, sensitive masking, `debug()` and `exists()`, and side‑by‑side output of color and plain loggers.
- **Unit tests** for color filters (`test_color_filters.py`), `debug()` (`test_debug_function.py`), and `exists()` (`test_exists_function.py`) covering all features and error conditions.

### Changed
- **Error messages for undefined variables** – when a variable is not found, the error message now includes the variable name (e.g., `Variable 'missing' not found in expression 'missing > 10'`) instead of the generic `Error evaluating expression`. This improves debuggability.
- **Plugin concurrency** – removed the `max_concurrent_handlers` parameter from `ActionProductMachine` and `PluginCoordinator`.  
  - Previously, plugin handlers were limited by an `asyncio.Semaphore` to prevent resource exhaustion.  
  - Since plugins typically perform independent I/O operations (e.g., writing to different databases, queues, or files), the semaphore introduced unnecessary serialization.  
  - Now all matching plugin handlers are executed **fully concurrently** via `asyncio.gather`, reducing overall execution time to that of the slowest handler.
- **All internal comments and docstrings** have been translated to English and updated to reflect the current implementation.
- **Plugin state initialization** – moved from `run_in_executor` to direct `await` of `get_initial_state()`, simplifying the code and making the coordinator fully asynchronous.
- **ActionProductMachine constructor** – removed the `context` parameter; the machine no longer holds request‑specific data.
- **ActionTestMachine constructor** – removed the `ctx` parameter (the test machine now only accepts `mocks`, `mode`, and `log_coordinator`).
- **BaseActionMachine.run() signature** – added mandatory first parameter `context: Context`. The same change applies to `sync_run()`.
- **DependencyFactory.run_action()** – now requires a `context` argument and passes it to the machine’s `run()` method.
- **All related tests** – updated to pass `context` where needed; fixtures and helper functions adjusted accordingly.
- **ConsoleLogger no longer adds automatic `[scope]` prefix** – users must now include scope variables explicitly in their templates (e.g., `[{%scope.machine}.{%scope.mode}.{%scope.action}.{%scope.aspect}]`).
- **VariableSubstitutor** completely rewritten to support color filters, underscore checks, marker‑based color post‑processing, and the new `debug()`/`exists()` functions.
- **LogCoordinator** now strips ANSI codes for loggers that do not support colors before passing the message.
- **ExpressionEvaluator** now includes `debug()` and `exists()` as safe built‑ins, allowing them to be used inside `iif`.

### Removed
- **Built‑in colorization from `ConsoleLogger`** – colors are now handled purely via template filters.
- **`max_concurrent_handlers`** – no longer accepted in constructors; related logic removed from `PluginCoordinator`.
- **`self._context` attribute** – completely eliminated from `ActionProductMachine` and `ActionTestMachine`.

### Fixed
- **Plugin state initialization** – now fully asynchronous (direct `await` instead of `run_in_executor`).
- **Exception messages** in `ExpressionEvaluator` and `VariableSubstitutor` are now consistently in English, fixing test expectations.
- **Test suite** – updated concurrency tests to verify that all handlers run in parallel (duration ~ max handler time). Removed obsolete tests that checked semaphore behavior.
- **Exception tests** – aligned with English error messages; all plugin exception tests now pass.
- **Type hints** – ensured all changes are compatible with strict `mypy` checks (no new issues introduced).
- **All 516 tests pass** after the refactoring; no functionality was broken.

### Security
- **Sensitive data masking** – sensitive fields can now be masked effectively using the `@sensitive` decorator.
- **Underscore rule** – access to names starting with underscore is forbidden in templates, reducing the risk of accidental data leaks.

### Deprecated
- Nothing


## [0.0.4] - 2026-03-19

### Added
- **Cross-cutting logging** – implemented the `idea_02` plan to introduce a bound logger into aspects.
  - **Problem:** Previously, logs lacked execution context (machine name, mode, action, aspect), making tracing and filtering difficult.
  - **Solution:** Added the `ActionBoundLogger` class, which is created for each aspect call and automatically adds the following fields to `LogScope`:
    - `machine` – machine class name.
    - `mode` – execution mode.
    - `action` – full action class name.
    - `aspect` – aspect method name.
  - Logging level (`info`, `warning`, `error`, `debug`) is passed via the `"level"` key in `var` (added automatically).
  - User data is passed only via `**kwargs` and ends up in `var`; system fields (except `level`) are not added.
- **Mandatory `log` parameter in aspects** – all aspects are now required to accept the sixth parameter `log: ActionBoundLogger`. Backward compatibility is not maintained (the core is not yet used in production, cleanliness is important).
- **`mode` parameter in machine constructors**:
  - `ActionProductMachine` now requires a mandatory non-empty string parameter `mode`.
  - `ActionTestMachine` defaults to `mode="test"`, but allows overriding.
  - `mode` is passed to `ActionBoundLogger` and ends up in `LogScope`.
- **Logging level support in `ConsoleLogger`**:
  - Added message coloring based on level: `info` — green, `warning` — yellow, `error` — red, `debug` — gray.
  - The unresolved variable marker `<none>` is colored red.
  - If no level is specified, `"info"` is used.
- **Tests for cross-cutting logging**:
  - `tests/logging/test_action_bound_logger.py` – checks logger creation, `emit` calls, `LogScope` formation, handling of user `kwargs`, and ignoring user-supplied `level`.
  - Extended `ActionProductMachine` tests to verify `log` is passed to aspects and `LogScope` correctness.
  - Extended `ActionTestMachine` tests to verify logger works with mocks.
  - Updated `test_console_logger.py` to verify level-based coloring.
- **Documentation** – added a detailed "Cross-cutting Logging" section to `README.md` with concepts, usage examples, and extension guidelines.

### Changed
- **`AspectMethod.__call__` signature** – added a sixth parameter `log`, making `log` mandatory in all aspects.
- **`ActionProductMachine._call_aspect`** – now always creates an `ActionBoundLogger` and passes it to the aspect method (no parameter existence check, as it is mandatory).
- **`LogCoordinator.emit`** – unchanged, but now called from `ActionBoundLogger` with empty instances of `BaseState` and `BaseParams` (instead of `{}` and `None`), matching expected types.
- **`ConsoleLogger.write`** – modified to extract the level from `var` and apply corresponding coloring.

### Fixed
- **Ignoring user-supplied `level`** – added `kwargs.pop("level", None)` in `ActionBoundLogger._emit` to prevent conflict between system and user levels (test `test_user_kwargs_override_nothing`).
- **Type checking (mypy)** – updated the `AspectMethod` protocol in `AspectMethod.py` to include the `log` parameter. Deleted mypy cache, error resolved.
- **Unsorted imports** – fixed all `I001` errors in the project using `ruff --fix`.
- **Removed unused import `BaseState` from `DependencyFactory.py`** (detected by ruff).

### Removed
- **Old aspect signature without `log`** – no longer supported.

## [0.0.3] - 2026-03-18

🎯 Massive refactoring: achieving ideal code quality
This release is dedicated to bringing the project to absolute quality standards. We systematically eliminated all linter warnings, achieved perfect typing, and 100% test pass rate. The project now meets enterprise development standards.

🏗️ Structure and naming
**Problem:** File names did not conform to PEP8 (PascalCase was used instead of snake_case), causing N999 errors in ruff.

**Solution:** Renamed all 18 files in the project according to the snake_case standard:

- `AuthCoordinator.py` → `auth_coordinator.py`
- `Authenticator.py` → `authenticator.py`
- `CheckRoles.py` → `check_roles.py`
- `ContextAssembler.py` → `context_assembler.py`
- `CredentialExtractor.py` → `credential_extractor.py`
- `Context.py` → `context.py`
- `EnvironmentInfo.py` → `environment_info.py`
- `RequestInfo.py` → `request_info.py`
- `UserInfo.py` → `user_info.py`
- `BaseLogger.py` → `base_logger.py`
- `ConsoleLogger.py` → `console_logger.py`
- `ExpressionEvaluator.py` → `expression_evaluator.py`
- `LogCoordinator.py` → `log_coordinator.py`
- `LogScope.py` → `log_scope.py`
- `VariableSubstitutor.py` → `variable_substitutor.py`

🔧 Code quality and linters
**Problem:** Numerous issues from ruff (N999, UP046, C901, W292), mypy (type errors), pylint (R0917, W0621, C0304, R1705).

**Solution:** Conducted a thorough code cleanup:

- Eliminated all 18 ruff errors, including the complexity of the `substitute` function (C901 was reduced from 11 to A(2) by decomposing into `_substitute_simple`, `_substitute_with_iif_detection`, `_substitute_variables`).
- Fixed all mypy errors: removed unused `type: ignore`, fixed the `context()` call in `ActionTestMachine`, added type annotations.
- Achieved pylint rating of 10.00/10 (fixed: unnecessary else in `console_logger._format_line`, name conflict `authenticator` and `context`, missing newline at end of files, too many positional arguments).

🧪 Testing and reliability
**Problem:** Tests did not run due to incorrect imports after file renaming.

**Solution:** Updated all imports in test files (`conftest.py`, `test_auth_coordinator.py`, `test_plugins.py`, etc.). All 341 tests now pass successfully.

**Achieved:** 100% test suite pass rate.

📦 Configuration and tools
**Problem:** Linter configuration was scattered, and some rules conflicted.

**Solution:** Centralized configuration in `pyproject.toml`:

- Configured ruff with conflicting rules disabled (E501, E402, N801, W292).
- Fixed pylint section: removed invalid code W292 (from ruff), added correct code C0304 to disable newline warning.
- Added per-file-ignores rules in ruff.

### Added
- **Linter rule disabling** – added comments to each disabled rule in `pyproject.toml` explaining the reason.
- **Automatic fixing** – added `lint-fix` and `pre-commit` commands to taskipy for automatic formatting fixes.

### Fixed
- **Fixed ABC import in `BaseAction.py`** – replaced incorrect import from `typing` with correct one from `abc` (runtime error).
- **Fixed `authenticator` name conflict** – in `auth_coordinator.py`, renamed constructor parameter from `authenticator` to `auth_instance`, attribute kept as `self.authenticator` (fixed pylint W0621).
- **Fixed `context` name conflict** – in all loggers (`base_logger.py`, `console_logger.py`, `log_coordinator.py`, `variable_substitutor.py`), renamed parameter `context` to `ctx`.
- **Fixed newline warning** – added blank lines at the end of all files where they were missing (C0304).
- **Fixed unnecessary `else` after `return`** – in `console_logger._format_line`, removed redundant branching (R1705).

### Changed
- **Improved code readability** – complex methods decomposed into smaller ones, added detailed comments.
- **Updated documentation** – added usage examples for all key components.

### Removed
- **Obsolete and unused imports** (checked with `vulture`).

## [0.0.2] - 2026-03-17

### Added
- **Conditional logic in logging templates** – added support for the `{iif(condition; true_value; false_value)}` construct in logger messages.
  - **Problem:** Previously only variable substitution `{%namespace.path}` was possible, but text could not be dynamically changed based on values (e.g., adding a "CRITICAL" marker for large amounts). This limited log expressiveness and forced developers to write additional checks in code.
  - **Solution:** Introduced the `ExpressionEvaluator` class, which safely evaluates expressions inside `iif` using the `simpleeval` library. Supported operators: comparison (`==`, `!=`, `>`, `<`, `>=`, `<=`), logical (`and`, `or`, `not`), arithmetic (`+`, `-`, `*`, `/`), built-in functions (`len`, `upper`, `lower`, `format_number`). Variables are substituted as literals before evaluation, ensuring safety and predictability. If an expression is invalid, `LogTemplateError` is thrown (strict policy), allowing immediate detection of template errors.
- **Extracted substitution logic into a separate class `VariableSubstitutor`.**
  - **Problem:** The `LogCoordinator` class contained complex logic for resolving variables and evaluating `iif`, leading to high cyclomatic complexity (B10) and low Maintainability Index (MI 34.95). This hindered testing and further development.
  - **Solution:** Moved all variable substitution and `iif` processing logic into a separate `VariableSubstitutor` class. `LogCoordinator` now only delegates substitution and broadcasts results to loggers. This raised MI of `LogCoordinator` to 100.00, and `VariableSubstitutor` got MI 46.66, indicating good maintainability.
- **Decomposition of `iif` parser** – extracted class `_IifArgSplitter`.
  - **Problem:** The `_split_iif_args` method in `ExpressionEvaluator` had high complexity (B10) due to manual parsing considering nested parentheses and strings. It was hard to read and test.
  - **Solution:** Created a separate `_IifArgSplitter` class implementing a finite state machine for argument parsing. Each method of the class has complexity A(1–2), making the code transparent and easily testable.
- **Validator chain for `_check_connections`.**
  - **Problem:** The `_check_connections` method in `ActionProductMachine` contained multiple rules in one body, giving complexity B10 and making it difficult to test individual rules.
  - **Solution:** Split the method into 4 private validators, each checking one rule of correspondence between passed `connections` and those declared via `@connection`. The main method simply calls them in order. Complexity of the main method reduced to A(5), each validator has complexity A(1–2).
- **Extracted plugin coordinator `PluginCoordinator`.**
  - **Problem:** The `ActionProductMachine` class was responsible for too many concerns (aspects, roles, connections, plugins, execution), resulting in MI 48.45 and making changes to plugin logic difficult.
  - **Solution:** Moved plugin management logic (state initialization, handler caching, asynchronous execution with semaphore) into a separate `PluginCoordinator` class. `ActionProductMachine` delegates plugin calls to it. MI of the main class increased to 51.15, and `PluginCoordinator` has MI 64.22, improving modularity and testability.
- **Improved `ReadableMixin.resolve`** – extracted navigation steps.
  - **Problem:** The `resolve` method contained three traversal strategies in a single loop (complexity B9), making it difficult to add new navigation types (e.g., for `NamedTuple`) and increasing error risk.
  - **Solution:** Extracted the three strategies into separate static methods (`_resolve_step_readable`, `_resolve_step_dict`, `_resolve_step_generic`), and strategy selection into `_resolve_one_step`. Complexity of `resolve` reduced to A(5), each step has complexity A(1–2).

### Fixed
- **Fixed error in `ExpressionEvaluator.evaluate_iif`** – now correctly handles string literals in branches: they are returned without quotes, allowing the result to be used directly in the template.
- **Fixed issue with boolean literals** – expressions now correctly recognize `True` and `False` (instead of invalid `truefalse`).
- **Eliminated `PytestCollectionWarning` for the test class `TestParams`** – renamed the class to `Params_Test` (ignored by pytest).

## [0.0.1] - 2026-03-16

### Added
- **Unified data access protocol** – introduced interfaces `ReadableDataProtocol` and `WritableDataProtocol`.
  - **Problem:** Different parts of the framework (aspects, plugins, tests) used various data access methods: some accessed attributes (`params.value`), others expected dictionaries (`state["key"]`). This led to confusion, code duplication, and difficulties when adding new data types (TypedDict, user classes).
  - **Solution:** Protocols define a unified interface for reading (`__getitem__`, `get`, `keys`, ...) and writing (`__setitem__`). Now any object implementing these methods can be used as `Params`, `Result`, or `state` in plugins.
- **Mixins for dataclasses** – `ReadableMixin` and `WritableMixin`.
  - **Problem:** Existing dataclass models (`UserInfo`, `RequestInfo`, `EnvironmentInfo`, as well as user `Params` and `Result`) did not satisfy the new protocols. Rewriting them manually would be labor-intensive.
  - **Solution:** Mixins automatically implement the protocols via reflection (`getattr`, `setattr`). Simply inherit a class from `ReadableMixin` (and/or `WritableMixin`), and it immediately gains dict-like access without changing existing code.
- **Strict typing for `state`.**
  - **Problem:** Previously, `state` was a plain dictionary without any static typing. This led to runtime errors (typos in keys, incorrect types) and hindered refactoring.
  - **Solution:** Now `state` must be typed via `TypedDict` (or a plain dict with annotations). Each aspect receives and returns a strictly typed state. Mypy checks conformance at compile time, and checkers do so at runtime.
- **Asynchronous authentication interfaces.**
  - **Problem:** Components `Authenticator`, `CredentialExtractor`, `ContextAssembler`, and `AuthCoordinator` were synchronous, preventing I/O operations (e.g., token verification via external API) without blocking the event loop.
  - **Solution:** All methods converted to `async def`. Implementations can now use `await` for asynchronous calls. `AuthCoordinator.process()` also became asynchronous and awaits component results.
- **Safe plugin initialization.**
  - **Problem:** The `get_initial_state()` method of plugins was called synchronously inside the async pipeline. If the implementation performed long operations (file reading, API request), it blocked the event loop.
  - **Solution:** Moved the call to a separate thread via `loop.run_in_executor`. Now even "heavy" initialization does not affect performance.
- **Dict-like access for context components.**
  - **Problem:** Components `UserInfo`, `RequestInfo`, and `EnvironmentInfo` were plain dataclasses, accessible only via attributes. This limited their use in plugins and logging, where dict access is more convenient.
  - **Solution:** Classes inherited from `ReadableMixin`. Now they can be accessed as `user["user_id"]`, unifying data access and simplifying serialization.
- **Migration guide** – a detailed document with examples of transitioning to the new version.

### Changed
- **Core (`ActionProductMachine`, `DependencyFactory`)** completely reworked to work via protocols.
  - **Reason:** Eliminate hard binding to `BaseParams`/`BaseResult`. Now the machine accepts any objects satisfying `ReadableDataProtocol` (for `params`) and `WritableDataProtocol` (for `result`). This opens the way to using TypedDict, user classes, and other structures.
- **`BaseParams` and `BaseResult`** are no longer abstract classes; they inherit the corresponding mixins.
  - **Reason:** Maintain backward compatibility. Existing parameter and result classes continue to work but now automatically implement the protocols.
- **Plugins** now receive data via `PluginEvent` with clear types: `params: ReadableDataProtocol`, `state_aspect: Optional[dict[str, object]]`, `result: Optional[WritableDataProtocol]`. All standard plugins rewritten to dict access.
  - **Reason:** Ensure type safety in plugins and unify data access.
- **`sync_run` method** improved: added a more precise error message when called from an async context.
  - **Reason:** Previously the message was uninformative; now the developer immediately understands that `sync_run` cannot be used inside an `async` function.
- **Tests** updated to cover new scenarios: TypedDict as input data, `state` as dict, mocks with `side_effect`, asynchronous authentication, dict access to context components.

### Removed
- **Outdated attribute access to fields** in core and plugins. Now only `obj["key"]`.
  - **Reason:** Unify access and eliminate code duplication.
- **Unused imports and dead code** (checked with `vulture`).

### Fixed
- **Cyclic import in `ActionProductMachine`** (removed incorrect self-import).
- **All `mypy --strict` errors** (project is now fully typed).
- **Achieved maximum `pylint` rating (10.00/10)** and zero `vulture` warnings.
- **Fixed event loop blocking** during plugin state initialization (execution in executor).
- **Fixed missing `await` in `AuthCoordinator.process()`**.
- **Fixed typing error in `ActionTestMachine.run()`** when returning result from `MockAction` (added `cast`).

## [1.0.0] - 2026-03-15

### Added
- **Basic AOA architecture** – Actions as atomic business operations consisting of a linear sequence of aspects.
- **Base classes** – `BaseAction`, `BaseParams`, `BaseResult` with generics support.
- **Aspects** – decorators `@aspect` and `@summary_aspect` for declaring execution stages. Aspects are called strictly in the order defined in the class (sorted by `co_firstlineno`).
- **Declarative DI** – `@depends` decorator for declaring action dependencies. Support for `factory` parameter for custom object creation.
- **Connection management** – `@connection` decorator for declaring required resource managers. Automatic validation of passed `connections` against declared keys.
- **ActionProductMachine** – production implementation of the action machine with aspect caching, role checking, checker validation, plugin support, and nested calls.
- **ActionTestMachine** – test implementation with dependency mocking via a dictionary of mocks. Automatic wrapping of `BaseResult` and callable into `MockAction`.
- **Plugins** – basic plugin system: `Plugin` class, `@on` decorator for event subscription, isolated plugin state (`get_initial_state`), `ignore_exceptions` support.
- **PluginEvent** – dataclass with full event information: `event_name`, `action_name`, `params`, `state_aspect`, `is_summary`, `deps`, `context`, `result`, `duration`, `nest_level`.
- **Execution context** – classes `UserInfo`, `RequestInfo`, `EnvironmentInfo` and the unifying `Context`. Context is created before action execution and accessible only to plugins and the machine.
- **Authentication** – components `CredentialExtractor`, `Authenticator`, `ContextAssembler` and coordinator `AuthCoordinator` to form Context from a request.
- **Role model** – `@CheckRoles` decorator is mandatory for each action. Support for special values `NONE` (no authentication), `ANY` (any authenticated user), and a list of specific roles.
- **Checkers** – result validation system for aspects via decorators: `IntFieldChecker`, `StringFieldChecker`, `BoolFieldChecker`, `FloatFieldChecker`, `DateFieldChecker`, `InstanceOfChecker`. Each checker validates presence, type, and additional field constraints.
- **Resource managers** – basic hierarchy: `BaseResourceManager`, `IConnectionManager`, concrete implementation `PostgresConnectionManager`, and proxy wrapper `WrapperConnectionManager` for safe connection passing to child actions.
- **Exceptions** – exception hierarchy: `AuthorizationException`, `ValidationFieldException`, `HandleException`, `TransactionException`, `ConnectionAlreadyOpenError`, `ConnectionNotOpenError`, `TransactionProhibitedError`, `ConnectionValidationError`.
- **Helper utilities** – `CoreHelper.run_in_thread` to execute synchronous code in a separate thread without blocking the event loop.
- **Tests** – comprehensive test suite demonstrating aspects, DI, nested actions, plugins, mocks, and integration with external DI containers (inject).