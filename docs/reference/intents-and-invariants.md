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

Access is a cascade of three levels, each of which can deny: role (`@check_roles`) → `guard=`/`grant.when=` → `access_decide`. Each level carries its own invariants:

- **`grant.when=`/`guard=` are synchronous functions returning strictly `bool`.** Checked at class definition, not at runtime: an `async def` in either raises `AccessConditionAsyncError` immediately — an un-awaited coroutine is always truthy, and an async condition would silently wave every check through.
- **`access_decide` defaults to `True`.** The method is declared on `BaseAction`; level 3 restricts nothing until an action explicitly overrides it. Denial at any of the three levels is the same `AuthorizationError`, differing only in `level` (`1` — role, `2` — `guard=`/`grant.when=`, `3` — `access_decide`).
- **`machine.check_access_decide` is capped by list size.** The list form of `(action, params)` pairs — the `max_check_access_decide_batch_size` constructor parameter (100 by default) on `ActionProductMachine`; a longer list is rejected with `CheckAccessDecideBatchSizeExceededError` before a single item is checked.
- **Denial at any of the three levels is an `AuthorizationError` that flies past `@on_error`/the saga.** Role, `guard=`, and `access_decide` are checked before `_execute_pipeline_aspects`: no `@regular_aspect`/`@summary_aspect` has run yet, so there's nothing to roll back. `@on_error` is a recovery mechanism for business-logic failures inside the pipeline, not a place for authorization decisions.

---

## Mandatory domain

Every operation and every domain entity is bound to a domain via `@meta(domain=...)` or `@entity(domain=...)`.

An operation without a domain is a "lost" component: it will not be in the system graph, not in Maxitor, not in the access matrix. Domains are the basis of the package-boundary invariant: they set the logical division that CI checks statically.

---

## A single summary aspect

Every operation has exactly one method marked `@summary_aspect`, and it must return a typed `Result`.

Otherwise the operation has no explicit exit point: the result could be assembled in several places, partially overwritten, or not assembled at all. The machine checks this at startup and raises `MissingSummaryAspectError`.

---

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

Every relation has an ownership type: **Composition** (strong), **Aggregation** (weak), **Association** (none). The reverse side must conform to the matrix:

| Side A | Allowed reverse side |
|--------|----------------------|
| `CompositeOne` / `CompositeMany` | `AssociationOne` / `AssociationMany` |
| `AggregateOne` / `AggregateMany` | `AssociationOne` / `AssociationMany` |
| `AssociationOne` / `AssociationMany` | any type |

Composite↔Composite, Aggregate↔Aggregate, Composite↔Aggregate are forbidden. The check is at `coordinator.build()`.

### Mandatory Inverse or NoInverse

Every relation field must have either `Inverse(TargetEntity, "field_name")` or `NoInverse()` in `Annotated`. The absence of both is an error at build. `NoInverse` explicitly states that the reverse side is intentionally absent — this is not the same as "forgot to specify".

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

`Inverse.field_name` cannot be an empty string (`ValueError`) or a non-string (`TypeError`); `target_entity` must be a type.

### Mandatory Rel description

Every relation field must have `= Rel(description="...")` as its default value. An empty or whitespace-only description is a `ValueError` at class definition. The description is mandatory on both sides: the forward relation and the reverse one.

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
