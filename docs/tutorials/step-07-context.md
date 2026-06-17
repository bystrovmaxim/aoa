<!-- translated-from: step-07-context_draft.md @ 2026-06-17T17:53:37Z · sha256:1be52733cb97 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 07 — Context

<table width="100%"><tr>
  <td align="left"><a href="step-06-dependencies.md">← Step 06 — Dependencies</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-08-cache.md">Step 08 — Cache →</a></td>
</tr></table>

- [The call environment](#the-call-environment)
- [An aspect does not see the context by default](#an-aspect-does-not-see-the-context-by-default)
- [Declare and read a slice](#declare-and-read-a-slice)
- [Invisibility of the rest](#invisibility-of-the-rest)
- [Transport independence](#transport-independence)
- [Extending the context](#extending-the-context)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

Every call has an environment: who initiated it, with which roles, under what `trace_id`, where it came from. Some steps will not make a decision without this. The trouble is that the environment is easy to turn into a back door: let an operation read it freely, and branches by IP address or `User-Agent` appear in the logic, behavior starts to depend on which transport the request arrived through. Business logic quietly grows onto the delivery.

AOA does not make the context an ambient environment you can reach into from anywhere. The environment is packed into `Context`, but an aspect **does not see it by default**. To read a field, an aspect declares it with the `@context_requires` decorator — as strictly as it declares dependencies. In return the machine hands it a `ContextView` — a slice that opens exactly the declared fields and nothing beyond. This is the same principle of explicitness as with [dependencies](step-06-dependencies.md): if you use it, declare it.

[▶ Try in Colab](https://drive.google.com/file/d/1SNlqpMH4ptVTQNdquObgokAkt90H3gUA/view?usp=drive_link) · [Open in project](../../examples/step_07_context/01_context.py)

---

## The call environment

`Context` is assembled once per call — by the authentication coordinator (about this — in the [Service](../index.md#iii-service) part) — and consists of three parts:

- **UserInfo** — who is calling: `user_id`, roles;
- **RequestInfo** — request data: `trace_id`, path, method, `client_ip`, `user_agent`, …;
- **RuntimeInfo** — the environment: `hostname`, `service_name`, service version, …

This is rich information — and that is exactly why access to it is rationed.

## An aspect does not see the context by default

Without `@context_requires` an aspect does not get the context at all — it has neither a parameter for it nor a loophole (`box` does not hold the context). This is a deliberate least access: only what is declared is visible. The declaration changes the aspect's signature — a last parameter `ctx` is added:

```python
@regular_aspect("Audit who placed the order and from which trace")
@context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
async def audit_aspect(self, params, state, box, connections, ctx):
    user_id = ctx.get(Ctx.User.user_id)
    trace_id = ctx.get(Ctx.Request.trace_id)
    ...
```

The `@context_requires` decorator is placed **closer to the body** of the method (under `@regular_aspect`), so that by the time the aspect checks the signature the number of parameters is already known. Without `@context_requires` an aspect has five parameters (`self, params, state, box, connections`), with it — six (`ctx` is added); for `@on_error` — seven (after `error`).

## Declare and read a slice

`ctx.get(...)` returns a value by a dot-path key. Standard fields are conveniently taken through the `Ctx` constants (`Ctx.User.user_id` == `"user.user_id"`) — that is autocomplete and protection from typos; for your own fields a raw string works. Through `ctx` you can read only what is declared in this aspect's `@context_requires` — `ContextView` will not hand out anything extra.

## Invisibility of the rest

The key point: the restriction works **even if the field is in the context**. If an aspect declared `user_id` and `trace_id`, `client_ip` is unavailable to it, even though it is present in `Context`:

```python
try:
    ctx.get(Ctx.Request.client_ip)        # not declared in @context_requires
except ContextAccessError:
    await box.info(Channel.business, "  client_ip not declared -> access refused")
```

**Run:**

```bash
uv run python examples/step_07_context/01_context.py
```

**Output:**

```text
  audit: order=ord-001 user=u-42 trace=trace-abc
    client_ip not declared -> access refused
```

The aspect read the declared fields (`user_id`, `trace_id`), and an attempt to take the undeclared `client_ip` — though it was in the context — was rejected. So from the aspect's header you can see *everything* it takes from the environment, and you cannot quietly start depending on an extra field.

## Transport independence

From this follows the main practical consequence. Since an aspect reads only the declared fields, it does not matter where the call came from: HTTP, MCP, CLI, or a test supply different environments, but the operation reads them the same way. A branch like "if this is HTTP with such-and-such `User-Agent`…" has nowhere to come from if the field is not declared — which means business logic does not grow onto the transport. The same `audit_aspect` works unchanged in any of these worlds.

## Extending the context

`UserInfo`, `RequestInfo`, and `RuntimeInfo` can be extended by inheritance — adding your own environment fields. Standard fields are covered by the `Ctx` constants; your own are accessed by a raw dot-path:

```python
class BillingUserInfo(UserInfo):
    billing_plan: str = "free"

@context_requires(Ctx.User.user_id, "user.billing_plan")
async def billing_aspect(self, params, state, box, connections, ctx):
    plan = ctx.get("user.billing_plan")
    ...
```

How to wire such an extended environment into the service is the topic of the [«Extending Context»](../index.md#how-to-write-your-own-extension) extension point.

## Invariants

- **Nothing by default.** Without `@context_requires` an aspect has no access to the context; `box` does not hold it.
- **Only the declared.** `ctx.get(key)` returns a value only if `key` is declared in `@context_requires`; otherwise — `ContextAccessError`, even when the field is present.
- **Signature.** `@context_requires` adds a `ctx` parameter: 6 for an aspect, 7 for `@on_error`; the count is checked at declaration.
- **At least one key.** An empty `@context_requires()` is a `ValueError`; a key is a non-empty string.
- **The whole context — to plugins.** The full `Context` is visible to observer [plugins](../index.md#ii-business-logic) and to role checking, but not to business code.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why the context is made an explicit slice is in the [Philosophy](../explanation/philosophy.md).

## Summary

The context in AOA is not an ambient environment but a declared slice. An aspect does not see it by default; `@context_requires` opens exactly the needed fields, the machine hands them over through `ContextView`, and the undeclared is unavailable even if present. Hence least access and transport independence: the operation reads the environment the same way no matter where the call came from, and cannot secretly grow onto delivery details.

Next — **[Cache](../index.md#ii-business-logic)**: a layer over the pipeline that can return a result without running the steps.

---

## Review questions

1. Why is an aspect's free access to the environment dangerous? What does it lead to over the long run?
2. What does an aspect get without `@context_requires`? How exactly does it get the declared fields?
3. An aspect declared `user_id` and `trace_id` but tries to read `client_ip`, which is in the context. What happens and why does it matter?
4. How does `@context_requires` provide the operation's transport independence?
5. Who sees the full `Context`, and who — only a slice? Why is it split this way?
6. How do you add your own field to the environment, and how does an aspect read it?

> **Exercise.** Add reading of `Ctx.Runtime.hostname` to `audit_aspect` (declare it in `@context_requires`) and log it. Then remove `Ctx.Request.trace_id` from the declaration but leave `ctx.get(Ctx.Request.trace_id)` in the body — and explain on which line and why execution will fail.

---

<table width="100%"><tr>
  <td align="left"><a href="step-06-dependencies.md">← Step 06 — Dependencies</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-08-cache.md">Step 08 — Cache →</a></td>
</tr></table>
