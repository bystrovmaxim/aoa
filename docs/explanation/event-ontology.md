<!-- translated-from: event-ontology_draft.md @ 2026-06-26T23:35:08Z (filesystem mtime; draft is gitignored, no git history) · sha256:cee212e8e0ab -->
# Event ontology

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

AOA doesn't produce mere logs. Every observation, signal, and command is an instance of one and the same archetype, moving along a strictly defined causal chain. This document describes the ontology: what kinds of events exist, who produces them, and how they relate to one another.

---

## The archetype: Event

Every event type in AOA is a specialization of one archetype:

```
Event[T: BaseModel]:
  payload:  T       # typed payload (a Pydantic model)
  trace_id: str     # shared identifier of the causal chain
  mode:     Mode    # how it was produced
  effect:   Kind    # what it does to the system
```

`Mode` determines the nature of the producer:

| Mode | Who produces it |
|------|----------------|
| `Auto` | AOA's own architecture, with no developer code |
| `Intent` | Business code, explicitly, via `box.info()` / `box.warning()` / `box.critical()` |
| `Derived` | An analytical plugin observing the stream |
| `Reasoned` | An LLM inside a `SupervisorAction` |
| `Imperative` | Execution of a decision handed down from above |

`Kind` is the ontology's main cut:

- **Observational** (0–2): the system observes reality without changing it
- **Causal** (3–4): the system changes its own configuration or topology

---

## Five levels

### 0 — Impulses

**Mode:** Auto · **Kind:** Observational

AOA's architecture generates these on its own — without a single line of business code. Plugins (`OpenTelemetryPlugin`, `DbTelemetryPlugin`) read this stream read-only.

- `GlobalStartEvent` / `GlobalFinishEvent` — the pipeline started and finished
- `BeforeRegularAspectEvent` / `AfterRegularAspectEvent` — the transition from one `state` snapshot to the next
- Metrics: `duration_ms`, `shared_blks_read`, WAL size

Impulses carry no business meaning. They exist for SRE and for the immune system: "pressure dropped," "pulse is 120."

---

### 1 — Events

**Mode:** Intent · **Kind:** Observational

Business code explicitly names a fact of the subject area through `box`:

```python
await box.info("order.shipped", OrderShippedFact(order_id=order.id, carrier="FedEx"))
await box.critical("payment.declined", PaymentDeclinedFact(reason="limit_exceeded"))
```

Each event carries a `Channel` (business, audit, client), a `Domain`, `user_id`, `trace_id`. Events form the OCEL log for process mining. This isn't "a timeout error" — it's "a business operation failed."

---

### 2 — Signals

**Mode:** Derived · **Kind:** Observational

Analytical plugins (`BusinessMetricsPlugin`, `ImmunityPlugin`) continuously watch the stream of Impulses and Events. When homeostasis is violated, they produce a typed signal:

```python
class ConversionDropSignal(BaseModel):
    action: str
    trend: float      # e.g. 0.6 instead of the normal 0.95
    window_sec: int

class CriticalLatencySignal(BaseModel):
    p99_ms: float
    baseline_ms: float
```

The difference from level 1: level 1 says "the payment was declined," level 2 says "payments have been declining in 40% of cases over the last 5 minutes."

---

### 3 — Decisions

**Mode:** Reasoned · **Kind:** Causal

A `SupervisorAction` receives a Signal (level 2) + an execution tree (level 0) + business context (level 1). The LLM is isolated: no direct access to the database or the network. It reasons and returns a structured diagnosis:

```python
class SupervisorDecision(BaseModel):
    diagnosis: str                    # "PayPal gateway unavailable"
    confidence: float
    commands: list[AdminCommand]      # a typed treatment plan
```

A diagnosis is a thought, not an action. It changes the system only through level-4 commands.

---

### 4 — Commands

**Mode:** Imperative · **Kind:** Causal

Executing a `SupervisorDecision` via `box.run(AdminAction)`. Commands are strictly typed, protected by `@check_roles(SystemRole)`, and leave an OCEL audit trail:

```python
await box.run(ToggleFeatureFlagAction, ToggleFeatureFlagParams(
    flag="use_paypal", percent=0
))
await box.run(ToggleFeatureFlagAction, ToggleFeatureFlagParams(
    flag="use_stripe_fallback", percent=100
))
```

The command closes the loop: the new configuration is applied at level 0, and the system restores homeostasis.

---

## The causal chain

```
[Business code] ──box.info()──▶  1. EVENT
[AOA runtime]   ──auto──────▶  0. IMPULSE
                                      │
                               [Plugin]
                                      │
                                      ▼
                               2. SIGNAL (anomaly)
                                      │
                              [SupervisorAction + LLM]
                                      │
                                      ▼
                               3. DECISION (diagnosis + plan)
                                      │
                              [AdminAction]
                                      │
                                      ▼
                               4. COMMAND (configuration mutation)
                                      │
                                      ▼
                         [New homeostasis → loop closed]
```

All levels are connected through `trace_id`. Every level knows what it was derived from.

---

## What sets this ontology apart

In a typical framework, Impulses, Events, and Commands exist in parallel universes: a developer writes the logs, Datadog computes the metrics, an on-call engineer types commands into PagerDuty.

In AOA this ontology is **computable and connected**. An Event produces a Signal. A Signal produces a Decision. A Decision produces a Command. All of this happens within a single `trace_id`, runs through strict Pydantic typing, and is protected by AOA's contracts.

This isn't logging. It's an architecture of self-awareness.
