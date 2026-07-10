<!-- translated-from: opentelemetry_draft.md @ 2026-06-24T02:08:28Z (filesystem mtime; draft is gitignored, no git history) · sha256:d8f6774964c4 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# OpenTelemetry — traces and an x-ray of state

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [What it is](#what-it-is)
- [Installation](#installation)
- [Two signals](#two-signals)
- [Setup](#setup)
- [Parameters](#parameters)
- [What's inside the example](#whats-inside-the-example)

---

`OpenTelemetryPlugin` is a built-in [plugin](../tutorials/step-09-plugins.md): it turns every `machine.run()` into OpenTelemetry signals **without touching the business code**. It is an observer — it changes nothing in the execution flow, and its failure is isolated. The key principle: **the plugin contains no export logic** — where to send (console, file, any of dozens of OTel backends) is up to you, by passing a provider.

Example for this article: [01_opentelemetry.py](../../examples/extensions/01_opentelemetry.py).

## What it is

The plugin emits **two independent signals**; at least one is required:

| Signal | Provider | What it gives |
|--------|-----------|----------|
| **Traces** | `tracer_provider` | one root span per run + a child span for each aspect, `@on_error`, and compensator — timing and structure |
| **Logs** | `logger_provider` | a record per event with attributes `aoa.state.<field>` — an **x-ray of `state`** after each step; works even without traces |

The `state` x-ray is exactly that [observability of state](../tutorials/step-02-state-as-x-ray.md): each aspect's contribution to `state` is serialized into `aoa.state.*` attributes and is fit for inspection.

## Installation

```bash
pip install aoa-otel
```

## Two signals

- **Traces** only — you need timing and structure (Jaeger/Zipkin/Tempo): pass `tracer_provider`.
- **Logs** only — you need a self-contained audit and an x-ray of `state` with no trace backend: pass `logger_provider`.
- **Both** — the full picture: timing and `state` snapshots.

(The Logs signal in OpenTelemetry is not yet stabilized — the SDK lives under `opentelemetry.sdk._logs`.)

## Setup

You configure the provider (the backend is your choice), the plugin only emits:

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from aoa.otel import OpenTelemetryPlugin

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))   # or ConsoleSpanExporter / OTLP

machine = ActionProductMachine(plugins=[OpenTelemetryPlugin(tracer_provider=provider)])
```

The plugin is attached to the machine as a list item; the business code does not change. A single machine can hold several plugins — each sees its own part of the stream.

## Parameters

`OpenTelemetryPlugin(*, tracer_provider=None, logger_provider=None, service_name="...", max_field_length=..., watch_actions=None, watch_events=None)`:

- `tracer_provider` / `logger_provider` — at least one is required (otherwise `ValueError`).
- `service_name` — the service name in spans/records.
- `max_field_length` — truncation of long `state` values in attributes.
- `watch_actions` / `watch_events` — narrow the observation to the operations/events you need (for example, only `state` snapshots).

## What's inside the example

```text
Spans (timing & structure):
  tax_aspect
  build_summary
  PriceOrderAction

State x-ray (aoa.state.* from log records):
  aoa.aspect.regular.after  step=tax_aspect  state={'with_tax': 120.0}
```

You can see the operation's root span with children per step (Traces) and a `state` snapshot after a step in the `aoa.state.*` attributes (Logs) — both projections collected from one run, with not a line of observation in the operation itself.

The plugin concept is in the chapter [Plugins](../tutorials/step-09-plugins.md); how to write your own observer is in [«Your own plugin»](../index.md#how-to-write-your-own-extension).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
