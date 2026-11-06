# Feature Specification: A resource is a database, and the model knows no store

**Feature Branch**: `feature/issue-487-resource-is-database`

**Created**: 2026-11-07

**Status**: Draft

**Input**: Issue #487, "A resource is a database, and the model knows no store" (bystrovmaxim/aoa#487). Step 4 of the root issue #488: a resource is a database, and the model knows no store.

## What this is

Today the model says which store an entity lives in and which data source reaches it, and a resource is the bridge between one domain and its data. After this change a resource **is** a database: it lists the entities that lie in it, and the model names no store at all. A relation may join entities of two databases, and only an action glues their data. The machine then checks every answer a resource gives: it may carry only the entities that resource lists.

## Clarifications

### Session 2026-11-07

- Q: What does an entity declare? → A: `@entity(description, domain=…)`: an entity names its domain. The `resource=` argument is removed.
- Q: What does a resource declare? → A: `@entities(*entity_classes)` lists what lies in this database and what the resource may assemble; each listed class must be an `@entity`. The `@meta` of a resource takes no domain: a database is shared by domains, and its domains are the domains of its entities.
- Q: What is a resource, and what glues two of them? → A: A resource is one database. Two databases are two resources; the data of two resources is glued only by an action. A relation may join entities of any resources.
- Q: What happens to data sources? → A: `BaseDataSource`, `InMemoryDataSource`, `ExternalServiceDataSource`, the data source graph node and its edges are removed, with the generic parameter of resources. `PostgresDataSource` becomes `PostgresPool`: it keeps the connection parameters, opens the pool, hands connections out and takes them back; it is in neither the model nor the graph.
- Q: How does a PostgreSQL resource connect? → A: It takes exactly one of `pool=` (a connection from the pool) or `connection_params=` (its own connection per call). A resource of a kind that knows no pool takes neither. Transactions stay inside the resource; its class does not depend on how it connects. The application chooses when it is assembled: a pool in a service's lifespan, an own connection in a script, a substitute pool in a test.
- Q: When does the machine check what a resource returns? → A: Always; there are no modes. When the model is built, AOA computes a plan for each resource: from which of its entities a relation leads out of its `@entities`. A class from which no such relation is reachable needs only its type checked. When a public method returns, the wrapper walks the answer by that plan.
- Q: Which rules are removed? → A: The rules of #475 and #479: a data source required for a resource that stores an entity; one resource per domain and data source; `@depends` only on resources of the action's domain.
- Q: What is out of scope? → A: Writes are not bounded by domain: an action of any domain may write through any resource it uses. Maxitor's logical and physical views (gnomon#67) and one transaction across two resources on one database are not included.
- Q: Where does the graph builder come from? → A: The merge commit of gnomon#66, which writes and reads protocol 2.0.
- Q: May one entity class be listed by two resources? → A: Yes. One logical entity may lie in two databases — a replica or a projection — and nothing refuses it. The graph carries one `resource_entity` link per resource, and the check compares an answer with the list of the resource that returned it.
- Q: Which resource kinds may declare `@entities`? → A: Every kind. The declaration says which entities the resource may return, and the check runs on every resource's answer; a gateway that returns catalog entities declares them and links to them in the graph. No separate rule restricts the declaration to storage.
- Q: Does a subclass of a listed entity pass the check? → A: No. The resource declared concrete classes and must return exactly what it promised; a subclass of a listed class is not listed and is refused. Entities are not subclassed in the model: when an answer must be shorter, it is a partial entity of the same class, and that class is listed, so a partial answer passes.
- Q: What does "comes in a wrapper" mean? → A: The resource's own public methods are wrapped when its class is declared; the action receives the resource itself, not a proxy, so `isinstance`, identity and attribute access stay exactly as they are. Checks on `connections[…]`, `box.resolve(…)` and a test-bench substitute all run because they hand over that same object.
- Q: What does a class listed twice in `@entities` do? → A: The declaration is refused, naming the class; a database lists each of its entities once.
- Q: Do dictionary members and lifecycle states have to be listed? → A: No. A dictionary member (`BaseEnumEntity`) and a lifecycle state (`BaseStateEntity`) belong to the model, not to a database: a relation to a dictionary holds its members loaded, and the check passes them wherever they appear in an answer.
- Q: What is a reference? → A: An unloaded relation — the relation container holds the id and no entity. A relation that leads out of the list passes only unloaded; a loaded entity of a class outside the list is refused, even a partial one that holds only its id.
- Q: What does a resource wrapper check? → A: A wrapper (`SqlStorageWrapper` or an application's `…StorageWrapper`) hands a nested action the resource it wraps; its answers are checked by the plan of the wrapped resource, not by a list of its own.
- Q: Which plan applies to a subclass? → A: The plan of the concrete class of the resource that answered. A subclass with its own `@entities` has its own plan; it never inherits its parent's.
- Q: Which methods are checked? → A: The plain functions, coroutine functions and async generators declared in a resource's class body whose names do not start with `_`. Class methods, static methods and properties are not wrapped (`get_wrapper_class` is a class method). A plain generator, and a plain function that returns an awaitable, are not checked.
- Q: Is a test-bench substitute checked? → A: When the substitute is a resource instance — a gateway built around a mock client, a storage over a substitute pool — its methods are checked like any resource's. A bare `Mock` is not a resource and is not checked.

## User Scenarios & Testing

### User Story 1 - A model that names no store (Priority: P1)

A developer declares `OrderCoreEntity` with `domain=StoreDomain` and no resource, then declares `ShopDatabaseStorage(PostgresStorage)` with `@entities(OrderCoreEntity, OrderLineDetailEntity, CustomerCoreEntity, TicketCoreEntity)` and `@meta` without a domain. A relation from `OrderCoreEntity` to an entity of another database is accepted. Two resources over two databases coexist without a refusal.

**Why this priority**: This is the change of meaning the whole feature rests on: without it a resource is still a bridge, and the check on return has nothing to compare an answer with.

**Independent Test**: Declare entities and resources of two databases in a fresh interpreter, build the model, and read back the entity's domain and the resource's entity list and domains.

**Acceptance Scenarios**:

1. **Given** `@entity(description="Customer order", domain=StoreDomain)`, **When** it is declared, **Then** the entity names `StoreDomain` and no resource; `@entity(..., resource=...)` is refused.
2. **Given** `@entities(OrderCoreEntity, ...)` on `ShopDatabaseStorage`, **When** the model is built, **Then** the resource lists exactly those entities, and its domains are the domains of those entities; `@meta(domain=…)` on the resource is refused.
3. **Given** a relation from an entity of one resource to an entity of another, **When** both are declared, **Then** the relation is accepted, and the two databases stay two resources.
4. **Given** a resource whose `@entities` names a class that is not an `@entity`, **When** the class is declared, **Then** the declaration is refused, naming the class and the requirement.
5. **Given** an action of one domain and `@depends` on a resource used by another domain, **When** the model is built, **Then** it is accepted; the rules of one resource per domain and of resources-only-of-the-action's-domain are gone.
6. **Given** a stored entity and a resource, **When** the model is built, **Then** no data source is required anywhere, and `BaseDataSource` does not exist to be named.

---

### User Story 2 - The machine refuses an entity the database does not hold (Priority: P1)

A resource `ShopDatabaseStorage` lists four entities. Its `get_order` returns an `OrderCoreEntity` whose `lines[0].product` is a `ProductCoreEntity` from the catalog database. The wrapper walks the answer and refuses it: that class is not in the list. A relation that leads out of the list must come back unloaded — the relation holds the product's id and no entity — and then it passes.

**Why this priority**: The check is what makes "a resource is a database" true at runtime rather than a naming convention. It is also the part that must not cost anything visible or change how a resource is written.

**Independent Test**: Define a resource with `@entities`, return entities inside and outside the list from a public method, and observe the pass, the refusal, the reference case and the iterator case.

**Acceptance Scenarios**:

1. **Given** a resource handed to an action through `connections[…]`, `box.resolve(…)` or a test-bench substitute that is a resource instance, **When** the action receives it, **Then** it receives the resource itself, and that resource's public methods are checked.
2. **Given** a public method that returns an entity the resource lists, **When** it returns, **Then** the answer passes and reaches the caller unchanged.
3. **Given** a public method that returns an entity the resource does not list, **When** it returns, **Then** `ResourceEntitiesError` names the resource, the entry point, the path inside the answer and the class, as in `ShopDatabaseStorage.get_order returned ProductCoreEntity at order.lines[0].product, which @entities(ShopDatabaseStorage) does not list`.
4. **Given** a relation that leads out of the list and is returned loaded, even with a partial entity that holds only its id, **When** the method returns, **Then** the answer is refused; **Given** the same relation returned unloaded (the container holds the id and no entity), **Then** it passes.
5. **Given** an async iterator that yields an entity outside the list, **When** the consumer reaches that element, **Then** the check fails at that element, as it yields.
6. **Given** a resource without `@entities` that returns an entity, **When** it returns, **Then** it is refused the same way, saying the resource declares no `@entities`.
7. **Given** a method whose name starts with `_`, **When** it returns an entity outside the list, **Then** it is not wrapped and not refused.
8. **Given** an answer that carries no entity, **When** it returns, **Then** it passes at the cost of one type check.
9. **Given** a `list`, `tuple` or mapping of entities inside the list, **When** it returns, **Then** every element is checked, and the path in the refusal names the element.
10. **Given** a public method that returns an instance of a subclass of a listed class, **When** it returns, **Then** it is refused as not listed; **Given** a partial answer of a listed class, **Then** it passes.
11. **Given** an answer whose entity holds a dictionary member or a lifecycle state, **When** it returns, **Then** it passes: neither needs to be listed.
12. **Given** a nested action that receives a resource through its wrapper, **When** a wrapper method returns the wrapped resource's answer, **Then** it is checked by the wrapped resource's plan.
13. **Given** a subclass of a resource with its own `@entities`, **When** an inherited method returns, **Then** the answer is checked by the subclass's list.

---

### User Story 3 - A database is reached through a pool or one connection (Priority: P2)

A service assembles `ShopDatabaseStorage(pool=PostgresPool(...))` in its lifespan; a script assembles `ShopDatabaseStorage(connection_params=...)` for one run; a test assembles `ShopDatabaseStorage(pool=SubstitutePool())`. The resource's class is the same in all three, and its transactions stay inside it.

**Why this priority**: Removing the data source must not remove the choice of how a database is reached; it moves that choice to the application.

**Independent Test**: Assemble the same resource class three ways, call the same method, and observe the same behaviour; declare both and neither for a PostgreSQL resource and observe the refusals.

**Acceptance Scenarios**:

1. **Given** a PostgreSQL resource with `pool=`, **When** it is assembled and a method runs, **Then** it takes a connection from the pool and returns it.
2. **Given** a PostgreSQL resource with `connection_params=`, **When** a method runs, **Then** it opens its own connection and closes it.
3. **Given** a PostgreSQL resource with both or with neither, **When** it is declared, **Then** the declaration is refused, naming the two arguments and the choice.
4. **Given** a resource of a kind that knows no pool, **When** it is given `pool=` or `connection_params=`, **Then** it is refused.
5. **Given** `PostgresPool`, **When** the model is built and the graph is drawn, **Then** the pool appears in neither.

---

### User Story 4 - The graph has no data source (Priority: P2)

The saved graph is protocol 2.0. Each resource links to each of its entities through `resource_entity`; a resource has no `domain` link; an entity has its own `domain` link. No data source vertex or edge exists.

**Why this priority**: The graph is the published model; it must show the new shape or the change is invisible to Maxitor and to readers of the saved file.

**Independent Test**: Build the demo's graph, read the saved file, and check the link kinds and their ends.

**Acceptance Scenarios**:

1. **Given** the model, **When** the graph is built, **Then** each `@entities` entry appears as a `resource_entity` link from the resource to the entity.
2. **Given** a resource with `@meta`, **When** the graph is built, **Then** it has no `domain` link; **Given** an entity, **Then** it links to its domain.
3. **Given** the saved graph file, **When** `graph-builder check` runs, **Then** the file is current, and no data source vertex or edge appears in it.

---

### User Story 5 - The demo is a set of databases (Priority: P3)

Resources that share a database today become one resource of it, listing the entities of every domain kept there. Relations between databases stay; an action glues their data.

**Why this priority**: The demo is the documented example of the model; it must show one database per resource, not one resource per domain.

**Independent Test**: Run the demo's tests and build its graph; count resources per database and check that relations across databases still exist.

**Acceptance Scenarios**:

1. **Given** two demo domains whose data lives in one database today, **When** the demo is migrated, **Then** they share one resource that lists the entities of both.
2. **Given** entities of two databases with a relation between them, **When** an action reads both, **Then** the action glues their data and each resource answers only its own entities.
3. **Given** the demo's tests and graph, **When** they run, **Then** they pass with the merged resources and the rebuilt graph.

---

### Edge Cases

- An entity listed by `@entities` twice, or an `@entities` with no classes: what the declaration says.
- An entity listed by two resources: each resource applies its own plan, and the graph carries one `resource_entity` link from each of them.
- A relation that leads out of the list, loaded with a partial entity that holds only its id: a loaded entity, refused; only an unloaded relation is a reference.
- An async iterator whose consumer stops early: which elements were checked.
- A method that returns an awaitable, a generator or a nested structure of mappings and lists: what the path in a refusal names.
- A subclass of a listed entity returned by a public method: refused, because the resource returns exactly the class it promised; a partial answer of a listed class is that class and passes.
- A gateway or a controller that declares `@entities` and returns those entities: accepted, checked, and linked in the graph the same way as a storage.
- A substituted resource in the test bench: the check runs on a substitute that is a resource instance the same way it runs on the real resource; a bare `Mock` is not checked.
- A dictionary member or a lifecycle state inside an answer: passed, since both belong to the model.
- A resource wrapper handed to a nested action: checked by the plan of the resource it wraps.
- The demo's data source classes that disappear with the change and the pages that name them.

## Requirements

### Functional Requirements

- **FR-001**: `@entity` takes `description` and `domain=…`; an entity names exactly one domain and no store; the `resource=` argument is removed and refused.
- **FR-002**: `@meta` of a resource takes no domain; a resource's domains are the domains of its entities.
- **FR-003**: `@entities(*classes)` lists the entities that lie in a database and that the resource may assemble; every listed class must be an `@entity`, and a class that is not is refused at declaration, naming the class and the requirement. The same entity class may be listed by more than one resource, and nothing refuses it; a class repeated in one list is refused, naming it. Every resource kind may declare it: it says what the resource may return, not only what a storage holds. The declaration is optional on a resource that never returns an entity.
- **FR-004**: A relation may join entities of different resources, and two resources over different databases coexist; an action glues the data of two resources.
- **FR-005**: `BaseDataSource`, `InMemoryDataSource`, `ExternalServiceDataSource`, the data source graph node and its edges, and the generic parameter of resources are removed from the package, its exports, its tests, its examples and its pages.
- **FR-006**: `PostgresDataSource` becomes `PostgresPool`; it keeps the connection parameters, opens the pool, hands connections out and takes them back; it appears in neither the model nor the graph.
- **FR-007**: A PostgreSQL resource takes exactly one of `pool=` or `connection_params=`; both or neither is refused at declaration; a kind that knows no pool takes neither and is refused when given one; transactions stay inside the resource and its class does not depend on how it connects.
- **FR-008**: The rules of #475 and #479 are removed: a resource that stores an entity requires no data source; one resource per domain and data source is not required; `@depends` may name a resource of another domain.
- **FR-009**: At model build, AOA computes for each resource the plan of which entities can reach a relation that leads out of its `@entities`; a class from which no such relation is reachable needs only its type checked.
- **FR-010**: A resource's public methods are wrapped once, when its class is declared: the plain functions, coroutine functions and async generators of its class body whose names do not start with `_`. Class methods, static methods and properties are not wrapped. An action receives the resource itself — through `connections[…]`, `box.resolve(…)` or a test-bench substitute that is a resource instance — so every one of these is checked; a bare `Mock` is not a resource and is not checked.
- **FR-011**: When a public method returns, the wrapper walks the answer by the plan of the concrete class that answered: the root, the elements of a list, tuple or mapping, and every loaded relation; an async iterator is checked element by element as it yields; a relation that leads out of the list must come back unloaded — the container holds the id and no entity. Dictionary members (`BaseEnumEntity`) and lifecycle states (`BaseStateEntity`) belong to the model and pass wherever they appear. A resource wrapper's answers are checked by the plan of the resource it wraps. A plain generator, and a plain function that returns an awaitable, are not checked.
- **FR-012**: An entity outside the list is refused with `ResourceEntitiesError`, naming the resource, the entry point, the path inside the answer and the class; the comparison is by the exact class, so a subclass of a listed class is not listed and is refused, while a partial answer of a listed class passes; a resource without `@entities` that returns an entity is refused the same way, saying it declares no `@entities`.
- **FR-013**: Methods whose names start with `_` are not wrapped; an answer without entities passes at the cost of one type check; the check always runs, and no mode turns it off.
- **FR-014**: The graph is protocol 2.0: a `resource_entity` link from each resource of any kind to each of its entities, from `@entities`; a resource has no `domain` link; an entity has its own; `graph-builder` is taken from the merge commit of gnomon#66.
- **FR-015**: The demo becomes "a resource is a database": resources that share a database become one resource listing the entities of every domain kept there; relations between databases stay; an action glues their data.
- **FR-016**: The saved graph files are rebuilt, and every changed level raises its version.
- **FR-017**: Documentation covers the constitution's page on resources, intents and invariants, entities, resources and the check on return, with an executed script and notebook for each case, including every refusal, and one changelog article.
- **FR-018**: Writes are not bounded by domain: an action of any domain may write through any resource it uses.

### Key Entities

- **Entity**: A business fact with a description, a domain and relations; it names no store after this change.
- **Resource**: One database; it lists the entities that lie in it through `@entities`, and its domains are theirs. An entity class may be listed by more than one resource.
- **Pool**: The connection source of a PostgreSQL database; it opens, hands out and takes back connections, and never enters the model.
- **Plan**: What the machine computed from a resource's `@entities` for the return check: which entity classes are checked by type only and which relations lead out of the list.
- **Wrapper**: The check put around each public method of a resource class when the class is declared; it applies the plan of the concrete class to the method's answer. The action receives the resource itself, not a proxy.
- **Relation and Reference**: A relation joins entities and may cross databases; a reference is an unloaded relation — its container holds the id and no entity — and is the only form in which a relation that leads out of the list may be returned.

## Success Criteria

### Measurable Outcomes

- **SC-001**: No active code, test, example, notebook or page names a data source, a resource's generic parameter, `resource=` on an entity or a domain on a resource's `@meta`; old names survive only in `specs/`, historical changelogs and labelled migration explanations.
- **SC-002**: A relation between entities of two databases is accepted, and two resources over different databases coexist with no refusal; the removed rules of #475 and #479 have no test and no implementation left.
- **SC-003**: Each refusal and each path of the return check has a test that fails when its check is removed, and no other test of its phase fails then.
- **SC-004**: On the demo's entities the return check costs no more than 5% of building the same entities, and the wrapper adds about 0.2 µs per call; an answer without entities passes at the cost of one type check. The figure is measured by a benchmark marked `benchmark`, which the closing check run leaves out; the regular tests guard only a loose upper bound, so that noise on a shared machine never fails them.
- **SC-005**: The demo's graph is protocol 2.0: one `resource_entity` link per listed entity, no resource `domain` link, an entity `domain` link, no data source vertex or edge; `graph-builder check` is green.
- **SC-006**: The closing check run on the pull request is green.

## Assumptions

- #485 and #486 are merged, and the names here follow #486.
- gnomon#66 is merged; its protocol 2.0 schema exists, and `graph-builder` is pinned to that merge commit.
- The wrapper is invisible to code that defines or uses a resource: no new base class, no changed public method signature, no new argument at the call site.
- A reference is an unloaded relation: its container holds the id and no entity. The plan decides which relations cross the boundary of the list.
- An entity's domain is required; `@entities` is required on a resource that assembles entities and optional on one that never returns an entity.
- Entity classes are not subclassed in the model: a shorter answer is a partial entity of the same class, so it is listed and passes. A subclass of a listed class is refused.
- `ResourceEntitiesError` is a runtime error and, like every AOA refusal of its kind, a `TypeError`; it is raised when a public method returns, never at declaration.
- `@entities` with no classes declares a resource that returns no entity; any entity it returns is refused. The path in a refusal names attributes as `order.lines[0].product`, with `[index]` for a sequence and `[key]` for a mapping.
- Writes are not bounded by domain; Maxitor's logical and physical views (gnomon#67) and one transaction across two resources on one database are not part of this change.
