<!-- translated-from: step-27-ui-permissions-resolve_draft.md @ 2026-07-17T15:32:57Z (filesystem mtime; draft is gitignored, no git history) · sha256:dbe720b68498 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 27 — UI permissions: the resolver

<table width="100%"><tr>
  <td align="left"><a href="step-26-maxitor.md">← Step 26 — Maxitor: a system you can see</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="../index.md">Contents →</a></td>
</tr></table>

- [The button that lies](#the-button-that-lies)
- [The idea: ask, don't copy the rule](#the-idea-ask-dont-copy-the-rule)
- [POST /permissions/resolve](#post-permissionsresolve)
- [A list is not a special case](#a-list-is-not-a-special-case)
- [A batch survives duplicates and one bad error](#a-batch-survives-duplicates-and-one-bad-error)
- [A guest is a valid answer too](#a-guest-is-a-valid-answer-too)
- [Why this isn't an ordinary operation](#why-this-isnt-an-ordinary-operation)
- [What the resolver doesn't say yet](#what-the-resolver-doesnt-say-yet)
- [Invariants](#invariants)
- [Check yourself](#check-yourself)

---

The [Authorization and roles](step-03-authorization-and-roles.md) chapter taught `@check_roles`/`access_decide` to decide "yes" or "no" on the server. But the frontend needs that same answer too — to decide whether the "Cancel order" button should be active or greyed out — and before this chapter it had no way to ask, other than trying the action and seeing whether the server refuses.

[▶ Try in Colab](https://colab.research.google.com/) · [Open in the project](../../examples/step_27_ui_permissions_resolve/01_role_gate_allowed.py)

---

## The button that lies

Picture an order table with a "Cancel" button on every row. The button can't be shown to everyone: only a manager can cancel an order, and not just any manager — one who actually has the right. Without a way to ask the server ahead of time, the frontend has exactly one path left: duplicate the same rule right inside the component:

```tsx
// BEFORE — the rule is manually duplicated
function OrderRow({ order, user }: { order: Order; user: CurrentUser }) {
  const canCancel = user.roles.includes("manager");
  return canCancel
    ? <button onClick={() => cancelOrder(order.id)}>Cancel</button>
    : <button disabled>Cancel</button>;
}
```

The rule "who can cancel an order" now lives in two places: on the server (the source of truth) and in the component (a copy). The server changes the rule — the component never finds out, until someone manually finds and fixes the copy.

---

## The idea: ask, don't copy the rule

Instead of keeping a copy of the rule, let the frontend ask the server directly — through a protocol, not by re-implementing the text of the rule. The server answers based on that one single rule, already declared via `@check_roles`/`access_decide`. There is no copy — so there can be no drift.

```tsx
// AFTER — the component doesn't know what the rule is made of
async function checkCanCancel(orderId: number): Promise<boolean> {
  const res = await fetch("/permissions/resolve", {
    method: "POST",
    body: JSON.stringify({
      protocol: 1,
      items: [{ operation: "CancelOrderAction", params: { order_id: orderId } }],
    }),
  });
  const { verdicts } = await res.json();
  return verdicts[0].allowed;
}
```

The component doesn't contain a single word about roles. If the rule on the server changes, the component needs zero edits.

---

## POST /permissions/resolve

The endpoint itself is a thin wrapper around the already-existing `machine.check_access_decide` (see [Authorization and roles](step-03-authorization-and-roles.md#asking-first-machinecheck_access_decide)): the resolver adds no new authorization logic — it turns a list of `(operation, params)` into a list of answers in the same shape the machine already knows how to return.

```python
verdict = await machine.check_access_decide(manager, CancelOrderAction, OrderParams(order_id=7))
```

`to_wire()` (package `aoa-fastapi-adapter`, `aoa.fastapi.permissions`) projects the internal `AccessVerdict` onto the wire `Verdict` shape. Notice a non-obvious detail: `scope` on an allowed verdict is `null`, not `"role"`, even though a role check is exactly what ran. `AccessVerdict.level` is `None` by contract precisely when `allowed=True` — there simply is no rejecting level if nothing rejected the call, and `to_wire()` builds `scope` from `level`. Full example — [`01_role_gate_allowed.py`](../../examples/step_27_ui_permissions_resolve/01_role_gate_allowed.py); on a denial (`level=1`, the role didn't match), `scope` is already `"role"` — see [`02_role_gate_denied.py`](../../examples/step_27_ui_permissions_resolve/02_role_gate_denied.py).

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/01_role_gate_allowed.py
uv run python examples/step_27_ui_permissions_resolve/02_role_gate_denied.py
```

---

## A list is not a special case

`machine.check_access_decide` is one method with two shapes: a single action, or a list of `(action, params)` pairs. The list is not a side overload — it's the primary shape: a single check is implemented as a list of one item. That's why `POST /permissions/resolve` is list-shaped (`items`/`verdicts`) from day one, even while the frontend still asks one question at a time — adding a second question to the same request later needs no change to the protocol's shape.

```python
single = await machine.check_access_decide(manager, CancelOrderAction, params)
batch = await machine.check_access_decide(manager, [(CancelOrderAction, params)])
# to_wire(single) == to_wire(batch[0])
```

A list longer than `max_check_access_decide_batch_size` (a constructor parameter of `ActionProductMachine`, default 100) is rejected before a single item is checked — `CheckAccessDecideBatchSizeExceededError`, mapped to HTTP `413 Payload Too Large` at the HTTP layer.

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/03_batch_of_one_equals_single.py
```

---

## A batch survives duplicates and one bad error

A list of questions in one request is not a list of guaranteed *different* questions. An order table with "Cancel" and "Refund" buttons on every row is two independent frontend components, neither aware of the other; if both ask about the same order, the question `("CancelOrderAction", {"order_id": 7})` can land in the batch twice. A naive implementation (a loop over `items`, a separate `access_decide` call for each) would do extra work in that case — the second call computes exactly the same thing the first one did, just once more.

`resolve_verdicts()` (package `aoa-fastapi-adapter`, `aoa.fastapi.permissions`) groups items by the key `(operation, canonical_key(params))` and calls `access_decide` exactly once per distinct key — at the position where that key was first seen, in request order. A batch of five questions where the first and the fifth are literally the same `(operation, params)`, and the three in between are different, produces **five** verdicts in the response (the list never gets shorter — that's the same positional contract, `items[i]` ↔ `verdicts[i]`, from the start of this chapter), but only **four** real `access_decide` calls: the fifth position gets an exact copy of the first position's verdict, computing nothing again.

```python
outcome = await resolve_verdicts(context, items, action_index, machine)
outcome.verdicts          # always the same length as len(items) — even under full deduplication
outcome.real_call_count   # how many REAL access_decide calls happened — at most len(items)
```

`real_call_count` is not a wire-protocol field: the client has no business (and no need) knowing which positions were freshly computed and which were copied — from its point of view, every answer is equally honest and independent. The field exists for tests and for this chapter's examples — the one way to confirm deduplication actually happened, not so the frontend can rely on it.

The second, independent problem with the same naive approach is fragility to errors: one batch item with an unrecognized action name (a typo, a stale frontend build) used to fail the whole request. Now that item gets a verdict with `reason_code: "UNKNOWN_ACTION"` at its own position — the HTTP status is still `200 OK`, and the rest of the batch answers as usual.

```python
{"allowed": false, "scope": null, "level": null, "reason_code": "UNKNOWN_ACTION"}
```

Finally, `max_check_access_decide_batch_size` (the batch-length cap, `413` on overflow — see the previous section) is now checked **after** deduplication, against the number of distinct keys, not the raw item count: a batch of a thousand copies of the same question is still one distinct key, and a cap of one lets it through, while a cap of one rejects just two genuinely different questions.

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/06_duplicate_within_batch.py
uv run python examples/step_27_ui_permissions_resolve/07_unknown_action_in_batch.py
uv run python examples/step_27_ui_permissions_resolve/08_batch_size_exceeded_after_dedup.py
uv run python examples/step_27_ui_permissions_resolve/09_mixed_dedup_isolation_and_order.py
```

---

## A guest is a valid answer too

The resolver always calls `auth_coordinator.process(request)` — but that isn't the same thing as "only works for logged-in users." If the coordinator (e.g. `NoAuthCoordinator`) answers missing credentials with a real anonymous `Context` rather than `None`, the resolver proceeds into `machine.check_access_decide` as usual — and an action with `@check_roles(GuestRole)` gets an honest `allowed: true`, exactly like any other role. `403` only happens when `process()` genuinely returned `None`.

```python
guest = Context()  # anonymous, but a real Context — not None
verdict = await machine.check_access_decide(guest, BrowseCatalogAction, PublicParams())
```

`GuestRole` only clears the question itself — it doesn't mean "always allowed". `access_decide` (level 3) can still base its answer on any fact, not just object ownership — for example, on whether a real-world event has already happened.

```python
async def access_decide(self, params, context, box, connections) -> bool:
    order = orders_db[params.order_id]
    if order.tracking_token != params.tracking_token:
        return False
    return order.status in ("shipped", "in_transit", "delivered")  # event hasn't happened yet — too early
```

**Run:**

```bash
uv run python examples/step_27_ui_permissions_resolve/04_guest_role_vs_rejected_anonymous.py
uv run python examples/step_27_ui_permissions_resolve/05_guest_gated_by_event.py
```

---

## Why this isn't an ordinary operation

The resolver needs to ask the machine about *other* actions — dozens per call, without running a single one of them. An ordinary AOA action runs inside a `ToolsBox`, which, by the context-privacy invariant, holds no reference to either `machine` or a full `Context` at all (see the `tools_box.py` docstring). So the resolver can't be an ordinary `BaseAction` registered via `.post(action_class)` — it needs direct access to `self._machine`/`self._auth_coordinator`, which only the adapter itself has.

The solution is a bespoke route registered right inside `FastApiAdapter.build()`, next to the already-existing `_register_health_check` (the `GET /health` endpoint) — except, unlike that one, it never skips the `auth_coordinator.process()` call.

---

## What the resolver doesn't say yet

This chapter is the base: role level only (1-2), a list from day one, guest access, deduplication, and per-item error isolation. Deliberately out of scope:

- **Honest reporting of the object-level check.** `scope` in this chapter is never `"object"`, even when `access_decide` genuinely checked a specific object — `entities` is always an empty list. Revealing that detail without rate-limiting protection would hand an attacker a way to guess other people's object IDs from the shape of a denial. Reporting and protection arrive together, later.
- **The client package.** This chapter's examples call `machine.check_access_decide`/the resolver directly; a convenient typed client (`api.CancelOrderAction.can(...)`) doesn't exist yet.

---

## Invariants

- **The resolver doesn't change the machine.** `to_wire()`/route registration is a thin wrapper in `aoa-fastapi-adapter`; the access rule is still declared only via `@check_roles`/`access_decide` on the action itself.
- **A list is the primary shape.** A single question is a batch of one, not a separate code path; `POST /permissions/resolve` accepts and returns lists (`items`/`verdicts`) from day one.
- **`auth_coordinator.process()` is always called.** `403` only if it returned `None`; a resolved anonymous `Context` (`NoAuthCoordinator`) flows into the machine as usual.
- **`scope`/`entities` are conservative in this chapter.** `scope` is `"role"` or `null` (never `"object"`); `entities` is always `[]`, even when `access_decide` genuinely ran.
- **The batch is capped — by distinct keys.** `max_check_access_decide_batch_size` (default 100) rejects an overly long list outright, `413`, but the count is taken after deduplication: a batch of a thousand copies of one question is one distinct key, not a thousand.
- **A duplicate is about work, not about the answer.** Items with the same `(operation, params)` produce `verdicts` of the same length and order; only the number of real `access_decide` calls is saved (counted only for the first occurrence of a key), never the length of the response.
- **One bad item never sinks the batch.** An unrecognized action name — `reason_code: "UNKNOWN_ACTION"` at its own position, `200 OK` for the whole request; the rest of the batch answers as usual.
- **The resolver and the catalog are bespoke routes, not actions.** Registered directly in `FastApiAdapter.build()`, because an ordinary action can't reach either `machine` or a full `Context`.

---

## Summary

`POST /permissions/resolve` is a thin, but principled, layer over `machine.check_access_decide`: the frontend gets an honest "can I?" from the one place the rule is declared, instead of keeping a copy of the rule in the component. A list is the protocol's primary shape from day one; a guest isn't a special case for the resolver, but an ordinary role checked by the same cascade; `scope`/`entities` are deliberately modest in this chapter — details arrive together with rate-limiting protection. The batch, meanwhile, is resilient to its own duplicates (identical questions cost one real call but never shorten the response) and to one bad error (an unrecognized action only quenches its own position, not the whole request).

---

## Check yourself

1. Why is `scope` `null`, not `"role"`, for an allowed (`allowed: true`) verdict? What does the `AccessVerdict` contract say about it?
2. What's the difference between "`auth_coordinator.process()` returned `None`" and "returned an anonymous `Context`"? What does the resolver do in each case?
3. Why does `POST /permissions/resolve` accept a list from day one, even though the frontend currently sends one item at a time?
4. Why can't the resolver be an ordinary `BaseAction` registered via `.post(action_class)`? What access, specifically, does an ordinary action lack?
5. An action's `access_decide` returned `False` for a guest. Does that mean the guest doesn't own the object? Give another possible reason for the denial.
6. Why is `entities` always an empty list in this chapter, even when `access_decide` genuinely checked a specific object?
7. A batch of five questions where the first and the fifth are the same `(operation, params)`. How many items will `verdicts` contain? How many times will `access_decide` actually run?
8. Why isn't `real_call_count` published on the wire `Verdict`, even though it exists on `ResolveOutcome`?
9. Why is the `max_check_access_decide_batch_size` cap in this chapter counted by the number of distinct keys, rather than the number of items in `items`? What would go wrong counting the raw item count instead?

> **Exercise.** Take `TrackOrderAction` from [`05_guest_gated_by_event.py`](../../examples/step_27_ui_permissions_resolve/05_guest_gated_by_event.py) and add a second reason for denial to `access_decide` — for example, that the tracking code is only valid for 30 days after shipping. Run `machine.check_access_decide` before shipping, after shipping, and after the 30 days have passed, and confirm `allowed` reflects exactly that reason in each case.

---

<table width="100%"><tr>
  <td align="left"><a href="step-26-maxitor.md">← Step 26 — Maxitor: a system you can see</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="../index.md">Contents →</a></td>
</tr></table>
