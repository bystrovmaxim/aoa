<!-- translated-from: authoring-logger_draft.md @ 2026-06-17T11:10:41Z · sha256:9c2a5c183a0a -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Your own logger

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [The contract: one method, write](#the-contract-one-method-write)
- [Step 1. Implement write](#step-1-implement-write)
- [Step 2. Filtering via subscribe](#step-2-filtering-via-subscribe)
- [Step 3. Wiring](#step-3-wiring)
- [What is important to know](#what-is-important-to-know)
- [Verification](#verification)

---

## When this is needed

A logger is a **sink** for the business events an operation sends from aspects via `box.info / warning / critical(...)`. To deliver them to a new place — Kafka, Slack, PagerDuty, a JSON file — subclass `BaseLogger` and implement one method. The shipped [`ConsoleLogger`](../extensions/console-logger.md) is written exactly this way. The whole logging concept — [Step 10 — Logs as business events](../tutorials/step-10-logs.md); here is how to write your own sink.

The full example: [04_custom_logger.py](../../examples/how_to/04_custom_logger.py).

## The contract: one method, write

`BaseLogger` (`from aoa.action_machine.logging.base_logger import BaseLogger`) gives a two-phase pipeline `match_filters → write` and asks you to implement only the write:

```python
async def write(self, scope, message, var, ctx, state, params, indent) -> None
```

The coordinator does everything heavy **before** the loggers: it validates `var`, substitutes the templates (`{%var.x}`, `{iif(...)}`, `@sensitive` masking), and fans out to all loggers. Into `write` comes an **already-rendered string** `message`, and the message metadata is in `var`:

```python
var["level"]       # LogLevelPayload(mask=Level.*, name="INFO" | "WARNING" | "CRITICAL")
var["channels"]    # LogChannelPayload(mask=Channel.*, names="business" | ...)
var.get("domain")  # a BaseDomain subclass or None
```

`mask` is for logic (filters, routing), `name`/`names` for display.

## Step 1. Implement write

Writing is I/O into your sink. The method is async, so you do not have to block the event loop:

```python
from aoa.action_machine.logging.base_logger import BaseLogger

class JsonLinesLogger(BaseLogger):
    def __init__(self, sink: list) -> None:
        super().__init__()                 # brings up the subscribe/match/handle pipeline
        self._sink = sink

    async def write(self, scope, message, var, ctx, state, params, indent) -> None:
        self._sink.append({
            "level": var["level"].name,
            "channels": var["channels"].names,
            "message": self.strip_ansi_codes(message),   # strip ANSI if the sink is not a terminal
        })
```

`indent` is the nested-call depth; `scope` is the `{%scope.*}` coordinates; `strip_ansi_codes` is a ready base helper (colors in a template are for the console, not a file/Kafka).

## Step 2. Filtering via subscribe

Filtering is **not rewritten** — it is built in. Without subscriptions a logger accepts everything. With subscriptions a message passes if **any** matches (`OR` across rules); within one rule `channels`, `levels`, `domains` are `AND`. The method is fluent:

```python
logger = (
    JsonLinesLogger(sink)
    .subscribe("warn-only", levels=Level.warning)              # only WARNING
    .subscribe("audit", channels=Channel.business, domains=OrdersDomain)
)
```

`var` is already validated by the coordinator by this point, so the filters compare `var["level"].mask` / `var["channels"].mask` / `var.get("domain")` against the rules. The subscription key is unique (a duplicate → `ValueError`); `unsubscribe(key)` removes a rule.

## Step 3. Wiring

Loggers are collected into a `LogCoordinator` and passed to the machine:

```python
machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[logger]))
```

Several loggers work at once (console + Kafka + Slack), each with its own subscriptions. The operation sends `box.info(...)` and knows nothing about the sinks.

## What is important to know

- **The templates are already substituted.** Into `write` comes the final string; `{%var.*}`, `{iif}`, and `@sensitive` masks have been expanded by the coordinator — no need to re-parse.
- **The base does not swallow exceptions from `write`.** A sink failure will surface; resilience to delivery failures is your concern (a buffer, a retry, a try/except inside `write`).
- **Color is optional.** The `supports_colors` property (`False` by default) and `strip_ansi_codes(text)` help if the sink does not understand ANSI.
- **A logger ≠ a plugin.** A logger receives what the operation **intentionally** logged through `box`; a [plugin](authoring-plugin.md) observes the machine's lifecycle events (start/finish/aspects/saga) independently of the logs.

## Verification

```bash
uv run python examples/how_to/04_custom_logger.py
```

```text
shipped records (INFO dropped by subscription):
  {"level": "WARNING", "channels": "business", "message": "Large amount 5000.0 flagged"}
```

The operation logged two lines (`info` + `warning`); the subscription `levels=Level.warning` let only WARNING through, and the logger sent it as a structured record to the sink. The whole logging concept, with templates and review questions — [Step 10 — Logs as business events](../tutorials/step-10-logs.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
