<!-- translated-from: step-25-context_draft.md @ 2026-06-17T17:53:37Z · sha256:f95451a104f8 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 25 — Context in tests

<table width="100%"><tr>
  <td align="left"><a href="step-24-substitution.md">← Step 24 — Substituting the environment</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-26-maxitor.md">Step 26 — Maxitor →</a></td>
</tr></table>

- [Assembling the context](#assembling-the-context)
- [Roles and @check_roles](#roles-and-check_roles)
- [Only the declared is visible](#only-the-declared-is-visible)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

Every call has an environment: who made it, where the request came from, in what runtime the operation works. It reaches the operation through [`Context`](step-12-authentication.md), and the operation reads from it not everything but only the fields it declared with [`@context_requires`](step-07-context.md). In a test you assemble such a `Context` with `TestBench` — no need for a global state or to warm an object up to the right shape: just set the values.

- `with_user(user_id=, roles=(...))` → `UserInfo` (roles are checked by `@check_roles`);
- `with_request(trace_id=, request_path=, …)` → `RequestInfo`;
- `with_runtime(service_name=, hostname=, …)` → `RuntimeInfo`.

[▶ Try in Colab](https://drive.google.com/file/d/1R3It-sKLhcECkYcgH0bm61UGigxyBxfG/view?usp=drive_link) · [Open in project](../../examples/step_25_context/01_context.py)

---

## Assembling the context

Each `with_*` has reasonable defaults, and additional fields are passed via `**kwargs`. An aspect that declared a context slice sees exactly the assembled values:

```python
bench = (
    TestBench()
    .with_user(user_id="u-test", roles=(AdminRole,))
    .with_request(trace_id="t-1")
    .with_runtime(service_name="orders-svc")
)
r = await bench.run(WhoamiAction(), EmptyParams(), rollup=False)
# user_id=u-test  trace_id=t-1  service=orders-svc
```

`WhoamiAction` declared `@context_requires(Ctx.User.user_id, Ctx.Request.trace_id, Ctx.Runtime.service_name)` and read them from `ctx` — the very "virtual reality" the test assembled.

## Roles and @check_roles

The roles you put on the user via `with_user(roles=...)` are **exactly** what `@check_roles` will check. Remove the needed role — and the access check rejects the call, as in production:

```python
await TestBench().run(WhoamiAction(), EmptyParams(), rollup=False)
# AuthorizationError: Access denied. Required role: 'admin', user roles: ['tester']
```

`TestBench` defaults to an anonymous test user with the stub role `tester`; since the operation requires `admin` and it was not given, it is refused. Authorization cannot be bypassed in a test: it is part of the same machine.

## Only the declared is visible

Assembling the context does not open an aspect access to everything. The operation reads `Context` only through the declared `@context_requires` slice (the parameter `ctx` is a `ContextView`), and a field the aspect **did not declare** is refused — even if it is in the context:

```python
# client_ip is set on the request, but the aspect declared only user_id
leak_bench = TestBench().with_request(client_ip="10.0.0.7")
r = await leak_bench.run(LeakAction(), EmptyParams(), rollup=False)
# client_ip refused: True
```

This is the same discipline as in the [context chapter](step-07-context.md): a test cannot quietly slip an operation environment data it did not ask for. What is declared is what is available, no more.

**Run:**

```bash
uv run python examples/step_25_context/01_context.py
```

**Output:**

```text
1) with_user/request/runtime -> user_id=u-test trace_id=t-1 service=orders-svc
2) no admin role             -> AuthorizationError: Access denied. Required role: 'admin', user roles: ['tester']
3) undeclared field          -> client_ip refused: True  (it was set, but not declared)
```

## Invariants

- **The context is assembled via `TestBench`.** `with_user`/`with_request`/`with_runtime` give `UserInfo`/`RequestInfo`/`RuntimeInfo` with defaults and `**kwargs`.
- **Roles are the input to `@check_roles`.** What you put on the user is what authorization checks; no required role → `AuthorizationError`.
- **Only the declared is visible.** An aspect reads `Context` through the `@context_requires` slice; an undeclared field → `ContextAccessError`, even if it is set.
- **No global state.** It is enough to assemble the input and the environment; there is no object to set up in advance.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md).

## Summary

A `Context` in a test is assembled with the same `TestBench`: `with_user` sets the user and roles (which `@check_roles` then checks), `with_request` and `with_runtime` set the request and runtime fields. The operation sees exactly the declared `@context_requires` slice of this, and an undeclared field is refused — authorization and the context boundary cannot be bypassed in a test, because it is the same machine.

With this the **Testing** part is assembled: the run depth ([TestBench](step-23-testbench.md)), substituting the environment ([mocks, connections, Rollup](step-24-substitution.md)), and assembling the context. Next — the **[Maxitor](step-26-maxitor.md)** part: how to see the whole system — operations, dependencies, entities — without a single line of manual documentation.

---

## Review questions

1. How do `with_user`, `with_request`, and `with_runtime` differ, and which parts of `Context` does each assemble?
2. What exactly does `@check_roles` check — and how is it connected to `with_user(roles=...)`?
3. What role does the test user have by default, and why does calling an `admin` operation without it fail?
4. Why might a field set via `with_request` turn out unavailable to an aspect? What is needed for it?
5. Why can authorization and the context boundary not be bypassed in a test?

> **Exercise.** In [01_context.py](../../examples/step_25_context/01_context.py) add `Ctx.Request.client_ip` to `LeakAction`'s `@context_requires` and confirm that the read now passes and `client_ip_refused` became `False`. Then give the test user the `AdminRole` via `with_user` for a second `WhoamiAction` run and watch the `AuthorizationError` disappear.

---

<table width="100%"><tr>
  <td align="left"><a href="step-24-substitution.md">← Step 24 — Substituting the environment</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-26-maxitor.md">Step 26 — Maxitor →</a></td>
</tr></table>
