# Intents and Invariants

In AOA every business operation is described through **intents** — declarations of what must be true: who has access, what the operation depends on, how a step rolls back. An intent is a decorator: `@meta`, `@check_roles`, `@depends`, `@compensate`, `@on_error`, or a result checker.

When you declare an intent, you hand it to the system. An **invariant** is what the system takes responsibility for in return: it checks at startup, at runtime, at build time, or in CI. It does not suggest, does not remind — it checks.

But the relationship goes both ways: the system also makes demands of you. You cannot write an operation without roles, without a domain, without an exit point. These are not team conventions — they are a grammar you cannot technically violate.

---

## Contents

- [What the system requires from you](#what-the-system-requires-from-you)
- [What the system guarantees in return](#what-the-system-guarantees-in-return)
- [When invariants are checked](#when-invariants-are-checked)
- [Naming invariant](#naming-invariant)
- [DAG invariant — acyclic dependencies](#dag-invariant--acyclic-dependencies)
- [Required roles invariant](#required-roles-invariant)
- [Required domain invariant](#required-domain-invariant)
- [Summary aspect invariant](#summary-aspect-invariant)
- [Compensator invariant](#compensator-invariant)
- [Include contract](#include-contract)
- [State contract invariant — checkers](#state-contract-invariant--checkers)
- [Logging invariants: privacy and masking](#logging-invariants-privacy-and-masking)
- [Entity relation invariants](#entity-relation-invariants)
- [Lifecycle FSM invariant](#lifecycle-fsm-invariant)

---

## What the system requires from you

AOA does not allow a "bare" operation. Every operation must have roles, a domain, and an exit point — otherwise the machine will not start:

| Required | How to declare |
|----------|----------------|
| Access roles | `@check_roles(...)` |
| Domain | `@meta(domain=...)` |
| Exit point with result | `@summary_aspect` |
| Acyclic dependency graph | `@depends` is validated at startup |

If an operation is open to everyone, you must explicitly write `@check_roles(NoneRole)`. This is not a formality — it is a deliberate intent, as opposed to the silent absence of a check.

---

## What the system guarantees in return

Once an intent is declared, the system takes it under control:

| You declared | System guarantees |
|--------------|-------------------|
| `@check_roles(AdminRole)` | Role is checked on every call |
| `@depends(PaymentAction, mode=UseCase.include)` | `PaymentAction` will actually execute in this session |
| `@result_string("validated_id", required=True)` | The next step will receive `state.validated_id` of the correct type |
| `@compensate("charge_aspect", ...)` | On failure, rollback will run automatically |

---

## When invariants are checked

| Moment | What is checked |
|--------|-----------------|
| **Application startup** | Graph structure, naming, required declarations, absence of cycles |
| **Runtime (every call)** | Roles, aspect contracts |
| **After root session completes** | Execution of all `UseCase.include` dependencies |
| **Build time** | Lifecycle FSM, transition correctness |
| **CI** | Package boundaries, class naming |

---

## Naming invariant

A suffix is not a style choice. Every suffix is enforced by a base class or decorator: a violation raises `NamingSuffixError` at class or method definition time, before the application starts.

Suffixes become visual anchors: `...Resource` means an external system adapter; `...Action` means a business operation. Context is read before the file is even opened.

### Complete suffix table

| What | Suffix | Where checked | Error |
|------|--------|---------------|-------|
| Subclass of `BaseAction` | `Action` | `__init_subclass__` at class definition | `NamingSuffixError` |
| Subclass of `BaseDomain` | `Domain` | `__init_subclass__` at class definition | `NamingSuffixError` |
| Subclass of `BaseRole` | `Role` | `__init_subclass__` at class definition | `NamingSuffixError` |
| Subclass of `BaseEntity` | `Entity` | `__init_subclass__` at class definition | `NamingSuffixError` |
| Method with `@regular_aspect` | `_aspect` | decorator at method definition | `NamingSuffixError` |
| Method with `@summary_aspect` | `_summary` | decorator at method definition | `NamingSuffixError` |
| Method with `@compensate` | `_compensate` | decorator at method definition | `NamingSuffixError` |
| Method with `@on_error` | `_on_error` | decorator at method definition | `NamingSuffixError` |

### Additional constraints

- The description in `@regular_aspect("...")` and `@summary_aspect("...")` cannot be an empty string or consist only of whitespace — `ValueError` when the decorator is applied.
- Indirect subclasses are checked the same as direct ones: `class SpecificTask(BaseTaskAction)` without the `Action` suffix will also fail.

### Examples

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

## DAG invariant — acyclic dependencies

The dependency graph between operations (`@depends`) must be acyclic. If A depends on B which depends on A — the machine will refuse at startup with `CyclicDependencyError` and show the cycle chain.

Without this invariant it is impossible to guarantee execution order. A cycle also makes the Include contract unresolvable — include requires the dependency to actually execute, but in a cycle neither side can finish first.

Analogy: topological sort in build systems (Make, Gradle, Airflow).

---

## Required roles invariant

Every public operation must have `@check_roles`. Without this decorator the machine will not run the operation — it does not warn, does not log, it refuses.

`@check_roles` does not implement authorization business logic — it guarantees that **a declaration exists** and is checked on every call. This is a different level: a developer cannot accidentally forget to write the check.

```python
# ✗ no @check_roles — machine will refuse
@meta(description="Delete order", domain=StoreDomain)
class DeleteOrderAction(BaseAction[...]): ...

# ✓ open to everyone — stated explicitly
@meta(description="Get status", domain=StoreDomain)
@check_roles(NoneRole)
class GetOrderStatusAction(BaseAction[...]): ...
```

---

## Required domain invariant

Every operation and domain entity must be bound to a domain via `@meta(domain=...)` or `@entity(domain=...)`.

An operation without a domain is a "lost" component: it will not appear in the system graph, will not show up in Maxitor, will not be included in the access matrix. Domains are the foundation for the package boundary invariant — they define the logical divisions that CI checks statically.

---

## Summary aspect invariant

Every operation must have exactly one method marked with `@summary_aspect`. That method must return a typed `Result`.

Without this, an operation has no explicit exit point: the result may be formed in multiple places, partially overwritten, or not formed at all. The machine checks at startup and raises `MissingSummaryAspectError`.

---

## Compensator invariant

`@compensate(target, description)` must reference an existing `@regular_aspect` in the same class. A compensator without a corresponding aspect is not allowed — it is a "dead rollback" that will never fire.

Checked at startup. The compensator method name must end with `_compensate`.

```python
# ✓ charge_aspect exists — charge_compensate is valid
@regular_aspect("Charge funds")
async def charge_aspect(self, ...): ...

@compensate("charge_aspect", "Refund funds")
async def charge_compensate(self, ...): ...
```

---

## Include contract

If an operation declares a dependency with `UseCase.include`, the dependent operation **must actually execute** within the same root session — not just declared, but genuinely called via `await box.run(...)`.

Checked after the root session completes, before `emit_global_finish`. If the contract is violated — `IncludeContractViolationError` listing the unexecuted dependencies in `missing_include_types`.

Difference from `UseCase.extend`: `extend` — the dependency may or may not execute depending on operation logic. `include` — mandatory on every successful completion of the root operation.

**Exception:** if the root operation is served from cache (cache hit), the check does not run — nested calls from the previous materialization are not part of the current ContextVar session.

**Interaction with `@on_error`:** if the pipeline returned a result via an error handler (rather than summary), the machine still considers the execution successful and the include check still runs.

---

## State contract invariant — checkers

Decorators `@result_string`, `@result_instance`, `@result_bool`, and their counterparts declare the result contract of an aspect: which key must appear in `state` and of what type. If the aspect did not return the expected value — error immediately, not in the next step.

This eliminates an entire class of defects: "the next step broke because the previous one didn't put data in state." Instead of hope — a guarantee of type and presence.

```python
@regular_aspect("Validation")
@result_string("validated_id", required=True)
async def validate_aspect(self, params, state, box, connections):
    return {"validated_id": params.order_id}

@summary_aspect("Creation")
async def create_summary(self, params, state, box, connections):
    state.validated_id  # guaranteed — safe to use without a check
```

Analogy: post-conditions in Design by Contract (Eiffel, Kotlin contracts).

---

## Logging invariants: privacy and masking

### Private names are blocked in log templates

Log templates use `{%namespace.path}` syntax to interpolate values. Any dot-path segment starting with `_` is blocked — at any level of nesting, not only the last:

```
{%context._internal.key}    → LogTemplateError on '_internal'
{%context.__dict__.keys}    → LogTemplateError on '__dict__'
{%params.user._secret}      → LogTemplateError on '_secret'
```

This is not a convention — it is a check at template render time. If data needs to appear in a log, declare a public `@property`.

### Masking sensitive fields with `@sensitive`

`@sensitive` is a decorator for `@property`. When the logger renders a template and encounters such a property, the value is automatically masked: only a short prefix is shown (`max_chars`), the rest is replaced by a mask character (`char`, default `*`).

```python
class UserParams(BaseParams):
    user_id: str
    password: str

    @sensitive(max_chars=0)
    @property
    def password_display(self) -> str:
        return self.password
```

Masking parameters are validated when the decorator is applied:
- `enabled` — must be `bool`
- `max_chars` — non-negative `int`
- `char` — a string of exactly one character
- `max_percent` — `int` in range 0..100

Violating any of these constraints raises `TypeError` or `ValueError` at class definition time.

**Summary:** two independent protection layers. The `_` block guards against accidental output of internal attributes. `@sensitive` is an explicit intent to show a field in logs — but masked.

---

## Entity relation invariants

Relations between entities are declared as fields with a container type and markers in `Annotated`. The framework enforces several distinct rules.

### Ownership compatibility matrix

Every relation has an ownership type: **Composition** (strong), **Aggregation** (weak), **Association** (no ownership). The inverse side must conform to the matrix:

| Side A | Allowed inverse side |
|--------|----------------------|
| `CompositeOne` / `CompositeMany` | `AssociationOne` / `AssociationMany` |
| `AggregateOne` / `AggregateMany` | `AssociationOne` / `AssociationMany` |
| `AssociationOne` / `AssociationMany` | any type |

Composite↔Composite, Aggregate↔Aggregate, Composite↔Aggregate — forbidden. Checked at `coordinator.build()`.

### Required Inverse or NoInverse

Every relation field must have either `Inverse(TargetEntity, "field_name")` or `NoInverse()` in `Annotated`. The absence of either is an error at build time. `NoInverse` explicitly signals that the reverse side is intentionally absent — it is not the same as "forgot to specify."

```python
# ✓ explicit inverse
customer: Annotated[
    AssociationOne[CustomerEntity],
    Inverse(CustomerEntity, "orders"),
] = Rel(description="Customer who placed the order")

# ✓ explicitly one-directional
audit_log: Annotated[
    CompositeMany[AuditLogEntity],
    NoInverse(),
] = Rel(description="Audit trail")
```

`Inverse.field_name` cannot be an empty string (`ValueError`) or a non-string (`TypeError`). `target_entity` must be a type.

### Required Rel description

Every relation field must have `= Rel(description="...")` as its default. An empty or whitespace-only description raises `ValueError` at class definition. The description is required on both sides: both the forward and the inverse relation.

### Hydration invariant (fail-fast)

Relation containers separate the **identifier** (always available) from the **loaded object** (optional). Accessing attributes of an unloaded container raises an error immediately — not `None`:

| Situation | Error |
|-----------|-------|
| Entity field not included in partial load | `FieldNotLoadedError` (subclass of `AttributeError`) |
| Attribute access through an unloaded `AssociationOne` / `AggregateOne` etc. | `RelationNotLoadedError` (subclass of `AttributeError`) |
| Iteration or indexing of an unloaded `*Many` container | `RelationNotLoadedError` |

For Many containers: `entities_loaded=False` with a non-empty `entities` tuple raises `ValueError` at construction. An empty `entities` with `entities_loaded=True` means "loaded with zero relations" — not "not loaded."

### id in a container cannot be None

`BaseRelationOne(id=None)` raises `ValueError`. A container must always know the identifier of the related entity, even if the object is not hydrated.

---

## Lifecycle FSM invariant

Every lifecycle template declared on an entity passes eight structural rules when `coordinator.build()` is called. Violating any of them raises `LifecycleValidationError` with the entity name, field name, and a description of the violation.

**Eight rules:**

1. Every state is tagged with `.initial()`, `.intermediate()`, or `.final()`.
2. At least one initial state exists.
3. At least one final state exists.
4. Final states have no outgoing transitions.
5. Every transition references an existing state.
6. Every non-final state has at least one outgoing transition.
7. From every initial state, at least one final state is reachable.
8. Every non-initial state is the target of at least one transition.

At runtime, `lifecycle.transition("shipped")` raises an error if the transition is not allowed from the current state — protection against "order moves from `cancelled` to `shipped`" exists both at build time and on every call.

Lifecycles are visualized in Maxitor as FSM diagrams generated directly from entity code.

Analogues: XState (JS); statecharts in aviation and medical software.
