<!-- translated-from: step-02-state-as-x-ray_draft.md @ 2026-06-17T17:53:37Z · sha256:b931686f28b9 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 02 — State: the operation's x-ray

<table width="100%"><tr>
  <td align="left"><a href="step-01-action-and-pipeline.md">← Step 01 — Action and the pipeline</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-03-authorization-and-roles.md">Step 03 — Authorization and roles →</a></td>
</tr></table>

- [Checkers](#checkers)
- [Independent state](#independent-state)
- [Contract violation](#contract-violation)
- [A contract-preserving aspect](#a-contract-preserving-aspect)
- [X-ray in the console](#x-ray-in-the-console)
- [X-ray to a file](#x-ray-to-a-file)
- [Opaque fields](#opaque-fields)
- [Checker reference](#checker-reference)
- [Review questions](#review-questions)

---

Every system has intermediate operation state. One step computes something — the next uses it. The only question is where that "something" lives and who is responsible for keeping it correct. In ordinary code the answer is vague: data goes into a mutable dictionary, an object field, a local variable — and if a step fails to put what the next one expects, the error surfaces not here but later: as someone else's `KeyError`, a wrong total in a calculation, a corrupted record in the database. The place of the cause and the place of the pain drift apart, and debugging turns into detective work.

AOA answers this sharply: here `state` is not a dictionary the steps exchange but a verifiable contract between them. Every regular aspect declares which fields it puts into state — `@result_string("order_id")`, `@result_int("quantity")`, `@result_instance("customer", CustomerProfile)` — and the machine checks what was returned against what was declared. If a field went missing, came out the wrong type, or broke a constraint, the next step simply will not run: control passes to error handling — [Saga rollback](step-04-saga-and-compensations.md) if the passed steps declared compensators, or [`@on_error`](step-05-error-handling.md) if there is a handler. The thing that holds this whole chapter together: a broken `state` does not pass further down the pipeline.

From this grows a property other systems extract through sweat and blood. Since each step declares and checks its own output, the machine sees not only the input `Params` and the final `Result` but the entire path between them: what appeared at each step, which constraints it passed, what was handed on. This is the **operation's x-ray**. It exists not because someone diligently scattered logs around, but because the model requires an explicit contract at every step. And so it is a property not only of debugging at the developer's desk but of a system running in production and watching itself.

Observability here is not nailed on the side. `state` is already structured and checked — all that remains is to surface it, and that is done by [plugins](step-09-plugins.md): they subscribe to the operation's lifecycle events — start, aspect completion, error, rollback — and watch from the outside, knowing nothing about the business code and interfering with nothing.

Below we walk this path from the beginning: first we establish what counts as a correct `state`, then plug in the OpenTelemetry plugin and see the same path from the outside, and finally learn to hide from observability what does not belong there — via `opaque=True`.

---

## Checkers

[▶ Try in Colab](https://drive.google.com/file/d/1elqy6vd_gmeZDQ9a63koxzp4PJxhoHAY/view?usp=drive_link) · [Open in project](../../examples/step_02_state_as_x-ray_of_the_operation/01_checkers.py)

A checker is a verifiable promise on an aspect's output: which field must appear in `state`, what type it is, and what constraints it obeys. A single aspect can declare its whole output contract at once — a stack of decorators above the method.

```python
@regular_aspect("Validate and normalise all order fields")
@result_string("order_id", required=True, min_length=5, max_length=20)
@result_int("quantity", required=True, min_value=1, max_value=999)
@result_float("unit_price", required=True, min_value=0.01)
@result_bool("is_urgent", required=True)
@result_date("delivery_date", required=True, date_format="%Y-%m-%d", min_date=datetime(2024, 1, 1))
@result_instance("customer", CustomerProfile, required=True, no_none=True, value_check=lambda c: c.is_active)
@result_string("coupon_code", required=False)
async def validate_aspect(self, params, state, box, connections):
    result: dict = {
        "order_id": params.order_id.strip().upper(),
        "quantity": params.quantity,
        "unit_price": params.unit_price,
        "is_urgent": params.is_urgent,
        "delivery_date": params.delivery_date,
        "customer": CustomerProfile(name=params.customer_name, is_active=True),
    }
    if params.coupon_code:
        result["coupon_code"] = params.coupon_code.strip().upper()
    return result
```

The stack reads like a contract written in plain language: after `validate_aspect`, `state` must contain `order_id`, `quantity`, `unit_price`, `is_urgent`, `delivery_date`, and `customer`; `coupon_code` may be absent, but if present it is a string. One checker per kind of data: a string with length bounds, an integer in a range, a number with a lower threshold, a flag, a date (as a string in a given format or a ready `datetime`), a class instance — and `value_check` lets you hang an arbitrary condition on top, here "the customer is active".

Constraints like `min_length` or `max_value` are optional. Even a bare `@result_string("name")` carries a contract — it fixes that the field must exist and that it is a string; the extra parameters are added when more than the type matters. In other words, a checker is always a promise about a field's existence and type, and constraints are merely its refinement.

What this buys you is visible in the next aspect. The terminal step receives an already-checked state and simply assembles the result, re-verifying nothing:

```python
@summary_aspect("Assemble validated order result")
async def assemble_summary(self, params, state, box, connections):
    total = round(state["quantity"] * state["unit_price"], 2)
    has_coupon = "coupon_code" in state
    await box.info(
        Channel.business,
        "order_id={%var.order_id}  total={%var.total}  urgent={%var.urgent}  coupon={%var.coupon}",
        order_id=state["order_id"],
        total=total,
        urgent=state["is_urgent"],
        coupon=has_coupon,
    )
    return OrderResult(...)
```

`assemble_summary` does not recompute or re-check `quantity` and `unit_price` — it trusts `state`, because the previous step already passed the contract. That trust is the whole point of checkers: downstream code works not with "some dictionary" but with state the machine has deemed valid. And the console output comes from the same place — the `box.info(...)` line gives birth to it.

**Run:**

```bash
uv run python examples/step_02_state_as_x-ray_of_the_operation/01_checkers.py
```

**Output:**

```text
Run 1: order with coupon code
  order_id=ORD-2024-001  total=149.97  urgent=True  coupon=True

Run 2: order without coupon (required=False → no error)
  order_id=ORD-2024-002  total=9.99  urgent=False  coupon=False
```

The first run is with a coupon, the second without. And here a subtlety is worth remembering: `required=False` does not switch the check off, it only allows the field to be absent. Should the field appear, it is still checked for type and constraints.

---

## Independent state

[▶ Try in Colab](https://drive.google.com/file/d/1G27ZaVAsJh7suA9rViFzI7p4BusCxq7G/view?usp=drive_link) · [Open in project](../../examples/step_02_state_as_x-ray_of_the_operation/02_independent_state.py)

Now to the property of `state` we noticed in the previous chapter but did not explain. `state` is not a shared basket where aspects pile up their goods. Each regular aspect receives a snapshot of state on input and returns a new, independent snapshot for the next one. A snapshot is a self-contained copy of the data at the moment the step finished; later steps do not touch it.

```python
@regular_aspect("Step 1: Normalise SKU")
@result_string("sku", required=True, min_length=3)
async def normalise_aspect(self, params, state, box, connections):
    return {"sku": params.raw_sku.strip().upper()}


@regular_aspect("Step 2: Validate quantity and forward SKU")
@result_string("sku", required=True)
@result_int("quantity", required=True, min_value=1, max_value=100)
async def validate_quantity_aspect(self, params, state, box, connections):
    return {
        "sku": state["sku"],
        "quantity": params.quantity,
    }
```

The line `"sku": state["sku"]` in the second aspect looks redundant — but it is not copying out of carelessness, it is a declaration of intent: "the field `sku` must live on." Fail to return it and the snapshot will contain only `quantity`.

The price of that line is small, and its benefit is not obvious until you picture a living project. Its pipelines get re-cut: steps are added, fields renamed, logic relocated. Were `state` a shared mutable object, fields would "leak" downward unnoticed — an aspect would receive data it never subscribed to, and an innocent reordering of steps would change behavior on the sly. A sequence of independent snapshots kills that hidden coupling at the root: a field exists exactly where it was explicitly declared and returned. The same trait makes an aspect testable on its own — its input and output are fully defined by the contract, and there is no need to substitute "internals".

**Run:**

```bash
uv run python examples/step_02_state_as_x-ray_of_the_operation/02_independent_state.py
```

**Output:**

```text
sku='ABC-001', quantity=5, line_total=500
```

---

## Contract violation

[▶ Try in Colab](https://drive.google.com/file/d/1L3CjV5XoxHCcGmxKfsoAtF-qztAOPXP9/view?usp=drive_link) · [Open in project](../../examples/step_02_state_as_x-ray_of_the_operation/03_contract_violation.py)

Theory is worth testing on a broken case. Here is an aspect that promises a required `sku` but returns only `quantity`:

```python
@regular_aspect("Intentionally broken step")
@result_string("sku", required=True)
@result_int("quantity", required=True, min_value=1)
async def broken_aspect(self, params, state, box, connections):
    return {"quantity": params.quantity}
```

Without a contract, the error would slip into the shadows and resurface later — a `KeyError` in the terminal step, a wrong total in a calculation, a corrupted row in the database. The checker keeps cause and effect from drifting apart: the violation is recorded exactly at the boundary of the aspect that allowed it. This is fail-fast raised to the level of the model, not a scatter of manual checks that someone will eventually be too lazy to write.

**Run:**

```bash
uv run python examples/step_02_state_as_x-ray_of_the_operation/03_contract_violation.py
```

**Output:**

```text
ValidationFieldError: Missing required parameter: 'sku'
(Next step never ran — error is immediate)
```

The second line matters more than the first: the next step did not run at all. The error stayed at the boundary and never reached the code that would have followed it.

---

## A contract-preserving aspect

[▶ Try in Colab](https://drive.google.com/file/d/1qyyAl6D2bM3bpGYTKkObbbC-uux55xKS/view?usp=drive_link) · [Open in project](../../examples/step_02_state_as_x-ray_of_the_operation/04_contract_preserving_step.py)

A contract protects not only a single aspect — it also protects the rebuilding of the pipeline itself. That is less obvious and therefore more important.

Picture a working chain: an aspect normalizes the item, the terminal step assembles the result. Between them a new step needs to go in — notify an operator, write diagnostics, prepare data for a neighboring system. It must not change the business state. But it stands in the middle, and its output dictionary becomes the input for the terminal step — so it is obliged to return the same contract the code that follows expects.

```python
# Before: data flows straight into summary
@regular_aspect("Normalise item")
@result_string("sku", required=True, min_length=3)
@result_int("quantity", required=True, min_value=1)
async def normalise_aspect(self, params, state, box, connections):
    return {"sku": params.raw_sku.strip().upper(), "quantity": params.quantity}


# After: a new step is inserted between normalise_aspect and summary
@regular_aspect("Inform operator without changing business state")
@result_string("sku", required=True, min_length=3)
@result_int("quantity", required=True, min_value=1)
async def inform_aspect(self, params, state, box, connections):
    # This could be a notification, an audit entry, a debug event.
    # But for the next step this aspect must be transparent.
    return {"sku": state["sku"], "quantity": state["quantity"]}
```

The contractual side: `inform_aspect` may not rely on "the old `state` somehow passing through on its own" — it must return `sku` and `quantity` explicitly. The defensive side: if, while inserting the step, the developer forgets `quantity`, the terminal aspect will not run, and the error stays here, at the output of `inform_aspect`, rather than resurfacing later as a random `KeyError`. This is how `state` becomes a boundary that, on every change to the pipeline, demands a fresh confirmation: the downstream code still receives what it counts on. That is why it is safe to change not only an aspect's innards but the very shape of the pipeline — adding steps, as long as each one honestly preserves the contract for the next.

**Run:**

```bash
uv run python examples/step_02_state_as_x-ray_of_the_operation/04_contract_preserving_step.py
```

**Output:**

```text
baseline result       = sku='ABC-001', quantity=5, line_total=500
with informing step   = sku='ABC-001', quantity=5, line_total=500
inform_aspect is allowed only because it preserves the downstream state contract
```

---

## X-ray in the console

[▶ Try in Colab](https://drive.google.com/file/d/1ZI8Evretmhze7n1-To6nm7jZuwol1Bz8/view?usp=drive_link) · [Open in project](../../examples/step_02_state_as_x-ray_of_the_operation/05_xray_console.py)

So far `state` has been visible only from inside the code. Let's plug in [OpenTelemetry](https://opentelemetry.io/) — the common observability standard with its traces and logs — and see the same path from the outside. One `machine.run()` gives one trace; each aspect inside is its own span.

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, SimpleLogRecordProcessor
from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin

tp = TracerProvider()
tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

lp = LoggerProvider()
lp.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogRecordExporter()))

plugin = OpenTelemetryPlugin(
    tracer_provider=tp,
    logger_provider=lp,
    service_name="checkout-service",
)
machine = ActionProductMachine(plugins=[plugin])
```

Note: the business code of `CheckoutAction` is not touched by a single line. Observability is wired at the machine level — the operation still describes the business, and the plugin watches its life from the side. It emits two signals: `tracer_provider` turns on traces (a root span for the whole run and child spans for each aspect), and `logger_provider` turns on logs about lifecycle events, including `state` snapshots after regular aspects.

A snapshot looks like this — after a `@regular_aspect` the log record itself gains `aoa.state.<field>` attributes, exactly what the aspect returned and what the machine validated with checkers:

```json
{
    "body": "aoa.aspect.regular.after",
    "attributes": {
        "aoa.action": "CheckoutAction",
        "aoa.aspect": "validate_aspect",
        "aoa.duration_ms": 0.021,
        "aoa.state.sku": "WIDGET-42",
        "aoa.state.quantity": 3
    },
    "trace_id": "0xc86725ae...",
    "span_id": "0x6b0241bd...",
    ...
}
```

After the next aspect, `"aoa.state.total": 59.97` is added — a field born exactly at that step. The records show how `state` grew step by step. To stress the point: this is not a log someone wrote by hand inside an aspect, but an automatic projection of already-validated state. Observability comes free of a single logging line in the business code.

**Run:**

```bash
uv run python examples/step_02_state_as_x-ray_of_the_operation/05_xray_console.py
```

In the console two kinds of objects will appear: spans (`"name": "validate_aspect"`) and logs (`"body": "aoa.aspect.regular.after"`), tied by a common `trace_id`. One run is one trace, inside which both the steps and the state are visible.

It is easy to conflate two layers of observation here, yet they are distinct and irreplaceable:

- `box.info(Channel.business, ...)` — a **business event** the operation writes itself: "what meaningful thing happened in the domain";
- `OpenTelemetryPlugin` — **technical observation** of execution: "what data passed through the pipeline".

One answers the question of meaning, the other the question of mechanics, and it is unwise to substitute one for the other.

---

## X-ray to a file

[▶ Try in Colab](https://drive.google.com/file/d/1X-4p5yGmdr5bNTkKrt6oSKAZ8MhZeDOm/view?usp=drive_link) · [Open in project](../../examples/step_02_state_as_x-ray_of_the_operation/06_xray_file.py)

The console is good for a first acquaintance; in production telemetry is written to a file, an agent, or an external backend. At the same time, let's show how to select only the events you need.

### Writing to a file

The `ConsoleSpanExporter` and `ConsoleLogRecordExporter` exporters accept `out` — any file-like object.

```python
with open("traces.txt", "w") as traces_file, open("logs.txt", "w") as logs_file:
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=traces_file)))

    lp = LoggerProvider()
    lp.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogRecordExporter(out=logs_file)))
```

After the run the spans end up in `traces.txt`, the log records in `logs.txt`.

### watch_events — filter by event type

By default the plugin receives all lifecycle events. Often you need fewer — for example, only `state` snapshots and the finish. That is what `watch_events` is for:

```python
from aoa.action_machine.plugin.core.events import AfterRegularAspectEvent, GlobalFinishEvent

plugin_logs = OpenTelemetryPlugin(
    logger_provider=lp,
    service_name="checkout-service",
    watch_events=frozenset({AfterRegularAspectEvent, GlobalFinishEvent}),
)
```

Such a plugin will see only `AfterRegularAspectEvent` (the `state` snapshot after a regular aspect) and `GlobalFinishEvent` (the operation's completion); everything else is filtered out before its handlers.

From here comes the technique the plugin architecture rests on. On one machine you can place two independent plugins:

```python
machine = ActionProductMachine(plugins=[plugin_traces, plugin_logs])
```

`plugin_traces` writes the full trace to `traces.txt`, `plugin_logs` writes selected records to `logs.txt`. Both work on a single run, but each sees its own slice of events. Observation is assembled from several independent projections — and each can be configured separately.

**Run:**

```bash
uv run python examples/step_02_state_as_x-ray_of_the_operation/06_xray_file.py
```

**Output:**

```text
Result: Order confirmed: 3x WIDGET-42 = $59.97

Traces written to: .../step_02_state_as_x-ray_of_the_operation/traces.txt
  (root span + 2 child spans — one per @regular_aspect)

Logs written to:   .../step_02_state_as_x-ray_of_the_operation/logs.txt
  (only AfterRegularAspectEvent + GlobalFinishEvent)
  (Before*/Start events filtered out by watch_events)
```

Open both files: `traces.txt` shows the structure of execution, `logs.txt` shows the selected state data.

---

## Opaque fields

[▶ Try in Colab](https://drive.google.com/file/d/19EuOPk9IgdW3QfqRunB-G17bGTDIZV9O/view?usp=drive_link) · [Open in project](../../examples/step_02_state_as_x-ray_of_the_operation/07_opaque.py)

An x-ray is good exactly as long as it does not show too much. Some fields are needed inside the operation but have no place in the observability layer: a payment token, a temporary key, a raw response from a foreign system, a heavy connection object. They may be part of `state`, but serializing them into logs is not allowed — sometimes for sensitivity, sometimes for weight, sometimes simply for uselessness.

For this, every checker has `opaque=True`.

```python
@regular_aspect("Validate order and mint payment token")
@result_string("order_id", required=True, min_length=3)
@result_string("payment_token", required=True, opaque=True)
async def payment_aspect(self, params, state, box, connections):
    token = f"tok_live_{params.card_last4}_{'x' * 16}"
    return {
        "order_id": params.order_id.upper(),
        "payment_token": token,
    }
```

`payment_token` remains a full-fledged part of `state`: the checker validates it, the following aspects read it. The only difference — the plugin will not surface it into `aoa.state.*` attributes:

```json
{
    "body": "aoa.aspect.regular.after",
    "attributes": {
        "aoa.action": "ChargeOrderAction",
        "aoa.aspect": "payment_aspect",
        "aoa.duration_ms": 0.025,
        "aoa.state.order_id": "ORD-2024-001"
    },
    ...
}
```

There is no `aoa.state.payment_token` attribute here.

It is important to understand what exactly the flag describes. `opaque=True` is not about "secrecy" in the legal sense but about the observability boundary: this value is not surfaced. It may be sensitive, heavy, unstable, or simply useless for analysis. The rule is simple: a field needed only to continue the operation and not involved in diagnostics is marked `opaque=True`.

**Run:**

```bash
uv run python examples/step_02_state_as_x-ray_of_the_operation/07_opaque.py
```

---

## Checker reference

This section is for coming back to: keep it at hand when you write your own operations.

### Checker types

| Checker                              | Field type           | Extra parameters                        |
| ------------------------------------ | -------------------- | --------------------------------------- |
| `result_string(field, ...)`          | `str`                | `min_length`, `max_length`, `not_empty` |
| `result_int(field, ...)`             | `int`                | `min_value`, `max_value`                |
| `result_float(field, ...)`           | `float`              | `min_value`, `max_value`                |
| `result_bool(field, ...)`            | `bool`               | —                                       |
| `result_date(field, ...)`            | `str` or `datetime`  | `date_format`, `min_date`, `max_date`   |
| `result_instance(field, Class, ...)` | instance of `Class`  | `no_none`, `value_check`                |

### Common parameters

| Parameter  | Default | Meaning                                                                  |
| ---------- | ------- | ------------------------------------------------------------------------ |
| `required` | `True`  | `True` — the field must be present; `False` — the field may be absent    |
| `opaque`   | `False` | `True` — the field is excluded from the `aoa.state.*` OTel Logs attributes |

### Behavior on violation

All checkers raise `ValidationFieldError` with the field name and a description of the violation — immediately on the aspect's completion, before control passes to the next one.

```python
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
```

### Declaring multiple fields

A contract is assembled from several `@result_*` decorators — one per field.

```python
@regular_aspect("Multi-field step")
@result_string("name", required=True, min_length=2)
@result_int("age", required=True, min_value=0, max_value=150)
@result_bool("is_verified", required=True)
@result_string("nickname", required=False)
async def some_aspect(self, params, state, box, connections):
    ...
```

Every field of a non-empty dictionary must be declared. A field without a checker is a hidden contract, and AOA does not recognize such invisible boundaries.

---

## Summary

`state` is neither global memory nor a basket for temporary data, but a sequence of independent, verifiable snapshots: each is born explicitly, checked immediately, and becomes the contract for the next step. Two things rest on this at once — testability (an aspect's input and output are fully defined by the contract) and observability (the snapshot projects itself outward).

That is why `state` can be surfaced without worry as the operation's x-ray — it shows not only the input and the `Result` but the whole path: where the data appeared, where it was checked, where the pipeline stopped on a violation. And `opaque=True` draws the boundary of that output: the field stays inside the operation but does not leave for `aoa.state.*`.

---

## Review questions

1. Why is `state` in AOA a verifiable contract rather than a mutable dictionary? Which two properties of the system does this provide?
2. Which invariant keeps a broken `state` from reaching the next step, and at what moment does it fire?
3. How is a sequence of independent snapshots better than shared mutable state when the pipeline's structure changes?
4. `required=False` versus the complete absence of a checker on a field — what is the difference at the level of the contract?
5. The `state` x-ray and `box.info(Channel.business)` are two layers of observation. What is the difference, and why does one not replace the other?
6. What does `opaque=True` describe — secrecy or the observability boundary? What happens meanwhile to the field's availability inside the operation?

> **Exercise.** Add a `discount: float` field to `01_checkers.py` with `min_value=0` and `max_value=1`. First return a valid value and confirm the operation passes; then return `1.5` and determine which invariant fires and at which boundary.

---

<table width="100%"><tr>
  <td align="left"><a href="step-01-action-and-pipeline.md">← Step 01 — Action and the pipeline</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-03-authorization-and-roles.md">Step 03 — Authorization and roles →</a></td>
</tr></table>
