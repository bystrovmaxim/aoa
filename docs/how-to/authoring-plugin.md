<!-- translated-from: authoring-plugin_draft.md @ 2026-06-17T11:07:16Z · sha256:1091fe8db5ba -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Your own plugin

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [The contract: two things](#the-contract-two-things)
- [Step 1. Subscribing to an event via `@on`](#step-1-subscribing-to-an-event-via-on)
- [Step 2. The run state](#step-2-the-run-state)
- [Step 3. Registration](#step-3-registration)
- [Filters: what reaches a handler](#filters-what-reaches-a-handler)
- [What is important to know](#what-is-important-to-know)
- [Verification](#verification)

---

## When this is needed

A plugin is an **observer** of the machine's lifecycle, not a participant. It reacts to typed events (operation start/finish, before/after each aspect, a saga rollback, an unhandled error) and is ideal for metrics, audit, tracing, side-effect logging. The shipped plugins [OpenTelemetry](../extensions/opentelemetry.md) and [OCEL](../extensions/ocel.md) are built exactly this way. The whole concept — [Step 9 — Plugins](../tutorials/step-09-plugins.md); here is how to write your own.

The full example: [03_custom_plugin.py](../../examples/how_to/03_custom_plugin.py).

## The contract: two things

Subclass `Plugin` (`from aoa.action_machine.plugin.core import Plugin`) and implement:

1. **`async get_initial_state()`** — fresh state for one run;
2. one or more **`@on(EventClass, ...)`** handlers with a fixed 4-argument signature:

```python
async def handler(self, state, event: EventClass, log) -> state
```

`state` — the current state of this run, `event` — a frozen event, `log` — a logger in the plugin's scope. The handler **must return the state** (possibly updated), and its name **must start with `on_`**.

## Step 1. Subscribing to an event via `@on`

`@on` (`from aoa.action_machine.intents.on import on, ...`) takes an event class. The subscription matches that class **and all its subclasses** via `isinstance` — hence the adjustable granularity:

```python
@on(BasePluginEvent)         # all events at all
@on(AspectEvent)             # all before/after of any aspects
@on(AfterRegularAspectEvent) # only after a regular aspect
@on(GlobalFinishEvent)       # only the operation finish (+ result, duration_ms)
@on(SagaRollbackCompletedEvent)  # only the completion of a saga rollback
@on(UnhandledErrorEvent)     # an error with no matching @on_error
```

The hierarchy mirrors the lifecycle: `GlobalStart/Finish`, aspects (`Regular`/`Summary`/`OnError`/`Compensate`, before/after), the saga rollback ([Step 4 — Saga](../tutorials/step-04-saga-and-compensations.md)), errors ([Step 5](../tutorials/step-05-error-handling.md)). Group classes (`AspectEvent`, `SagaEvent`) are not emitted themselves — they are only for subscription; the machine always sends a concrete leaf event. A typo in a class name fails at import, not silently at runtime.

## Step 2. The run state

A plugin **does not keep request state in instance fields**. At the start of each run the machine calls `get_initial_state()`, then threads this state through the plugin's handlers (each receives the current one, returns an updated one), and at the end of the run — discards it:

```python
async def get_initial_state(self) -> dict:
    return {"aspect_events": 0}      # fresh on EVERY run

@on(AspectEvent)
async def on_count_aspects(self, state, event, log):
    state["aspect_events"] += 1
    return state                     # goes into the next handler of this run
```

Need to accumulate **between** runs (a counter, an OCEL file, a metrics client) — inject external storage into the constructor:

```python
class CallAuditPlugin(Plugin):
    def __init__(self, sink: list) -> None:
        super().__init__()
        self._sink = sink            # outlives the runs

    @on(GlobalFinishEvent)
    async def on_record_finish(self, state, event, log):
        self._sink.append((event.action_name, state["aspect_events"]))
        return state
```

## Step 3. Registration

A plugin is supplied to the machine as a list — once per machine:

```python
machine = ActionProductMachine(plugins=[CallAuditPlugin(sink)])
```

Then operations run as usual — they know nothing about the plugin.

## Filters: what reaches a handler

Two levels of narrowing, both optional:

- **The `Plugin` constructor** — `super().__init__(watch_actions=..., watch_events=...)`: `watch_actions` (by `event.action_class`, via `issubclass` — subclasses count too) and `watch_events` (via `isinstance`). Did not call `super().__init__()` — you inherit `None` (no filtering).
- **`@on(...)`** — additional filters: `action_class`, `action_name_pattern`, `aspect_name_pattern`, `nest_level`, `domain`, `predicate=lambda e: ...`, `ignore_exceptions`. **Within one `@on` — AND**; several `@on` on one method give **OR**.

```python
@on(GlobalFinishEvent, nest_level=0, predicate=lambda e: e.duration_ms > 1000)
async def on_slow_root_call(self, state, event, log):
    ...
```

## What is important to know

- **An observer, not a participant.** All events are `@dataclass(frozen=True)`: the plugin reads the payload but changes neither the event, nor the result, nor the operation's state. A failing plugin must not bring down the operation — for that there is `ignore_exceptions=True`.
- **The handler name starts with `on_`**, the signature is exactly `(self, state, event, log)`, and it **returns state** (otherwise the next handler gets `None`).
- **`all_aspect_states`** in `GlobalFinishEvent` — snapshots of `state.to_dict()` after each regular aspect (this is how [OCEL](../extensions/ocel.md) gathers frames without touching the pipeline).

## Verification

```bash
uv run python examples/how_to/03_custom_plugin.py
```

```text
sink (action, aspect_events) per run -> [('GreetAction', 2), ('GreetAction', 2)]
```

`aspect_events == 2` is the before+after of the summary aspect in each run (the run state), and `sink` accumulated both records (external storage between runs). The operation did not change meanwhile. The whole plugin concept, with review questions — [Step 9 — Plugins](../tutorials/step-09-plugins.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
