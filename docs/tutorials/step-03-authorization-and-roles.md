<!-- translated-from: step-03-authorization-and-roles_draft.md @ 2026-07-18T19:03:37Z (filesystem mtime; draft is gitignored, no git history) · sha256:095153226a0a -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 03 — Authorization and roles

<table width="100%"><tr>
  <td align="left"><a href="step-02-state-as-x-ray.md">← Step 02 — State: the operation's x-ray</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-04-saga-and-compensations.md">Step 04 — Saga and compensations →</a></td>
</tr></table>

- [Access cannot be forgotten](#access-cannot-be-forgotten)
- [Roles as classes](#roles-as-classes)
- [Role hierarchy](#role-hierarchy)
- [Several allowed roles](#several-allowed-roles)
- [A condition on top of a role: grant](#a-condition-on-top-of-a-role-grant)
- [A shared condition: guard](#a-shared-condition-guard)
- [Checking the fact: access_decide](#checking-the-fact-access_decide)
- [Asking first: machine.check_access_decide](#asking-first-machinecheck_access_decide)
- [Where the user's roles come from](#where-the-users-roles-come-from)
- [Role modes](#role-modes)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

In most systems authorization is strings and habit. Somewhere near the top of a method sits `if user.role == "admin"`, elsewhere there is `"administrator"` with a typo, and in a third place the check was simply forgotten. Who can call what is collected nowhere: to find out, you grep the codebase and hope you caught every spot. And per-object authority ("a manager may cancel only their own order") drowns in the same business logic as the order itself.

AOA treats access as a **mandatory declaration of the operation**, not a string in its body. Who may call an `Action` is declared once, in the header, with the `@check_roles` decorator — and checked by the machine **before** the first aspect. Roles, moreover, are not strings but classes: with a name, a description, inheritance, and a place in the system graph. This chapter is about how operation-level authorization works; authentication (how a request yields a user with roles) is a separate topic of the [service layer](../index.md#iv-service).

[▶ Try in Colab](https://drive.google.com/file/d/1oB84MmIX7ritKbk5x8giwNV0-ymln_ig/view?usp=drive_link) · [Open in project](../../examples/step_03_authorization_and_roles/01_roles.py)

---

## Access cannot be forgotten

`@check_roles` is one of the three mandatory decorators of an operation (alongside `@meta` and `@summary_aspect`, see [Action and the pipeline](step-01-action-and-pipeline.md)). The machine will not build the operation graph without it: at initialization a `MissingCheckRolesError` is raised. Silence does not mean "open to everyone" — the absence of an access check counts as an error, not as permission.

If an operation truly is open to everyone, that is said out loud — through the `GuestRole` sentinel:

```python
@meta(description="View an order", domain=StoreDomain)
@check_roles(GuestRole)              # open to everyone — stated explicitly
class GetOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Return the order")
    async def get_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="viewed")
```

`GuestRole` is the intent "no authentication required", not a default value. The difference is fundamental: `@check_roles` cannot be forgotten, while the decision "let anyone call it" stays deliberate and visible in the header.

The neighboring sentinel is `AnyRole`: "any authenticated user is required, the specific role does not matter". It lets a call through if the user has at least one (live) role, and rejects an anonymous one:

```python
@check_roles(AnyRole)               # anyone who has at least one role
class GetProfileAction(BaseAction[...]): ...
```

`GuestRole` and `AnyRole` are "sealed" system roles (`SystemRole`): they can be neither subclassed nor assigned to a user. They exist only as an argument to `@check_roles`.

---

## Roles as classes

A business role in AOA is a class, a subclass of `ApplicationRole`, with mandatory `name` and `description` (like a domain). The class name ends with `Role` — otherwise `NamingSuffixError` right at declaration.

```python
class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Can manage orders"
```

Why a class and not a string? The string `"manager"` is backed by nothing: the typo `"manger"` shows up in production, the list of existing roles is collected nowhere, renaming is a text search. A class, by contrast, is typed (the IDE and mypy catch the error), carries a description, lands in the system graph and the "operation × role" matrix, and cannot be confused with another. Authorization stops being "magic strings" and becomes part of a grammar the system knows.

To bind a role to an operation is to name its class:

```python
@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)           # the manager role is required
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="cancelled")
```

---

## Role hierarchy

Privileges are inherited through ordinary subclassing, and therein lies the whole trick. Let's make the administrator a subclass of the manager:

```python
class AdminRole(ManagerRole):       # an admin is a manager with greater rights
    name = "admin"
    description = "Full control; includes manager privileges"
```

The runtime access check is `issubclass(user_role, required_role)`. So the requirement `@check_roles(ManagerRole)` is satisfied by both a manager and an administrator: `issubclass(AdminRole, ManagerRole)` is true. But `@check_roles(AdminRole)` will no longer let a manager through — `issubclass(ManagerRole, AdminRole)` is false.

It reads like this: **a subclass is a role with greater authority that also counts as its parent.** By modeling "admin → manager → reader" through inheritance and requiring the minimally necessary role in an operation, you automatically admit everyone above. There is no need to duplicate permission lists.

Let's assemble three operations with different policies and run them under three users. The full code is in the [example](../../examples/step_03_authorization_and_roles/01_roles.py); here is the gist:

```python
@check_roles(GuestRole)      class GetOrderAction(...):     ...   # everyone
@check_roles(ManagerRole)   class CancelOrderAction(...):  ...   # managers and admins
@check_roles(AdminRole)     class PurgeOrdersAction(...):  ...   # admins only
```

A user with roles is built through the call context:

```python
manager = Context(user=UserInfo(user_id="m1", roles=(ManagerRole,)))
admin   = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
```

**Run:**

```bash
uv run python examples/step_03_authorization_and_roles/01_roles.py
```

**Output:**

```text
User: anonymous
  GetOrder    [GuestRole]     -> allowed
  CancelOrder [ManagerRole]  -> denied
  PurgeOrders [AdminRole]    -> denied

User: manager
  GetOrder    [GuestRole]     -> allowed
  CancelOrder [ManagerRole]  -> allowed
  PurgeOrders [AdminRole]    -> denied

User: admin
  GetOrder    [GuestRole]     -> allowed
  CancelOrder [ManagerRole]  -> allowed
  PurgeOrders [AdminRole]    -> allowed
```

The matrix reads at a glance: an anonymous user passes only into the open operation; a manager — into the open one and the "manager" one; an admin, being a manager, passes everywhere. On denial the machine raises `AuthorizationError` — before a single aspect has run.

---

## Several allowed roles

Sometimes an operation must be callable by roles from different branches of the hierarchy — for example, a manager **or** an auditor. Then `@check_roles` accepts a list; the semantics is OR (one of those listed is enough):

```python
@check_roles([ManagerRole, AuditorRole])    # manager OR auditor (or their subclasses)
class ExportOrdersAction(BaseAction[...]): ...
```

An empty list is forbidden (`ValueError`), and `@check_roles` does not accept strings at all — only role classes and the two sentinels. This is deliberate: a list of role names is bad precisely because it is not checked.

---

## A condition on top of a role: grant

A role answers "who is calling"; it knows nothing about the specific call — the same `RegionalManagerRole` covers every region alike. Sometimes one role is not enough — a regional manager, say, should only act within their own region. That's what `grant(role, when=...)` is for on `@check_roles`: a role paired with an optional condition on the caller.

```python
@check_roles(
    grant(RegionalManagerRole, when=lambda user: user.user_id.startswith("eu-")),
    grant(GlobalAdminRole),
)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]): ...
```

Grants are tried in declaration order, `any()` semantics: as soon as a role matches and its `when=` (if given) returns `True`, the role-level check passes. A role matching but `when=` returning `False` is not fatal — the check keeps going to the next grant. `grant(GlobalAdminRole)` with no `when=` needs no condition — the role alone is enough.

A bare role in `@check_roles` (like `ManagerRole` above) is not a legacy form — it stays the permanent shorthand for "no condition needed"; `grant(role)` with no `when=` is equivalent to it. Bare roles and `grant(...)` instances can be freely mixed in the same call.

`when=` sees only the caller (`UserInfo` — `user_id` and `roles`), not the call's parameters: it is about **who** is asking, not **what** they're asking for.

**Run:**

```bash
uv run python examples/step_03_authorization_and_roles/02_grant.py
```

Full code is in [`02_grant.py`](../../examples/step_03_authorization_and_roles/02_grant.py).

---

## A shared condition: guard

`guard=` is a single condition on top of whichever grant already won, shared by every role on the operation (unlike `grant.when=`, which is per-role). It is checked once, only after a grant has already matched:

```python
@check_roles(
    StaffRole,
    guard=lambda user, params: not params.order_id.startswith("LOCKED-"),
)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]): ...
```

Unlike `grant.when=(user)`, `guard=(user, params)` also sees the call's parameters — so a condition like "is this particular order locked" belongs naturally in `guard=`, not in `when=`. A caller without `StaffRole` never even reaches `guard=`: the role check has to pass first.

**Run:**

```bash
uv run python examples/step_03_authorization_and_roles/03_guard.py
```

Full code is in [`03_guard.py`](../../examples/step_03_authorization_and_roles/03_guard.py).

---

## Checking the fact: access_decide

Role and `guard=` both decide before the machine has loaded the object itself. Sometimes that's not enough: "a manager may cancel an order" is about a role, but "a customer may cancel *their own* order" is a fact about a specific order, not about the customer's role in general. The third, object-level check is the `access_decide` method on the action itself:

```python
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    async def access_decide(self, params, context, box, connections) -> bool:
        return params.owner_user_id == context.user.user_id
```

By default (on `BaseAction`), `access_decide` returns `True` — level 3 adds no restriction beyond role/`guard=` until an action explicitly overrides the method. `access_decide` runs only after role and `guard=` have already passed; a denial here is the same `AuthorizationError` as at levels 1-2, just with `level=3`.

**Run:**

```bash
uv run python examples/step_03_authorization_and_roles/04_access_decide.py
```

Full code is in [`04_access_decide.py`](../../examples/step_03_authorization_and_roles/04_access_decide.py).

---

## Asking first: machine.check_access_decide

A frontend deciding whether to show a "Cancel" button, or grey it out, cannot find out by actually trying to cancel the order. `machine.check_access_decide` answers "would this be allowed?", checking the same role → `guard=` → `access_decide` cascade, but running neither the cache, nor the aspects, nor plugin events:

```python
verdict = await machine.check_access_decide(context, CancelOrderAction, params)
if verdict.kind == ResolveItemKind.SUCCESS:
    show_cancel_button()
```

A denial here is not an exception but `verdict.kind` being something other than `SUCCESS` (`ResolveItemKind.SECURITY` for a role/`guard=`/`access_decide` rejection), with `verdict.reason` (a human-readable message; always an empty string for `SUCCESS`). The same method, `check_access_decide`, accepts either one action or a list of `(action, params)` pairs, returning a list of verdicts in the same order:

```python
verdicts = await machine.check_access_decide(context, [
    (CancelOrderAction, params_1),
    (CancelOrderAction, params_2),
])
```

The list is not a side overload — it's the primary form: a single check is implemented as a one-item list. One failing item in the list (say, a bug in `access_decide` for a particular order) does not bring down the rest — only its own verdict fails. A list longer than `max_check_access_decide_batch_size` (a constructor parameter on `ActionProductMachine`, defaulting to 100) is rejected with `CheckAccessDecideBatchSizeExceededError` before a single item is checked.

**Run:**

```bash
uv run python examples/step_03_authorization_and_roles/05_machine_check.py
```

Full code is in [`05_machine_check.py`](../../examples/step_03_authorization_and_roles/05_machine_check.py).

---

## Where the user's roles come from

`@check_roles` declares a *requirement*; the *user's* roles live in `Context.user.roles` — a tuple of role classes. The context is assembled by the authentication coordinator before the operation runs: `NoAuthCoordinator` returns an anonymous user (`roles=()`), while a production coordinator extracts a token from the request, verifies it, and puts the corresponding roles into the context. How exactly this context is built from an HTTP/MCP request is the topic of the [Authentication](../index.md#iv-service) chapter of the service layer; here it is enough for the operation to know that the roles are already in the context, and the checking mechanics are the same regardless of transport.

The aspect itself does not see the roles directly — like the whole context, they are available only through the declared slice `@context_requires` (see [Context](../index.md#iii-business-logic)), if the operation needs to read `user_id` or the roles for audit for some reason. This does not perform authorization — that is done by the machine via `@check_roles` at the entrance.

---

## Role modes

A role also has a lifecycle — for the case when rights change but the system must not break. The mode is set by the `@role_mode(...)` decorator and comes in four kinds:

- `ALIVE` — an ordinary live role (the default for subclasses of `ApplicationRole`);
- `DEPRECATED` — the role still works, but `@check_roles` with it emits a warning: time to move off;
- `SILENCED` — the role is temporarily "muted": for a user it is ignored on check, as if it were absent;
- `UNUSED` — the role is withdrawn from use: an attempt to require it in `@check_roles` is a `ValueError` at import.

This turns changing the role model from a risky operation into a managed one: a role can be marked deprecated, give the team time to migrate, then be silenced and finally withdrawn — and each stage is checked by the machine, not kept in someone's head.

---

## Invariants

- **Access is mandatory.** No `@check_roles` — no operation: `MissingCheckRolesError` at initialization. Openness is declared explicitly through `GuestRole`.
- **Classes only.** `@check_roles` accepts `GuestRole`, `AnyRole`, a role class, a non-empty list of classes, or `grant(...)` instances mixed with bare roles. Strings are rejected (`TypeError`), an empty list is a `ValueError`.
- **Inheritance = authority.** The check is `issubclass(user_role, required_role)`; a subclass satisfies the parent's requirement.
- **Sentinels are sealed.** `GuestRole`/`AnyRole` cannot be subclassed and cannot be assigned to a user.
- **Check before logic.** Roles, `guard=`, and `access_decide` are checked before the first aspect; denial at any of the three levels is an `AuthorizationError`, the aspects do not run.
- **Role names.** A role class ends with `Role`, otherwise `NamingSuffixError`; `name`/`description` are mandatory and non-empty.
- **`grant.when=`/`guard=` are synchronous and `bool`-only.** An `async def` in either raises `AccessConditionAsyncError` at class definition, not at runtime — an un-awaited coroutine is always truthy, and the check would silently wave everything through.
- **`access_decide` defaults to `True`.** Level 3 restricts nothing beyond role/`guard=` until an action explicitly overrides the method.
- **`machine.check_access_decide` is capped by list size.** `max_check_access_decide_batch_size` (100 by default) — a longer list is rejected with `CheckAccessDecideBatchSizeExceededError` before a single `access_decide` call.
- **Denial at any of the three cascade levels flies past `@on_error`/the saga.** Role/`guard=`/`access_decide` run before `_execute_pipeline_aspects` — no `@regular_aspect`/`@summary_aspect` has run yet, so there's nothing to roll back; `@on_error` is a recovery mechanism for business-logic failures inside the pipeline, not a place for authorization decisions.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why access is made a mandatory declaration is in the [Philosophy](../explanation/philosophy.md).

---

## Summary

Authorization in AOA is a declaration, not code in the operation's body. `@check_roles` is mandatory and checked before the first aspect; roles are typed classes with inheritance, where a subclass carries the parent's rights; `GuestRole`/`AnyRole` cover "open to everyone" and "any authenticated user"; a list gives OR-semantics; role modes make changing the model manageable. The cascade then extends further: `grant(role, when=...)` is a condition on a specific role, `guard=` is a shared condition on top of any role, `access_decide` is an object-level fact check, and `machine.check_access_decide` answers "would this be allowed?" without running the operation. Who can call what is assembled from the code into an access matrix — without a single "magic string".

Next — **[Saga and compensations](../index.md#iii-business-logic)**: what happens when a multi-step operation fails halfway, and how to roll back what was already done.

---

## Review questions

1. Why is the absence of `@check_roles` an initialization error and not "the operation is open to everyone"? Which property of the system does this protect?
2. How does `GuestRole` differ from `AnyRole`? When is each appropriate?
3. An operation declares `@check_roles(ManagerRole)`. Will a user with `AdminRole` pass if `AdminRole(ManagerRole)`? And the other way around? Why?
4. Why are roles classes and not strings? What does this give review, the graph, and refactoring?
5. How does a list in `@check_roles([A, B])` differ from a role hierarchy? When do you need a list, and when inheritance?
6. Where do the user's roles live and who puts them there? Does the aspect see them directly?
7. Why does a role need a lifecycle mode? What happens with `@check_roles` for a `UNUSED` role and for a `DEPRECATED` one?
8. How does `grant(role, when=...)` differ from `guard=`? Which of the two sees the call's parameters, and which sees only the caller?
9. A role matched, but its `grant.when=` returned `False`. Does that end the check or not? Why?
10. `access_decide` returned `False`. What `level` will the `AuthorizationError` carry? What if the role hadn't matched at all?
11. How does `machine.check_access_decide` differ from `machine.run` on denial — what does the calling code get in each case?

> **Exercise.** Add an `AuditorRole(ApplicationRole)` role and an `ExportOrdersAction` with `@check_roles([ManagerRole, AuditorRole])` to the example. Run it under a manager, an auditor, and an anonymous user and check the matrix. Then make `AuditorRole` a subclass of `ManagerRole` and explain how access to the "manager" operations changes.
>
> **Exercise.** Take the `CancelOrderAction` from [`04_access_decide.py`](../../examples/step_03_authorization_and_roles/04_access_decide.py) and add a `guard=` that forbids cancelling orders above a certain amount. Use `machine.check_access_decide` to confirm the verdict correctly distinguishes a `guard=` denial (level 2) from an `access_decide` denial (level 3) for the same user.

---

<table width="100%"><tr>
  <td align="left"><a href="step-02-state-as-x-ray.md">← Step 02 — State: the operation's x-ray</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-04-saga-and-compensations.md">Step 04 — Saga and compensations →</a></td>
</tr></table>
