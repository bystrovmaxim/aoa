<!-- translated-from: step-05-error-handling_draft.md @ 2026-07-10T14:55:05Z (filesystem mtime; draft is gitignored, no git history) · sha256:705466221b6f -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 05 — Explicit error handling

<table width="100%"><tr>
  <td align="left"><a href="step-04-saga-and-compensations.md">← Step 04 — Saga and compensations</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-06-dependencies.md">Step 06 — Dependencies →</a></td>
</tr></table>

- [The problem: the all-powerful try/except](#the-problem-the-all-powerful-tryexcept)
- [@on_error: a handler by type](#on_error-a-handler-by-type)
- [Returning a Result closes the error](#returning-a-result-closes-the-error)
- [Several handlers: order and shadowing](#several-handlers-order-and-shadowing)
- [When no one caught it](#when-no-one-caught-it)
- [Three layers and their order](#three-layers-and-their-order)
- [Invariants](#invariants)
- [Review questions](#review-questions)

---

`try/except` is universal — and therein lies the trouble. One block can do everything at once: roll back steps, close connections, replace an exception with a meaningful response, log. Behind a heap of such blocks the business logic is no longer visible — it is unclear where the operation does its job and where it cleans up the aftermath and argues with the infrastructure.

AOA separates this into layers. Rollback is `@compensate` ([previous chapter](step-04-saga-and-compensations.md)). Everything else — releasing resources, deciding whether to re-raise the exception or return a meaningful result — is taken on by the global `@on_error`, firing at the end. Business logic, rollback, and error handling become three independent layers, and `try/except` nearly disappears from the main code.

[▶ Try in Colab](https://drive.google.com/file/d/1K8iE9PCF1p_jHuksS9Dkb3K55vaVtJhj/view?usp=drive_link) · [Open in project](../../examples/step_05_error_handling/01_on_error.py)

---

## The problem: the all-powerful try/except

When error handling lives right inside an aspect, it drags everything along: the rollback, the logging, and the shaping of the response. Each such block is a blend of three different concerns in one place. `@on_error` lifts handling out of the operation body into a separate declaration: "errors of this type are handled like this." The aspect again does only its own job and simply raises an exception if something is wrong.

## @on_error: a handler by type

`@on_error(exception_type, description=...)` declares a handler method for a particular error type. The machine catches exceptions thrown by regular aspects **and** the summary, finds the first matching handler by `isinstance(error, type)`, and calls it. The method name ends with `_on_error`, the method is async; the signature is like an aspect's, plus the error itself:

```python
@summary_aspect("Validate credentials")
async def login_summary(self, params, state, box, connections):
    if params.username == "bad":
        raise ValueError("invalid credentials")
    return LoginResult(username=params.username, status="ok")

@on_error(ValueError, description="Invalid credentials")
async def validation_error_on_error(self, params, state, box, connections, error):
    await box.info(Channel.business, "on_error: {%var.msg}", msg=str(error))
    return LoginResult(username=params.username, status="login_failed")
```

The handler catches not only errors from the aspect's own code but also those that arrived from resources: if a payment gateway or a database threw an exception, it rises as an aspect error and is caught by `@on_error` by type — on a par with any other. If the handler needs context fields, it declares its own `@context_requires` (independently of the failed aspect) and receives a seventh parameter `ctx`.

## Returning a Result closes the error

The main thing about `@on_error` is that it **returns a `Result`**. This result becomes the operation's output, and the error is considered handled: what comes out is not an exception but a meaningful answer. The machine meanwhile checks that exactly the declared `Result` type was returned.

**Run:**

```bash
uv run python examples/step_05_error_handling/01_on_error.py
```

**Output:**

```text
  on_error: invalid credentials

Result: username=bad, status=login_failed
```

The aspect failed with `ValueError`, the handler intercepted it, recorded the event, and returned `LoginResult(status="login_failed")` — the operation finished with a regular result, not an exception. For the rest of the system (including the [include contract](../reference/intents-and-invariants.md)) this is a successful completion: a result was obtained, even if through a handler.

## Several handlers: order and shadowing

There can be several handlers, and they are checked **top to bottom in declaration order** in the class; the first one whose type matches `isinstance` fires. Hence the rule: **specific first, then general**.

```python
@on_error(PaymentDeclinedError, description="Payment declined — a clear status for the client")
async def declined_on_error(self, params, state, box, connections, error):
    return CreateOrderResult(status="payment_declined")

@on_error(Exception, description="Everything else")
async def fallback_on_error(self, params, state, box, connections, error):
    return CreateOrderResult(status="error")
```

If you put the general handler before the specific one, it will **shadow** the specific one — which then never fires for any overlapping type. This is a trap worth knowing about: the declaration order is the checking order, and the machine does not reorder handlers or warn about shadowing on its own. Declare from particular to general. A single handler can cover several types at once — `@on_error((ValueError, KeyError), description=...)`.

## When no one caught it

If no handler matched by type, **the original error is propagated unchanged** (and to observers the machine emits an `UnhandledErrorEvent`). So "letting an error bubble up" means not writing a handler for it, rather than adding a catch-all `@on_error(Exception)`.

A separate case is a failure in the handler itself. If `@on_error` throws an exception while running, the machine wraps it in `OnErrorHandlerError`: the handling error is not masked as a business error. A handler is code that should reliably return a result, not a new source of failures.

## Three layers and their order

Let's assemble the full picture of a failure. When an aspect fails, the machine acts strictly in order:

1. **Rollback** — the saga unwind: compensators of the executed steps in reverse order ([the saga chapter](step-04-saga-and-compensations.md)).
2. **Handling** — `@on_error` receives the **original** error of the aspect (the unwind is transparent to it) and decides what to return.

The order is exactly this for a reason: compensators return the system to a consistent state, and `@on_error` already works with the rolled-back data while shaping the response. So the three concerns end up separated: **business logic** — in the aspects, **rollback** — in `@compensate`, **error handling** — in `@on_error`. Each layer reads on its own, and `try/except` in the operation body becomes nearly unnecessary.

## Invariants

- **The handler is declared and typed.** `@on_error(type, description=...)`: the type is a subclass of `Exception` (or a tuple of types), the description is non-empty; the method is async, the name ends with `_on_error`, the signature has 6 parameters (or 7 with `@context_requires`). A violation is an error at class declaration.
- **First match by type.** Handlers are checked top to bottom; the first matching by `isinstance` fires. Declaration order = checking order; shadowing is not tracked by the machine — that is the author's responsibility (particular → general).
- **Return a `Result`.** The handler returns the declared `Result`; this completes the operation normally. A failure of the handler itself → `OnErrorHandlerError`.
- **No match — no masking.** The original error is propagated unchanged; to observers — an `UnhandledErrorEvent`.
- **Layer order.** First compensations, then `@on_error` with the original error.

The full list is in [Intents and invariants](../reference/intents-and-invariants.md); the terms are in the [Glossary](../reference/glossary.md). Why error handling is moved into a separate layer is in the [Philosophy](../explanation/philosophy.md).

## Summary

`@on_error` turns error handling from a scatter of `try/except` into a visible contract: a handler is declared by type, checked in declaration order, returns a `Result` — or, if there is no match, lets the original error through. Together with `@compensate` this gives three independent layers — logic, rollback, handling — each of which reads on its own.

Next — **[Dependencies](../index.md#iii-business-logic)**: how an operation declares everything external through `@depends` and `@connection` and receives it, without hiding implicit couplings in its body.

---

## Review questions

1. Which three concerns does a single `try/except` usually blend, and across which three layers does AOA separate them?
2. What does `@on_error` return, and what happens to the operation meanwhile? Does it count as a successful completion?
3. In what order are handlers checked? What happens if a general `@on_error(Exception)` is declared before a specific one — and will the machine catch this?
4. Errors from which sources does `@on_error` catch? Does it catch a failure in the summary aspect and an exception from a resource?
5. What happens if no handler matches by type? And if the handler itself throws an exception?
6. In what order do the saga unwind and `@on_error` go, and which error does the handler receive?

> **Exercise.** Add a second error type to the example (e.g., `PermissionError`) and a separate `@on_error` for it, and at the end — a general `@on_error(Exception)`. Run the operation so that each of the three paths fires. Then move the general handler to the front and explain why the specific ones stopped firing.

---

<table width="100%"><tr>
  <td align="left"><a href="step-04-saga-and-compensations.md">← Step 04 — Saga and compensations</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-06-dependencies.md">Step 06 — Dependencies →</a></td>
</tr></table>
