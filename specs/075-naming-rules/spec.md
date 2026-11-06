# Feature Specification: Every base class names its descendants

**Feature Branch**: `feature/issue-486-naming-rules`

**Created**: 2026-11-06

**Status**: Draft

**Input**: Issue #486, "Every base class names its descendants". Step 3 of the root issue #488.

## What this is

A class name says what the class is. AOA already refuses, when a class is declared, an action not ending with `Action`, a domain without `Domain`, a role without `Role`, an event without `Event`, and an entity without its kind (`CoreEntity` and the five others). Every other base class keeps its descendants' names by habit only. After this change every base class names its descendants the same way, and resources get kinds the way entities have them.

## Clarifications

### Session 2026-11-06

- Q: Which classes may inherit `BaseResource` directly? → A: Only the three kind bases, `BaseStorage`, `BaseGateway` and `BaseController`, as `BaseEntity` admits only its six kinds. Any other direct descendant is refused with `DeclarationStructureError`, naming the three kinds.
- Q: What suffix does a resource carry? → A: Its kind: `…Storage`, `…Gateway`, `…Controller`. The kind bases already end so.
- Q: What is a wrapper's name? → A: Its kind and `Wrapper`: `…StorageWrapper`, `…GatewayWrapper`, `…ControllerWrapper`. A resource class whose name ends with `Wrapper` must end with its kind's wrapper suffix; and when the model is built, every class a resource's `get_wrapper_class()` names must carry its kind's wrapper suffix. A wrapper is still a resource of its kind, so the kind rule reads "ends with the kind, or with the kind and `Wrapper`".
- Q: Which other base classes get the rule? → A: `BasePlugin` (today `Plugin`) → `Plugin`; `BaseLogger` → `Logger`; `BaseParams` → `Params`; `BaseResult` → `Result`; `Lifecycle` → `Lifecycle`; `BaseAdapter` → `Adapter`; `BaseCoordinator` → `Coordinator`; `BasePluginEvent` → `Event`; `BaseGraphNode` → `GraphNode`; `BaseGraphEdge` → `GraphEdge`; `BaseGraphNodeInspector` → `Inspector`; `BaseActionMachine` → `Machine`; `BaseRouteRecord` → `RouteRecord`. `BaseIntent` gets none: every primitive inherits it.
- Q: Which classes are renamed in AOA's own code? → A: `Plugin` → `BasePlugin`; `ParamsStub` → `StubParams`, `ResultStub` → `StubResult`; `SqlResource` → `SqlStorage`, `PostgresResource` → `PostgresStorage`, `WrapperSqlResource` → `SqlStorageWrapper`; `SocketChannel` → `SocketChannelController`; `WrapperLangGraphController` → `LangGraphControllerWrapper`; `OcelStoreResource`, `InMemoryOcelStoreResource`, `OcelStoreWrapper` → `OcelStorage`, `InMemoryOcelStorage`, `OcelStorageWrapper` on `BaseStorage`. Module names follow the class names where a module is named after one class.
- Q: What about `@on`? → A: A method declared with `@on` must start with `on_`, as every handler does today; the rule names the method and the prefix.
- Q: Is the old name kept as an alias? → A: No. The change is breaking; every caller in the repository moves, and the changelog says how to migrate.
- Q: Does Maxitor move here? → A: No. Gnomon takes AOA as a submodule at a fixed commit; it follows in gnomon#67.

## User Scenarios & Testing

### User Story 1 - A resource's name says its kind (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `class CatalogDatabase(PostgresStorage)`, **When** the class is declared, **Then** `NamingSuffixError` says it inherits `BaseStorage` and should be named `CatalogDatabaseStorage`.
2. **Given** `class Cache(BaseResource)`, **When** the class is declared, **Then** `DeclarationStructureError` says a resource inherits `BaseStorage`, `BaseGateway` or `BaseController`.
3. **Given** `class OrdersWrapper(BaseStorage)` or a resource whose `get_wrapper_class()` names a class not ending with `StorageWrapper`, **Then** the declaration, or the model build, is refused naming the expected suffix.

### User Story 2 - Every other base class names its descendants (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a descendant of any base class listed in the clarifications whose name lacks the suffix, **When** it is declared, **Then** `NamingSuffixError` names the class, the base and the suffix.
2. **Given** an `@on` method not starting with `on_`, **When** it is declared, **Then** `NamingSuffixError` names the method and the prefix.

### User Story 3 - The repository follows (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the core, the six other packages, their tests, the demo, the examples, the notebooks and the documentation, **When** they are imported, run and built, **Then** none breaks a rule, and none names an old class.

## Requirements

- **FR-001**: Only `BaseStorage`, `BaseGateway` and `BaseController` inherit `BaseResource` directly; a resource's name ends with its kind, a wrapper's with its kind and `Wrapper`; `get_wrapper_class()` targets are checked when the model is built.
- **FR-002**: The base classes of the clarifications refuse a descendant without its suffix; `Plugin` is `BasePlugin`.
- **FR-003**: `@on` refuses a method not starting with `on_`.
- **FR-004**: The renames of the clarifications, in every package, test, example, notebook and page.
- **FR-005**: Graph files rebuilt; every changed level raises its version.
- **FR-006**: One documentation page lists every naming rule; one changelog article.

## Success Criteria

- **SC-001**: Each rule has a test that fails when the rule is removed, and no other test of its phase fails then.
- **SC-002**: No file outside `specs/` and the changelog names an old class.
- **SC-003**: The closing check run on the pull request is green.

## Assumptions

- Test-only classes (doubles, fakes) follow the rules too: they are declared, so they are checked.
