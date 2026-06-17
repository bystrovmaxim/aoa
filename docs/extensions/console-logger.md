<!-- translated-from: console-logger_draft.md @ 2026-06-17T17:02:35Z · sha256:b59a0fb1287a -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# ConsoleLogger — business events to the console

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [What it is](#what-it-is)
- [Setup](#setup)
- [Filtering: subscriptions](#filtering-subscriptions)
- [Parameters](#parameters)
- [What's inside the example](#whats-inside-the-example)

---

`ConsoleLogger` is a built-in logger: a sink that prints business events (`box.info/warning/critical`) to stdout. Delivery is decided by the logger, not by the operation code — that is the topic of the chapter [Logs as business events](../tutorials/step-10-logs.md); here is the card for the ready-made sink. **Ships out of the box**, no separate `pip` extra needed.

Example for this article: [01_logging_sensitive.py](../../examples/step_10_logs/01_logging_sensitive.py).

## What it is

One line per accepted event, via `print`. When color is enabled, the line gets truecolor by [level](../tutorials/step-10-logs.md): `info` — white, `warning` — yellow, `critical` — red (explicit colors from in-string templates are preserved). Nested calls are indented.

## Setup

Loggers are attached to the machine through `LogCoordinator`; the operation code knows nothing about the console:

```python
from aoa.action_machine.logging import ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator

machine = ActionProductMachine(
    log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
)
```

Without a coordinator, `box` events are silently dropped — logging is switched on and off from the outside, without touching the operation.

## Filtering: subscriptions

By default a logger **with no subscriptions accepts everything**. To narrow the stream, add subscriptions:

```python
logger = ConsoleLogger()
logger.subscribe("audit", channels=Channel.security, levels=Level.critical)
```

Within a single subscription the conditions `channels` / `levels` / `domains` are combined with **AND**; multiple subscriptions are combined with **OR**; `subscribe` returns `self` for chaining. This is how you keep several loggers on one machine, each with its own slice of the stream (everything — to the console; only `security`-critical — to another sink).

## Parameters

`ConsoleLogger(use_colors=True, use_indent=True, indent_size=2, level_fg_prefixes=None)`:

- `use_colors` — ANSI coloring by level (turn off for files/CI);
- `use_indent` / `indent_size` — indentation by call nesting;
- `level_fg_prefixes` — override the base color for specific levels (`{Level.warning: "\033[…m"}`).

## What's inside the example

```text
  Login: user=alice, amount=500.0
  Info: normal transaction
  Warning: amount 500.0 requires review
  Critical: amount 500.0 requires review
  Token: tok*****
```

You can see substitution, the `iif` branch, the `warning`/`critical` levels (different colors in a terminal), and the masked `@sensitive` token. Channels, levels, templates, and masking are covered in detail in the chapter [Logs as business events](../tutorials/step-10-logs.md); your own delivery (Kafka, Slack, PagerDuty) is [«Your own logger»](../index.md#how-to-write-your-own-extension).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
