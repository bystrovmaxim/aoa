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
- Q: What about `@on`? → A: Out of scope. Its existing `on_` validation and `NamingPrefixError` remain unchanged; this issue changes class naming only.
- Q: Is the old name kept as an alias? → A: No. The change is breaking; every caller in the repository moves, and the changelog says how to migrate.
- Q: Does Maxitor move here? → A: No. Gnomon takes AOA as a submodule at a fixed commit; it follows in gnomon#67.

### Session 2026-11-07

- **Handler naming excluded**: The maintainer confirmed that handlers are not changed in this issue. T006 is withdrawn; the remaining task IDs are stable.

- **Resource identity**: Only the actual framework kind bases may inherit `BaseResource` directly. A user class cannot obtain that privilege by copying a name or declaring `RESOURCE_KIND`. The kind is derived from ancestry, not a descendant's attribute. Combining two distinct resource kinds is refused with `DeclarationStructureError` at class declaration; multiple inheritance within one kind remains allowed when Python's MRO permits it.
- **Wrapper declaration**: `get_wrapper_class` becomes a class method returning a resource class or `None`, independent of resource instances. Existing instance-method overrides must migrate; the model build refuses them with `DeclarationStructureError`, rather than guessing whether they use `self`. Inherited class methods are valid. Model build checks every declared resource and recursively every returned wrapper, without constructing resources or opening connections. A visited set terminates self-reference and longer cycles after each distinct class is checked.
- **Wrapper results**: `None` means no wrapper and preserves pass-through. A non-resource result or a resource of another kind raises `DeclarationStructureError` at model build. A same-kind resource whose name lacks `<Kind>Wrapper` raises `NamingSuffixError` there. A method that raises causes model build to fail; its error is never treated as no wrapper. Correctly named inherited wrappers and deeper nesting remain supported.
- **Migration evidence**: Old identifiers may appear in `specs/`, historical changelogs and explicitly labelled migration explanations. They must not remain as active imports, exports, aliases, declarations or calls. Runnable documentation uses the new API; a before-migration code fragment is labelled as non-runnable with `# Fragment: <reason>`.
- **Delivery**: Local checks that can run here precede documentation and changelog. New documentation cases are executed while written. The complete branch is then eligible for a PR, where CI runs the closing checks. Commits and PR creation still require the maintainer's explicit instruction.

## User Scenarios & Testing

### User Story 1 - A resource's name says its kind (Priority: P1)

**Acceptance Scenarios**:

1. **Given** `class CatalogDatabase(PostgresStorage)`, **When** the class is declared, **Then** `NamingSuffixError` says it inherits `BaseStorage` and should be named `CatalogDatabaseStorage`.
2. **Given** `class Cache(BaseResource)`, **When** the class is declared, **Then** `DeclarationStructureError` says a resource inherits `BaseStorage`, `BaseGateway` or `BaseController`.
3. **Given** `class OrdersWrapper(BaseStorage)` or a resource whose `get_wrapper_class()` names a class not ending with `StorageWrapper`, **Then** the declaration, or the model build, is refused naming the expected suffix.

4. **Given** a user-defined direct subclass that copies a kind-base name or declares `RESOURCE_KIND`, **When** it is declared, **Then** `DeclarationStructureError` refuses it. The same error refuses inheritance from two resource kinds; a descendant attribute cannot change its ancestry-derived kind.
5. **Given** an inherited class-method wrapper declaration returning `None`, a same-kind wrapper, or a chain of wrappers, **When** the model is built, **Then** every distinct reachable class is checked without resource construction, and cycles terminate.
6. **Given** an instance-method override, non-resource return or wrong-kind wrapper, **When** the model is built, **Then** `DeclarationStructureError` identifies the invalid declaration. A same-kind target lacking the wrapper suffix raises `NamingSuffixError`; a getter exception fails the build without being suppressed.

### User Story 2 - Every other base class names its descendants (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a descendant of any base class listed in the clarifications whose name lacks the suffix, **When** it is declared, **Then** `NamingSuffixError` names the class, the base and the suffix.

### User Story 3 - The repository follows (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the core, the six other packages, their tests, the demo, the examples, the notebooks and the documentation, **When** they are imported, run and built, **Then** none breaks a rule, and no active API use names an old class; historical and migration explanations follow the stated exceptions.

## Requirements

- **FR-001**: Only `BaseStorage`, `BaseGateway` and `BaseController` inherit `BaseResource` directly; a resource's name ends with its kind, a wrapper's with its kind and `Wrapper`; `get_wrapper_class()` is a class method, and every reachable wrapper target is checked when the model is built, with the identity, inheritance, result and cycle rules above.
- **FR-002**: The base classes of the clarifications refuse a descendant without its suffix; `Plugin` is `BasePlugin`.
- **FR-003 (scope guard)**: Do not change `@on` handler naming, its validation or `NamingPrefixError`; no implementation task is assigned to this existing behavior.
- **FR-004**: The renames of the clarifications, in every package, test, example, notebook and page.
- **FR-005**: Graph files rebuilt; every changed level raises its version.
- **FR-006**: One documentation page lists every naming rule and migration; every new case, including refusals, has an executed script and matching notebook; one changelog article.

## Success Criteria

- **SC-001**: Each rule has a test that fails when the rule is removed, and no other test of its phase fails then.
- **SC-002**: No active API use retains an old class or renamed module. Old identifiers are permitted only in `specs/`, historical changelogs and explicitly labelled migration explanations as defined above.
- **SC-003**: The closing check run on the pull request is green.

## Assumptions

- Test-only classes (doubles, fakes) follow the rules too: they are declared, so they are checked.
