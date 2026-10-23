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
| Entity-kind descendant | `CoreEntity`, `AssocEntity`, `DetailEntity`, `SpecEntity`, `EnumEntity` or `StateEntity`, matching its kind base | Inheritance hooks at class definition, including intermediate and undecorated classes | `NamingSuffixError` |
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

A role also declares its lifecycle mode, once, with `@role_mode`. The set is closed — `ALIVE`, `DEPRECATED`, `SILENCED`, `UNUSED` — and the argument is checked where it is written: a string, a member of another enum or a class is refused while the module is imported, and the refusal names the role, the value that arrived and all four members. What a mode *means* is decided by its consumer, never by the decorator: `@check_roles` refuses to require an `UNUSED` role and warns about a `DEPRECATED` one, and the access check grants nothing to a `SILENCED` one.

```python
# ✗ the string the enum carries — RoleModeDeclarationError at import
@role_mode("alive")
class ViewerRole(ApplicationRole): ...


# ✓ the member — and what it means is still the consumer's business
@role_mode(RoleMode.ALIVE)
class ViewerRole(ApplicationRole): ...
```

[`examples/step_03_authorization_and_roles/17_a_wrong_role_mode.py`](../../examples/step_03_authorization_and_roles/17_a_wrong_role_mode.py) runs both refusals, and the `UNUSED` refusal that follows from `@check_roles`.

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

Otherwise the operation has no explicit exit point: the result could be assembled in several places, partially overwritten, or not assembled at all. An operation with none raises `MissingSummaryAspectError` at startup; an operation with **two** raises `DuplicateSummaryAspectError`, which names both methods — before this rule, a second summary surfaced as a graph error about a missing node, a message about a node the developer never wrote.

The answer is checked against the operation's `Result` twice, and the two checks catch different mistakes. At assembly, a summary annotated with anything else — `Any`, another operation's result — is refused with `AspectSignatureError`, because the annotation is a promise the machine can read before serving a call. At run time, a method that contradicts its own annotation — an annotated `ResultStub` that returns a `dict` — is refused with `ActionResultTypeError`, naming the operation, the declared `Result` and what actually came back. A `Result` **supertype** is accepted (`-> BaseResult`), because it promises nothing false.

---

## What an aspect declaration must be

The four methods the machine calls itself — `@summary_aspect`, `@regular_aspect`, `@on_error`, `@compensate` — are declarations, and their signature is part of the contract rather than the author's private business. The rules are the object check's rules (`@access_decide`, below), applied to all four:

| Decorator | Parameters, in this order |
| --- | --- |
| `@summary_aspect` | `self, params, state, box, connections` |
| `@regular_aspect` | the same |
| `@on_error` | the same, then `error` |
| `@compensate` | `self, params, state_before, state_after, box, connections, error` |

`ctx` is appended last when, and only when, `@context_requires(...)` sits under the declaration and can be seen by it.

- **The names are the engine's names, in the engine's order.** They are not a style preference: the pipeline passes these values by position, so `self, p, state, box, connections` runs and `p` receives the parameters object. Renaming or reordering is refused where the method is declared, with `AspectSignatureError` naming both orders.
- **Every parameter but `self` carries an annotation, and so does the return.** A bare one is refused at declaration.
- **The annotations resolve to what the pipeline hands over**, checked when the capability is assembled, because `params` is annotated with the operation's own `Params` — a name that does not exist while the class body runs. `params`: `BaseParams` or the operation's `Params`; `state`: `BaseState`; `box`: `ToolsBox`; `connections`: `Connections`; `ctx`: `ContextView`; `error`: `Exception` or the class the handler was declared for; a compensator's `state_after`: `BaseState | None`, because the aspect it compensates may not have finished.
- **The signature must be callable by position.** Keyword-only parameters, `*args`, `**kwargs` and defaults on values the pipeline always supplies are refused.
- **The return is the one the pipeline reads**: a summary and an on-error handler answer with the operation's `Result`, a regular aspect returns a state fragment `dict[str, Any]`, a compensator returns nothing.
- **The moment is in the message.** A refusal made while the class body executes says so; one made while the capability is assembled says the class body had already run, so a reader is not sent back to code that is already correct.

The rules are the subject of [`examples/step_01_Action_and_pipeline/05_aspect_declarations.py`](../../examples/step_01_Action_and_pipeline/05_aspect_declarations.py), which runs each refusal and prints what comes back.

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
- **The signature is fixed.** `(self, params, box, connections)`, plus the trailing `ctx` that `@context_requires` adds — names in that order, every parameter annotated, the annotations resolving to what the step hands over: `params` (`BaseParams` or the operation's own `Params`), `box: ToolsBox`, `connections: Connections`, `ctx: ContextView`.
- **It answers with a verdict.** A return of `Verdict` or one of its three answers; anything else is refused at assembly, and at run time a check that returns something else becomes `Undecided` rather than permission.

**Context is declared, never granted.** As with every declared behaviour, the context reaches the check only through `@context_requires` under the declaration: the trailing `ctx` then exists, it is a `ContextView` limited to the keys that were named, and another key raises `ContextAccessError`. There is no parameter that hands over the whole context.

The refusal rules above are the subject of [`examples/step_03_authorization_and_roles/06_the_declaration.py`](../../examples/step_03_authorization_and_roles/06_the_declaration.py), which runs each of them.

## A correct compensator

`@compensate(target, description)` must reference an existing `@regular_aspect` of the same class. A compensator without a corresponding aspect is not allowed — it is a "dead rollback" that will never fire.

Checked at startup. The compensator method name ends with `_compensate`, and its signature is the contract above: the two states it is given differ, `state_before` is always a state while `state_after` is `None` when the compensated aspect did not finish, and its return is ignored — so `-> None` is what it declares.

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
from typing import Any

from aoa.action_machine.model import BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox


@regular_aspect("Validation")
@result_string("validated_id", required=True)
async def validate_aspect(
    self, params: BaseParams, state: BaseState, box: ToolsBox, connections: Connections
) -> dict[str, Any]:
    return {"validated_id": params.order_id}


@summary_aspect("Creation")
async def create_summary(
    self, params: BaseParams, state: BaseState, box: ToolsBox, connections: Connections
) -> BaseResult:
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

## Entity kinds

Every application entity chooses one kind base. Core describes an independent domain object; Assoc a technical connection without business data; Detail an identifiable part of an owner; Spec variant-specific data sharing the head's identity; Enum a shared reference value; State a lifecycle state description. These meanings are explained with separate runnable examples in [Step 20](../tutorials/step-20-entity.md).

The hierarchy performs structural checks when Python creates a class, before decorators run. `BaseEntity` owns the common hierarchy checks; each kind base owns its suffix check. The framework recognises a kind base by direct inheritance from `BaseEntity` and its own `__init_subclass__` hook. The six supplied bases define the supported domain kinds; an application selects one of them. `@entity` supplies model metadata rather than performing these hierarchy checks.

| Case | Behaviour |
| --- | --- |
| Ordinary application class inherits `BaseEntity` directly | `DeclarationStructureError`: select a kind base |
| Two different kind bases occur in the inheritance chain | `DeclarationStructureError` |
| Descendant has a missing or mismatched kind suffix | `NamingSuffixError` |
| Intermediate or undecorated descendant | Same hierarchy and suffix checks; no exemption |
| One kind plus an ordinary Python mixin | Accepted |
| Construction of one of the six kind bases | `TypeError` at the attempted construction |
| Exported Entity node | Required `properties.entity_kind`; the Maxitor store preserves the value |
| `BaseStateEntity` descendant | Requires the `StateEntity` suffix; excluded from ordinary Entity nodes |

The six wire values are `core`, `assoc`, `detail`, `spec`, `enum` and `state`. Normal Entity export does not emit `state`: lifecycle states have their own graph representation. All six kind bases are excluded from discovery. An application-specific intermediate class that should not be discovered uses `@exclude_graph_model`; a `Base` name prefix alone is insufficient.

The semantic contracts are not a new set of automatic database checks. The marker does not inspect fields to identify business data, enforce a composite primary key, compare a specialization's key with its head's, or perform ownership deletion. `get_primary_key()` continues to use `id` by convention. Relation and lifecycle validation remain separate. Maxitor carries the classification but does not yet hide associative nodes based on it.

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
    AssociationOne[CustomerCoreEntity],
    Inverse(CustomerCoreEntity, "orders"),
] = Field(description="The customer who placed the order")

# ✓ intentionally one-way link
audit_log: Annotated[
    CompositeMany[AuditLogEntity],
    NoInverse(),
] = Field(description="Audit log")
```

`Inverse.field_name` cannot be an empty string (`ValueError`) or a non-string (`TypeError`); `target_entity` must be a type for an ownership relation. On a specialization head, `Inverse(field_name="record")` omits the target class because the alternatives already specify it.

### Relation descriptions and defaults

Every ownership, specialization and generalization relation requires a non-blank `Field` description. Missing or blank descriptions raise `EntityFieldDeclarationError` when the graph is built. The description is metadata, not an instance default. Required relation fields have no default. Only a nullable relation may use `default=None`; factories and all other defaults are refused. The rule applies even when an edge is hidden.

A bare Core, Assoc, Detail or Spec field, including optional and collection forms, is refused. Use a relation container, or `Annotated[EntityType, NoRelation("reason")]` for an embedded value. A State field uses a lifecycle type. See [complete declarations and refusals](../how-to/explicit-entity-fields.md).

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

### Closed dictionaries and declared values

Both dictionaries and lifecycle statuses declare catalogue members with `value(...)`,
imported from `aoa.action_machine.domain`. The factory records keyword arguments; the
class-creation hook constructs the members after the model exists. No custom namespace
substitutes a factory for the class name. `members`, `codes()`, `by_code()` and
`entity_type` retain their catalogue meanings. Duplicated codes fail at class creation.

A dictionary supplies required nonblank `code` and `display_name`, and its fields may be
inherited. Its catalogue is its own: `@entity` rejects an empty dictionary, while an
undecorated intermediate may be empty. A state subclass without new declarations can
inherit its parent's catalogue instead.

| Boundary | Contract |
| --- | --- |
| Dictionary property declaration | Supported scalar/date/time/UUID types, Enum, Literal, unions and tuples; list/dict/set/frozenset/Any/nested models are refused, including inside unions or tuples |
| Runtime reference | A declared instance or mapping with code; copied or foreign instances, unknown/missing/blank codes, bare strings and unknown top-level keys are refused |
| Reference descriptions | Incoming display_name and properties do not change the declared value; the code selects it |
| Optional reference | None only when the containing field permits it; an unknown code never becomes absence |
| Export | to_reference() equals model_dump(mode="json"); field serializers run and extra fields appear under properties |
| Input schema | Requires code, allows optional label/properties and rejects unknown top-level keys; runtime still checks membership and whitespace-only codes |
| Output schema | Requires code/display_name/properties, describes the emitted type of each extra property and rejects unknown nested keys; nested properties require every emitted property, including null values, and an excluded property is absent |
| Completed values | Checked after user validators; Literal choices match by type and value, and bool does not satisfy int |
| Nullability | A union accepts None only when included; Literal may list None explicitly; a property annotated only None is refused |
| Tuple properties | Each item follows its annotation; a refusal identifies the item index |
| Graph | The dictionary Entity node carries properties.values; references carry reference_qualname; values are not separate nodes |

The property check inspects the annotation when the class is created and the completed member
after custom validators run: a result outside the declared types, outside a `Literal`'s
choices, or null where the union excludes it is refused. Serialization schemas retain the
definitions used by Enum properties. A state's property types remain unrestricted by the
dictionary rule, and frozen models do not recursively freeze mutable state properties. The
[dictionary guide](../tutorials/step-20-dictionaries.md) demonstrates the supported paths
and documents these limits.

### Entity specialization: the build rules

A **head** contains common information. Its **alternatives** contain variant-specific
information about the same object. An **axis** consists of one specialization field,
its dictionary and its alternatives. The
[relations tutorial](../tutorials/step-21-relations.md#generalization-and-specialization)
provides a complete model before introducing the individual operations.

#### Declaration and checking time

The head declares `Specialization[Alternatives, Dictionary]`, optionally unioned with
`None`, and normally `Inverse(field_name="record")`. Each alternative declares
`Generalization[Head]`, `Classifier(variant=Dictionary.VALUE)` and the
paired `Inverse(Head, "pressing")`. Use `Field(description=...)` for descriptions.
The head has no classification marker or duplicated selector. A single alternative is
allowed; one type is used instead of a union in the first argument.

| Moment | Checks |
| --- | --- |
| Dictionary class creation | Value field validation and unique codes; `@entity` then requires a nonempty catalogue |
| Marker construction | `field` must be a nonblank string; `variant` must be a `BaseEnumEntity` instance; membership is checked at model build |
| Type resolution | `model_rebuild()` resolves forward references; it is not model-wide validation |
| Model build | Dictionary, membership, coverage and relationships are checked across loaded declarations |
| Container construction | The dictionary resolves `variant`, the first type argument checks `entity`, and a loaded class's declared value must be the identical selected object |

`BaseSpecEntity.declared_variant` reads the resolved marker, including after a forward
reference is rebuilt. It is declaration metadata, not another per-instance selector.

#### Rules within an axis

| Requirement | Refusal |
| --- | --- |
| Second type argument is a nonempty decorated `BaseEnumEntity` descendant | Missing, unrelated, undecorated or empty dictionary |
| No `Classifier` on the head field | An additional classification declaration on the head |
| Each alternative is registered with `@entity` | An alternative with no entity declaration |
| Each alternative names a member of this dictionary by identity | Missing, copied or foreign value, even with a matching code |
| Exactly one reverse `Generalization` points to the head | Missing or ambiguous reverse declaration |
| `Classifier.field` names the reverse field it annotates | A different or nonexistent field name |
| Head `Inverse.field_name`, if supplied, matches that reverse field | Mismatched paired name |
| Each dictionary value has exactly one alternative | Missing alternative, duplicated ownership or mismatched counts |

The resolver derives the mapping from reverse declarations. Dictionary order supplies
forward-edge order and `alternative_index`; union order does not assign values to classes.
No class-to-table mapping or database constraint is generated.

#### Rules across axes and current limits

One dictionary may classify several axes, each with complete coverage. An alternative
class belongs to one head class. Specialization chains must not form cycles. The current
closure check compares reverse links by head class: every axis must include every class
that generalizes to that head. Thus the
[two-axis example](../../examples/step_21_relations/11_specialization_two_axes.py) shares
alternatives, while the
[subset example](../../examples/step_21_relations/38_error_axis_subset.py) is refused.
Independent disjoint alternative sets on one head are not supported by this check.

Use the paired `Inverse` declarations shown in the tutorial. The specialization validator
does not require a head `Inverse` or enforce every reverse `Inverse` target/field check
performed for ownership relations. A bare `Generalization` to a head without an axis
does not establish a validated specialization.

#### Runtime values and diagnostics

`Specialization[T, D]` requires `id` and `variant`; `entity` defaults to `None`.
`Generalization[T]` requires `id` and also has an optional `entity`. Both are frozen.
They expose the loaded object through `.entity` without attribute proxying or a query.
A known variant with `entity=None` is different from an optional head field set to `None`.
An unknown code is an error in either case.

The resource resolves stored codes, chooses what to load and maintains identity
consistency. Identifiers are typed as `Any`; the containers do not compare the head's
identifier, the link identifier and the loaded object's identifier, or inspect storage
for missing/duplicate rows. Partial or explicitly unvalidated construction APIs do not
replace normal validation.

The direct declaration validator raises `SpecializationDeclarationError`. Container
validation raises Pydantic `ValidationError`; `by_code` raises `KeyError`. Malformed
annotations can fail earlier while Python or Pydantic processes the class. Normal machine
creation can also encounter graph-construction errors before the dedicated validator.
The [diagnostic guide](../how-to/specialization-declaration-fails.md) isolates each failure
with a script and notebook; it does not promise a universal first-error order.

#### Graph and Maxitor

Each visible alternative has a forward `entity_specialization` edge carrying its code,
index, field and dictionary identifiers/label. There is no `classifier_field` on that edge.
Reverse `parent_entity` edges describe generalization. These are model relationships, not
Python inheritance or stored-object links.

`NoGraphEdge` on the head field suppresses forward edges while preserving the field and
reverse edges. Maxitor uses the forward edges to group multiple alternatives and label
the group by its dictionary. A single alternative has no group; its reverse generalization
can still appear as a relation. Dictionary cards show value codes, labels and descriptive
properties. See [Step 26](../tutorials/step-26-maxitor.md#specialization-the-variants-in-one-frame).


## Lifecycle FSM

A lifecycle axis is one aspect of an entity's progress, with its own possible states and transitions. For example, payment and delivery may have separate lifecycles. `BaseStateEntity` describes a possible status; a `Lifecycle` instance holds a reference to the selected declared status object. The state type declares its own statuses and carries their catalogue — `members`, `codes()`, `by_code()` and `entity_type`; the axis names that type as `Lifecycle[OrderStateEntity]`.

```python
from aoa.action_machine.domain import BaseStateEntity, Lifecycle, value


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    NEW = value(code="new", display_name="New")
    CONFIRMED = value(code="confirmed", display_name="Confirmed")
    SHIPPED = value(code="shipped", display_name="Shipped")


class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Declare the allowed order transitions; the statuses live on the type."""

    _template = (
        Lifecycle()
        .state(OrderStateEntity.NEW)
        .to(OrderStateEntity.CONFIRMED)
        .initial()
        .state(OrderStateEntity.CONFIRMED)
        .to(OrderStateEntity.SHIPPED)
        .intermediate()
        .state(OrderStateEntity.SHIPPED)
        .final()
    )
```

| Contract | Behaviour |
| --- | --- |
| Status fields | `code` and `display_name` are required non-blank strings; extra domain fields must be declared on the status subclass. Status objects reject attribute reassignment; nested mutable values are not recursively frozen. |
| Status catalogue | Status attributes are declared on the state type and collected in declaration order; their codes must be unique within the type and every status has that concrete type. |
| Lookup | `members` is a tuple; `codes()` returns a list in declaration order; `entity_type` is the type; `by_code(code)` returns the declared object or raises `KeyError`. All four live on the state type. |
| Declaring a template | `.state(status)` and `.to(*statuses)` take status objects, not strings. Every referenced status must be a declared member of the axis's state type, and every declared status must appear as a state; a foreign or missing status is refused at class definition. |
| Inheritance | A subclass without statuses inherits its parent's catalogue; a subclass with statuses gets its own. The axis reads the state type from `Lifecycle[StateType]`. |
| Classification | `.initial()`, `.intermediate()` and `.final()` belong to the template; a status field does not imply a classification. The same description may be classified differently in different templates. |
| Runtime | The constructor and `transition(target)` take code strings and resolve them to declared status objects. `current_status` returns that exact object; `current_state` returns its code. No separate current code is stored. A transition checks the edge and creates a new Lifecycle, not a new status object, leaving the original unchanged. |
| Current metadata | `current_state_info` still returns the template's `StateInfo`, with classification and transitions. Reading current-state properties on a template raises `RuntimeError`. |
| Equality and hashing | Use the concrete lifecycle class and current code. Domain fields do not participate, including unhashable fields. Template repr, equality and hashing retain their unset-state behaviour. |
| Status access on a lifecycle | `get_state_entity(code)` returns the attached object or `None`; `get_state_entities()` returns a copy of the mapping. |
| Graph export | The state keeps its code-based id and template classification. The label comes from `display_name`; `properties.attributes` contains the status's JSON-serialized fields, except fields excluded from serialization. A non-serializable value fails export. Status types do not become `Entity` nodes. |
| Maxitor response | The diagram state attributes contain only `code`, `display_name`, `sort_order`, `color` and `fill_color` when supplied. Other domain fields remain in the full graph. |
| Maxitor presentation | Initial states come first in the returned list, then integer `sort_order` (zero if absent or not an integer), then code. This does not prescribe screen coordinates. `color` overrides the outline, `fill_color` the fill; absent or unusable colour values use the existing palette. |

A malformed status raises Pydantic `ValidationError` when created. Vocabulary errors happen at class definition: duplicate codes or a new template without members raise `ValueError`; mixed types, a non-Lifecycle base, or a foreign status raise `TypeError`. Passing strings to the template builder raises `TypeError` at that call. At runtime an unknown current code raises `InvalidStateError`, and a forbidden move raises `InvalidTransitionError`.

For the rationale and independent runnable cases, see [Step 22](../tutorials/step-22-lifecycle.md).

Every lifecycle template declared on an entity passes eight structural rules at `coordinator.build()`. A violation of any is a `LifecycleValidationError` with the entity name, the field name, and a description of the violation.

1. Every state has a `.initial()`, `.intermediate()`, or `.final()` label.
2. There is at least one initial state.
3. There is at least one final state.
4. Final states have no outgoing transitions.
5. Every transition references an existing state.
6. Every non-final state has at least one outgoing transition.
7. From every initial state at least one final state is reachable.
8. Every non-initial state is the target of at least one transition.

At runtime `lifecycle.transition("shipped")` checks the move against the current state. Graph validation checks the declared rules; it does not execute an order's transition or validate a sequence of past events.

Maxitor draws lifecycles as FSM diagrams straight from the entity code. The analogs are XState in the JS world, statecharts in aviation and medical software.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
