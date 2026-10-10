<!-- translated-from: intents-and-invariants_draft.md @ 2026-07-16T21:45:54Z (filesystem mtime; draft is gitignored, no git history) · sha256:d96324851717 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Intents and invariants

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [What the system requires of you](#what-the-system-requires-of-you)
- [What the system guarantees in return](#what-the-system-guarantees-in-return)
- [When invariants are checked](#when-invariants-are-checked)
- [The naming invariant](#the-naming-invariant)
- [Acyclic dependencies](#acyclic-dependencies)
- [Mandatory roles](#mandatory-roles)
- [Mandatory domain](#mandatory-domain)
- [A single summary aspect](#a-single-summary-aspect)
- [A correct compensator](#a-correct-compensator)
- [The include contract](#the-include-contract)
- [The state contract and checkers](#the-state-contract-and-checkers)
- [Privacy and masking in logs](#privacy-and-masking-in-logs)
- [Entity relations](#entity-relations)
- [Lifecycle FSM](#lifecycle-fsm)

---

In AOA every business operation is described through **intents** — declarations of what must be true: who has access, what the operation depends on, how a step is rolled back. An intent is a decorator: `@meta`, `@check_roles`, `@depends`, `@compensate`, `@on_error`, or a result checker.

By declaring an intent, you hand it to the system. An **invariant** is what the system takes on in return: it will check it — at startup, at runtime, at build, or in CI. It does not advise and does not remind — it checks.

And this link is two-way: the system not only keeps your intents but makes demands of its own. You cannot write an operation without roles, without a domain, without an exit point. These are not team conventions that can be bypassed by agreement — this is a grammar that is technically impossible to break.

This page is a reference: you come back to it when you need to know exactly what is checked and at what moment.

---

## What the system requires of you

AOA will not let a "bare" operation through. Every one must have roles, a domain, and an exit point — otherwise the machine does not start.

| Required | How to declare |
|----------|----------------|
| Access roles | `@check_roles(...)` |
| Domain | `@meta(domain=...)` |
| An exit point with a result | `@summary_aspect` |
| An acyclic dependency graph | `@depends` checked at startup |

If an operation is open to everyone, you say it out loud — `@check_roles(GuestRole)`. Not a formality but a declared intent, as opposed to a silent absence of a check.

---

## What the system guarantees in return

A declared intent the system takes under control:

| You declared | The system guarantees |
|--------------|------------------------|
| `@check_roles(AdminRole)` | the role is checked on every call |
| `@depends(PaymentAction, mode=UseCase.include)` | `PaymentAction` actually runs in this session |
| `@result_string("validated_id", required=True)` | the next step gets `state.validated_id` of the right type |
| `@compensate("charge_aspect", ...)` | on failure the rollback launches automatically |

---

## When invariants are checked

| Moment | What is checked |
|--------|-----------------|
| **Application startup** | the graph structure, naming, mandatory declarations, the absence of cycles |
| **Runtime (every call)** | roles, aspect contracts |
| **After the root session completes** | execution of all `UseCase.include` dependencies |
| **Build** | the lifecycle FSM, transition correctness |
| **CI** | package boundaries, class naming |

---

## The naming invariant

A suffix in AOA is not a matter of style. Each suffix is fixed by a base class or a decorator, and a violation raises `NamingSuffixError` at the moment the class or method is defined — before the application starts. The benefit is not only strictness: suffixes work as visual anchors. `...Resource` is an adapter of an external system, `...Action` is a business operation; the context reads before the file is even opened.

### The full suffix table

| What | Suffix | Where checked | Error |
|------|--------|---------------|-------|
| `BaseAction` subclass | `Action` | `__init_subclass__` at class definition | `NamingSuffixError` |
| `BaseDomain` subclass | `Domain` | `__init_subclass__` at class definition | `NamingSuffixError` |
| `BaseRole` subclass | `Role` | `__init_subclass__` at class definition | `NamingSuffixError` |
| `BaseEntity` subclass | `Entity` | `__init_subclass__` at class definition | `NamingSuffixError` |
| Method with `@regular_aspect` | `_aspect` | the decorator at method definition | `NamingSuffixError` |
| Method with `@summary_aspect` | `_summary` | the decorator at method definition | `NamingSuffixError` |
| Method with `@compensate` | `_compensate` | the decorator at method definition | `NamingSuffixError` |
| Method with `@on_error` | `_on_error` | the decorator at method definition | `NamingSuffixError` |

Beyond suffixes there are two more constraints. The description in `@regular_aspect("...")` and `@summary_aspect("...")` cannot be empty or whitespace-only — otherwise `ValueError` at decorator application. And indirect subclasses are checked on a par with direct ones: `class SpecificTask(BaseTaskAction)` without the `Action` suffix fails the same way.

```python
# ✗ arbitrary name — NamingSuffixError at method definition
@regular_aspect("Validation")
async def do_validation(self, ...): ...

# ✓
@regular_aspect("Validation")
async def validate_aspect(self, ...): ...

# ✗ empty description — ValueError
@regular_aspect("")
async def validate_aspect(self, ...): ...

# ✗ no Domain suffix — NamingSuffixError at class definition
class Shipping(BaseDomain): ...

# ✓
class ShippingDomain(BaseDomain): ...
```

---

## Acyclic dependencies

The dependency graph between operations (`@depends`) must be acyclic. If A depends on B, and B on A, the machine refuses at startup with `CyclicDependencyError` and shows the cycle's chain.

Without this invariant it is impossible to guarantee the execution order. A cycle, moreover, makes the include contract unsolvable: include requires the dependency to actually run, but in a cycle neither side can complete first. The analogy is familiar from build systems — this is a topological sort of tasks (Make, Gradle, Airflow).

---

## Mandatory roles

Every public operation must have `@check_roles`. Without it the machine will not run the operation — it does not warn, does not log, it refuses.

`@check_roles` does not implement the business logic of authorization — it guarantees that **the declaration exists** and is checked on every call. This is a different level: a developer cannot accidentally forget to write the check.

```python
# ✗ no @check_roles — the machine refuses
@meta(description="Delete order", domain=StoreDomain)
class DeleteOrderAction(BaseAction[...]): ...

# ✓ open to everyone — said explicitly
@meta(description="Get status", domain=StoreDomain)
@check_roles(GuestRole)
class GetOrderStatusAction(BaseAction[...]): ...
```

Access is one cascade, and it is checked in two moments: identity, roles and both conditions **before the run exists**, and the declared object rule **inside the run**, on a real object. Five words are published, and each of them can end a call — `AUTH_COORDINATOR`, `CHECK_ROLES`, `WHEN` (a role matched but its own condition refused), `GUARD` (the shared condition refused) and `ACCESS_DECIDE`. Each step carries its own invariants:

- **A condition declares the reason it refuses with.** `grant(..., when=..., reason=...)` and `@check_roles(guard=..., guard_reason=...)` are declared together: one without the other is refused where it is written. The declared sentence travels into `Refused.reason`, and the framework invents no reason of its own.
- **`when=`/`guard=` are synchronous functions returning strictly `bool`.** Checked at class definition, not at runtime: an `async def` in either raises `AccessConditionAsyncError` immediately — an un-awaited coroutine is always truthy, and an async condition would silently wave every check through.
- **There are three answers and only three.** `Allowed`; `Refused`, naming the step that refused and, when the developer declared one, the reason; `Undecided`, naming the step that could not tell — never the failure's text, which stays on the server. A refusal is not a failure and a failure is not a refusal.
- **The object check is a declaration.** One per operation, never inherited, named `..._access_decide`, with a non-empty description, `async` and a fixed signature (see below). An operation without one has no object-level rule — there is no default that "allows everything" to override.
- **The question is one call, one answer.** `machine.check_access_decide` asks about a single operation and a single set of parameters and returns one of the three words without running anything; there is no list form and no cap on one.
- **A refusal flies past `@on_error` and the saga.** The early steps run before `_execute_pipeline_aspects`: no aspect has run yet, so there is nothing to roll back. `@on_error` is a recovery mechanism for business-logic failures inside the pipeline, not a place for authorization decisions.

---

## Mandatory domain

Every operation and every domain entity is bound to a domain via `@meta(domain=...)` or `@entity(domain=...)`.

An operation without a domain is a "lost" component: it will not be in the system graph, not in Maxitor, not in the access matrix. Domains are the basis of the package-boundary invariant: they set the logical division that CI checks statically.

---

## A single summary aspect

Every operation has exactly one method marked `@summary_aspect`, and it must return a typed `Result`.

Otherwise the operation has no explicit exit point: the result could be assembled in several places, partially overwritten, or not assembled at all. The machine checks this at startup and raises `MissingSummaryAspectError`.

---

## The declared access check

`@access_decide` marks the operation's own object-level rule — the one part of a decision that needs the object itself. It is a declaration like `@summary_aspect`, and what the system requires of it is checked the same way: at declaration for the shape, at assembly for the types.

```python
    @access_decide("Refuse an order that is already locked")
    async def cancel_order_access_decide(
        self, params, box, connections,
    ) -> Verdict:
        return Allowed() if not params.order_id.startswith("LOCKED-") else FORBIDDEN_OBJECT
```

- **At most one per operation.** A second one is a `DuplicateAccessDecideError` at assembly: an operation answers about its object once.
- **A description is required, and it is not empty.** The sentence travels into the assembled graph, where the check is a node of its own with its own name and explanation.
- **The method is `async`.** The step awaits it; a plain `def` is refused where it is written.
- **The name ends with `_access_decide`.** Short names are refused the way they are for every declared behaviour.
- **The signature is fixed.** `(self, params, box, connections)`, plus the trailing `ctx` that `@context_requires` adds — names in that order, every parameter annotated, the annotations resolving to what the step hands over: `params` (`BaseParams` or the operation's own `Params`), `box: ToolsBox`, `connections: dict[str, BaseResource]`, `ctx: ContextView`.
- **It answers with a verdict.** A return of `Verdict` or one of its three answers; anything else is refused at assembly, and at run time a check that returns something else becomes `Undecided` rather than permission.

**Context is declared, never granted.** As with every declared behaviour, the context reaches the check only through `@context_requires` under the declaration: the trailing `ctx` then exists, it is a `ContextView` limited to the keys that were named, and another key raises `ContextAccessError`. There is no parameter that hands over the whole context.

The refusal rules above are the subject of [`examples/step_03_authorization_and_roles/06_the_declaration.py`](../../examples/step_03_authorization_and_roles/06_the_declaration.py), which runs each of them.

## A correct compensator

`@compensate(target, description)` must reference an existing `@regular_aspect` of the same class. A compensator without a corresponding aspect is not allowed — it is a "dead rollback" that will never fire.

Checked at startup. The compensator method name ends with `_compensate`.

```python
# ✓ charge_aspect exists — charge_compensate is valid
@regular_aspect("Charge funds")
async def charge_aspect(self, ...): ...

@compensate("charge_aspect", "Refund funds")
async def charge_compensate(self, ...): ...
```

---

## The include contract

If an operation declared a dependency with `UseCase.include`, the dependent operation **must actually run** within the same root session — not merely be declared, but be genuinely called via `await box.run(...)`.

Checked on completion of the root session, before `emit_global_finish`. On violation — `IncludeContractViolationError` with the list of unfulfilled dependencies in `missing_include_types`.

The difference from `UseCase.extend`: `extend` — the dependency may or may not run, depending on the operation's logic; `include` — mandatory on every successful completion of the root operation.

There are two clarifications. If the root operation was served from cache (a cache hit), the check is not run — nested calls from a past materialization do not belong to the current session. And if the pipeline returned a result through an error handler rather than the summary, the execution still counts as successful, and the include check still fires.

---

## The state contract and checkers

The decorators `@result_string`, `@result_instance`, `@result_bool`, and their kin declare an aspect's result contract: which key must appear in `state` and of which type. If an aspect did not return the expected — an error immediately, not on the next step.

This eliminates an entire class of defects of the form "the next step broke because the previous one did not put the data in state". Instead of hope — a guarantee of presence and type.

```python
@regular_aspect("Validation")
@result_string("validated_id", required=True)
async def validate_aspect(self, params, state, box, connections):
    return {"validated_id": params.order_id}

@summary_aspect("Creation")
async def create_summary(self, params, state, box, connections):
    state.validated_id  # guaranteed to be there — usable without a check
```

The analogy is postconditions in Design by Contract (Eiffel, contracts in Kotlin).

---

## Privacy and masking in logs

### Private names are blocked in log templates

Log templates substitute values with the `{%namespace.path}` syntax. Any path segment starting with `_` is blocked — at any nesting level, not only the last:

```
{%context._internal.key}    → LogTemplateError at '_internal'
{%context.__dict__.keys}    → LogTemplateError at '__dict__'
{%params.user._secret}      → LogTemplateError at '_secret'
```

This is not a convention but a check at the moment the template is rendered. Need to show data in a log — declare a public `@property`.

### Masking sensitive fields via `@sensitive`

`@sensitive` is hung on a `@property` **getter** (order: `@property` outside, `@sensitive` inside). When the logger renders a template and meets such a property, the value is automatically masked: a short prefix is shown (`max_chars`), the rest is replaced with the mask character (`char`, `*` by default).

```python
class UserParams(BaseParams):
    user_id: str
    password: str

    @property
    @sensitive(max_chars=0)
    def password_display(self) -> str:
        return self.password
```

The masking parameters are checked at decorator application: `enabled` — a `bool`; `max_chars` — a non-negative `int`; `char` — a string of exactly one character; `max_percent` — an `int` in the range 0..100. A violation of any of these is a `TypeError` or `ValueError` at class definition.

So, two independent layers of protection. The `_` block guards against accidentally printing internal attributes. `@sensitive` is an explicit intent to show a field in logs, but in masked form.

---

## Entity relations

Relations between entities are declared with fields of a container type and markers in `Annotated`. The framework guards several separate rules.

### The ownership compatibility matrix

Every ownership relation has an ownership type: **Composition** (strong), **Aggregation** (weak), **Association** (none). The reverse side must conform to the matrix:

| Side A | Allowed reverse side |
|--------|----------------------|
| `CompositeOne` / `CompositeMany` | `AssociationOne` / `AssociationMany` |
| `AggregateOne` / `AggregateMany` | `AssociationOne` / `AssociationMany` |
| `AssociationOne` / `AssociationMany` | any type |

Composite↔Composite, Aggregate↔Aggregate, Composite↔Aggregate are forbidden. The check is at `coordinator.build()`.

### Mandatory Inverse or NoInverse

Every ownership-relation field must have either `Inverse(TargetEntity, "field_name")` or `NoInverse()` in `Annotated`. The absence of both is an error at build. `NoInverse` explicitly states that the reverse side is intentionally absent — this is not the same as "forgot to specify".

```python
# ✓ explicit reverse side
customer: Annotated[
    AssociationOne[CustomerEntity],
    Inverse(CustomerEntity, "orders"),
] = Rel(description="The customer who placed the order")

# ✓ intentionally one-way link
audit_log: Annotated[
    CompositeMany[AuditLogEntity],
    NoInverse(),
] = Rel(description="Audit log")
```

`Inverse.field_name` cannot be an empty string (`ValueError`) or a non-string (`TypeError`); `target_entity` must be a type for an ownership relation. On a specialization head, `Inverse(field_name="record")` omits the target class because the alternatives already specify it.

### Mandatory Rel description

Every ownership-relation field must have `= Rel(description="...")` as its default value. An empty or whitespace-only description is a `ValueError` at class definition. The description is mandatory on both sides: the forward relation and the reverse one.

### The hydration invariant (fail-fast)

Relation containers separate the **identifier** (always available) from the **loaded object** (optional). Touching attributes of an unloaded container fails immediately — it does not return `None`:

| Situation | Error |
|-----------|-------|
| An entity field was not included in the partial load | `FieldNotLoadedError` (subclass of `AttributeError`) |
| Touching an attribute through an unloaded `AssociationOne` / `AggregateOne` etc. | `RelationNotLoadedError` (subclass of `AttributeError`) |
| Iterating or indexing an unloaded `*Many` container | `RelationNotLoadedError` |

For Many containers: `entities_loaded=False` with a non-empty `entities` tuple is a `ValueError` at creation. An empty `entities` with `entities_loaded=True` means "loaded, zero relations", not "not loaded".

### The id in a container cannot be None

`BaseRelationOne(id=None)` is a `ValueError`. A container must always know the identifier of the related entity, even if the object itself is not hydrated.

---

### Entity specialization: the build rules

A specialization declaration describes common information and the kinds of additional information that may accompany it. The common entity is the **head**; the detail classes are its **alternatives**. One head field, its code field, and its alternatives form an **axis**. The [relations tutorial](../tutorials/step-21-relations.md#generalization-and-specialization) introduces these terms and gives complete runnable declarations. This section specifies what the current implementation checks.

#### Declaration surface and checking time

On the head, write `Specialization` parameterized by the alternative class or union of classes, a `Classifier` naming the code field and the declared codes, and `Inverse(field_name="record")` naming their reverse field. On each alternative, write `Generalization[Head]`, a `Classifier` with that alternative's single code, and an `Inverse` identifying the head's specialization field. Supply relationship descriptions with `Rel`. These declarations describe domain objects; they do not specify a storage layout or establish Python inheritance between the head and alternatives.

There are three distinct checking moments:

| Moment | Checks relevant to specialization |
|---|---|
| Constructing a marker in an annotation | `Classifier.field` is a nonblank string; `codes` is a nonempty `Literal` of nonblank strings. Invalid arguments raise `TypeError` or `ValueError`. |
| Reading declarations and building the model graph | The resolver and declaration validator check the rules below. Machine creation includes graph construction and this validation, but graph construction can fail first. |
| Constructing a relation value | Pydantic checks the supplied object against the container's type argument. The containers are frozen after construction. This is separate from the declaration checks. |

`model_rebuild()` resolves Pydantic's forward type references. It does not replace AOA's declaration validation. The validator normally examines the currently loaded classes registered with `@entity`, excluding classes marked out of the graph model. Importing a model is therefore relevant; an unimported class is not available for this check.

#### Rules within an axis

| Declaration requirement | What is checked |
|---|---|
| The head field identifies a specialization | The resolver recognizes a parameterized `Specialization` container and requires a `Classifier` marker. A marker on an unrelated field is not sufficient to create an axis. |
| Alternatives are declared entities | Each listed class must carry entity declaration metadata. |
| The classifier names a usable data field | The name must occur in the head's Pydantic fields. The specialization field itself, another recognized specialization field, and an ownership relation cannot serve as the classifier. Properties and `ClassVar` attributes are not Pydantic fields. |
| Each alternative provides a reverse declaration | Its `Generalization` points to this head. Missing or wrongly targeted reverse declarations leave a head code without an owner. |
| An alternative supplies one code | There must be exactly one reverse field to that head and exactly one code on it. When the head names an inverse field, that name must match the reverse field. |
| Codes agree in both directions | Every head code must occur on an alternative, every alternative code must occur on the head, and the counts must agree. Two alternatives cannot own the same code in an accepted declaration. |
| Declared codes fit the classifier annotation | Each code is passed to a Pydantic `TypeAdapter` for that annotation. This uses normal Pydantic validation, including permitted coercions, rather than a strict string-type equality check. |

The code-to-class mapping comes from the alternatives' reverse declarations. It is not formed by zipping the head's code list with its union. The head code order supplies the order used for emitted forward edges and their `alternative_index`; it does not redefine which class owns a code. See the [reordered-code experiment](../../examples/step_21_relations/05_specialization_mapping.py).

Use the declared paired-marker form even though the current specialization validator does not enforce all the same mirroring rules as ownership relations. In particular, it does not require the head's `Inverse` marker or verify every reverse `Inverse` target/field. A bare `Generalization` on a class whose target declares no specialization axis does not, by itself, create a paired specialization. Do not treat successful construction of such declarations as proof of complete inverse validation.

#### Rules across axes

An alternative class may be claimed by only one head class. A head may have multiple specialization fields, but each must name a different classifier field. A chain of head-to-alternative relationships must not return to a class already in that chain: self-reference and longer cycles are invalid.

The current closure check has a stronger consequence than simply requiring matching inverse names. For **each** axis it rejects any other declared class that has a `Generalization` to that head but is absent from that axis's alternatives. It compares the head class, not the reverse field's `Inverse` name. Consequently, separate classifier fields do not make disjoint alternative sets on one head valid. The [two-axis example](../../examples/step_21_relations/11_specialization_two_axes.py) uses the same alternatives; the [different-set example](../../examples/step_21_relations/38_error_axis_subset.py) demonstrates the refusal.

#### Diagnostics and their limits

The dedicated validator raises `SpecializationDeclarationError` with the head class, specialization field, and explanation. The [diagnostic guide](../how-to/specialization-declaration-fails.md) gives independent broken declarations and repairs. An extra code on an alternative and a cycle between two distinct classes are both reachable errors; the guide includes actual examples of each.

Do not depend on a universal first-error order for arbitrary broken models. Declaration parsing, graph expansion, graph wiring, and the specialization validation pass occur at different points. For example, a head with a nonexistent code can cause `KeyError` while graph labels are assembled, before the dedicated validator can report the declaration error. The [machine-build experiment](../../examples/step_21_relations/39_error_machine_build.py) demonstrates this current limitation; the direct-validator experiment gives the more useful diagnostic.

#### Relation values and application responsibilities

`Specialization[T]` requires an `id` argument and a `variant` argument; `entity` defaults to `None`. `Generalization[T]` requires `id` and has the same optional `entity`. They are Pydantic models with frozen fields. A supplied entity is checked against `T` during normal construction. The type argument can be narrowed to one alternative. Reading `.entity` returns the supplied object or `None`; these containers do not proxy its attributes or perform loading.

The current field types are deliberately broader than the domain declaration: `id` is `Any` and `variant` is `str | None`. Requiring those arguments does not imply a non-null identifier or code. There is no built-in check that the head's classifier value, the link's `variant`, the object's class, its identifier, and its reverse link agree. There is also no automatic rejection of a string merely because it is absent from the declared code list. Use appropriate value annotations and explicit loading/application checks for those requirements.

The model build does not inspect stored data. It establishes neither completeness (every head object has corresponding details) nor data disjointness (only the appropriate kind of details exists for each object). It does not create database constraints or determine how many tables exist.

#### Graph and Maxitor

For a visible axis, the model graph contains one `entity_specialization` association edge per alternative, while the head field also remains an `EntityField` column. Forward-edge properties carry the field name, classifier field, this edge's code, its code-list index, and the complete code-to-class identifiers and display labels. The reverse declaration produces `parent_entity` generalization edges carrying the reverse field, head field, code, and head identifier. Neither direction is derived from Python subclassing.

`NoGraphEdge` on the head field suppresses the forward edges, not the field column or the reverse edges. The Maxitor store retains both edge families. Its full-graph view excludes the `Generalization` relationship, so reverse edges are absent there. The ERD builds a display group for multiple alternatives and one combined field row; those display groups are not extra entities in the model graph.

A single-alternative axis is accepted by the model. The current ERD emits no alternatives group and no replacement ordinary relation line for it. For the actual rendering, including the current arrow endpoint limitation, see [Step 26](../tutorials/step-26-maxitor.md#specialization-the-variants-in-one-frame).

## Lifecycle FSM

Every lifecycle template declared on an entity passes eight structural rules at `coordinator.build()`. A violation of any is a `LifecycleValidationError` with the entity name, the field name, and a description of the violation.

1. Every state has a `.initial()`, `.intermediate()`, or `.final()` label.
2. There is at least one initial state.
3. There is at least one final state.
4. Final states have no outgoing transitions.
5. Every transition references an existing state.
6. Every non-final state has at least one outgoing transition.
7. From every initial state at least one final state is reachable.
8. Every non-initial state is the target of at least one transition.

At runtime `lifecycle.transition("shipped")` raises an error if the transition is not allowed from the current state — the guard against "an order goes from `cancelled` to `shipped`" works both at build and on every call.

Maxitor draws lifecycles as FSM diagrams straight from the entity code. The analogs are XState in the JS world, statecharts in aviation and medical software.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
