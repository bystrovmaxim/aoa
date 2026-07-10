<!-- translated-from: supervisor-actions_draft.md @ 2026-06-21T01:10:11Z (filesystem mtime; draft is gitignored, no git history) · sha256:bf7ccba6fa55 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Supervisor Actions: a second control loop

<table width="100%"><tr>
  <td align="left"><a href="intent-oriented-ai-development.md">Intent-Oriented AI Development</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [The problem: the first control loop is static](#the-problem-the-first-control-loop-is-static)
- [The living-cell model](#the-living-cell-model)
- [The second loop: observation → interpretation → adaptation](#the-second-loop-observation--interpretation--adaptation)
- [Signals, not logs](#signals-not-logs)
- [SupervisorAction — not a god, a regulator](#supervisoraction--not-a-god-a-regulator)
- [A permission lattice](#a-permission-lattice)
- [Checkability of Supervisor decisions](#checkability-of-supervisor-decisions)
- [Grammar for operations](#grammar-for-operations)
- [Open questions](#open-questions)

---

## The problem: the first control loop is static

AOA in its current form implements a single loop: a human sets intents → the runtime checks invariants → the machine executes. That's a powerful model, but it assumes the system's structure is set in advance and changes only by a human's hand.

Real systems run into situations a human didn't anticipate: an anomalous spike in errors in a specific Action, degradation of a dependent service, a shift in load patterns. Today the only answer is to wait until a human notices the problem and steps in.

Supervisor Actions is a research question: can we add a second control loop, in which the machine observes itself, interprets signals, and makes adaptive decisions, without breaking IOP's guarantees?

---

## The living-cell model

A biological cell has two control loops. The first is executing the genetic program: protein synthesis, metabolism, maintaining homeostasis. The second is adaptation: receptors pick up signals from the environment, the nucleus interprets them and triggers changes in how the cell operates, without changing the genome.

AOA implements the first loop: a human sets intents, the machine checks and executes them. Supervisor Actions introduce the second loop: the machine observes itself, interprets signals, and adapts.

| Cell component | AOA component |
|---|---|
| Membrane receptors | Plugins — observe events, aggregate signals |
| Nucleus | SupervisorAction — interprets signals, makes decisions |
| Effectors | The control-command API — applies allowed changes |
| Genome | Action contracts, graph invariants, permission policies |

The key constraint: a cell's nucleus can't change the genome. A Supervisor can't change an Action's contracts, aspect structure, or graph invariants. It only operates within the space of allowed control commands.

---

## The second loop: observation → interpretation → adaptation

AOA's first loop: `a human sets an intent → the machine checks → the machine executes`.

The second loop, which Supervisor Actions introduce:

```
plugins observe events
        ↓
aggregate into domain signals
        ↓
SupervisorAction interprets
        ↓
issues a typed MachineCommand
        ↓
the policy engine checks the command
        ↓
the machine applies (or rejects) it
```

Every step of this loop goes through the same IOP principles: intents are typed, decisions are verifiable, changes are rollback-able.

---

## Signals, not logs

Plugins shouldn't send the Supervisor raw events. The telemetry stream is enormous, and the LLM agent inside the Supervisor would drown in noise.

Between the plugins and the Supervisor there needs to be an aggregation layer: a **Signal** — a domain-semantic fact about the system's state.

The difference matters:

```python
# A raw event (not this)
AfterRegularAspectEvent(action="CreateOrderAction", aspect="check_inventory", duration_ms=4200)

# A technical signal (operational degradation)
Signal(
    type="aspect_degradation",
    action="CreateOrderAction",
    aspect="check_inventory",
    error_rate=0.38,           # 38% over the last 5 minutes
    baseline_error_rate=0.02,  # the norm
    evidence=["timeout x47", "connection_refused x3"],
    window_minutes=5,
    confidence=0.96,
)

# A business signal (a shift in context)
Signal(
    type="context_shift",
    description="A new user segment with a high share of nighttime orders",
    action="CreateOrderAction",
    evidence=["+340% nighttime orders over 7 days", "average order value +28%"],
    window_minutes=10080,  # a week
    confidence=0.92,
)
```

A technical signal says: "the system is breaking." A business signal says: "the environment has changed." The Supervisor handles both — and this is exactly where AOA is fundamentally stronger than infrastructure systems. Kubernetes sees a pod, latency, a restart. AOA sees a business operation, an aspect, a domain, a compensator, an include dependency. The Supervisor can reason not "the service is unhealthy" but "the create-order operation is degrading at the inventory-check step."

---

## SupervisorAction — not a god, a regulator

The main trap when designing a Supervisor is giving it too much power. "A system that restructures itself" sounds nice, but it's architecturally toxic: if the Supervisor can change the pipeline arbitrarily, readability, reproducibility, and trust in the code all break down.

The Supervisor is a **homeostasis regulator**, not an architect. Its job is to keep the system in a stable state within pre-set boundaries, not to restructure the organism.

Concretely: the Supervisor must not change an Action's structure (add/remove aspects, change `@result_*` contracts). That's a code change, not a configuration change. The first version of the Supervisor only manages **configuration and operational decisions**.

---

## A permission lattice

Every possible Supervisor command is grouped by risk level:

**Observation (no changes):**
- create an anomaly report, raise an incident, request confirmation from a human

```python
MachineCommand(type="create_incident", severity="high", signal=signal, summary="...")
```

**Configuration changes (low risk):**
- change a limit, a timeout, a threshold, a feature flag

```python
MachineCommand(type="set_config", path="actions.CreateOrder.aspects.check_inventory.timeout_ms", value=8000)
```

**Operational switches (medium risk):**
- switch a Resource implementation, open a circuit breaker, enable a canary

```python
MachineCommand(type="switch_resource", action="CreateOrderAction", port="inventory",
               from_impl="PostgresInventory", to_impl="RedisInventory")
```

**Forbidden without manual confirmation:**
- change aspect structure, contracts, roles, domain invariants

```python
MachineCommand(type="add_aspect", action="CreateOrderAction", aspect="FraudCheck")
# ← rejected by the policy engine: structural changes are outside the allowlist
```

This lattice isn't an implementation detail — it's part of the Supervisor's architectural contract. Commands that don't fall within the allowlist are rejected by the policy engine before execution.

---

## Checkability of Supervisor decisions

If the Supervisor contains an LLM agent, its decisions can be hallucinations too. The IOP principle demands: **a Supervisor decision must go through the same verification loop as any other intent in the system**.

That requires typed `MachineCommand`s:

```python
@dataclass
class SwitchResourceCommand(MachineCommand):
    action: type[BaseAction]
    resource_port: str
    from_impl: type[BaseResource]
    to_impl: type[BaseResource]
    reason: str               # mandatory: why the Supervisor made this decision
    evidence: list[Signal]    # which signals support the decision
    rollback_after_minutes: int | None  # automatic rollback
```

The policy engine checks the command against the allowlist, blast-radius limits, a cooldown (no more than N commands per period), and idempotency. Only a command that passes gets applied. Every command is written to the audit log.

---

## Grammar for operations

Earlier in this section we discussed how AOA sets a **grammar for coding** — an AI agent writes Actions within a checkable architectural grammar, not arbitrary code.

Supervisor Actions introduce the next level: **grammar for operations**.

| Level | AI acts as | The grammar constrains |
|---|---|---|
| Development | An agent writing Actions | Contracts, aspects, the graph, TestBench |
| Operations | A Supervisor managing the machine | Policy, the command allowlist, blast radius, audit |

In both cases the AI doesn't work in an open space. It works inside a checkable lattice of intents. A hallucination during development → a contract violation → the test fails. A hallucination during operations → a command outside the allowlist → policy rejects it.

This is exactly the living-cell principle: the nucleus makes decisions, but the genome is untouchable.

---

## Open questions

Supervisor Actions is a research direction. Before implementing it, a number of questions need answers:

**Signal protocol:** how do you standardize a Signal so that a plugin can emit it and a Supervisor can accept it without either knowing the other's details?

**Causality:** how does a Supervisor tell correlation from causation? "CreateOrderAction failed 47 times" doesn't prove `InventoryCheckAction` is at fault. You need observation windows, a baseline, a confidence score.

**Feedback loops:** if the Supervisor applies a change and it makes the system worse, that produces new signals, which the Supervisor interprets again. How do you break a potential cycle?

**Testability:** a `SupervisorAction` must be testable through TestBench, with plugins and the LLM client substituted. How do you build a "world" for operational decisions?

**A human in the loop:** under what conditions must a Supervisor request confirmation from a human rather than applying a decision on its own?

These questions will shape the design before the first prototype.

---

Supervisor Actions isn't an attempt to make the system "smart" in some general sense. It's a logical extension of IOP: if a developer's intents are checkable and observable, why should an AI agent's decisions be an exception? We're building a system in which every level — from writing code to running it in production — obeys the same principles: contracts, checkability, observability, rollback.

---

*Status: draft. AOA research section.*
