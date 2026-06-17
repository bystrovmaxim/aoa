<!-- translated-from: questions-aoa-answers-with-code_draft.md @ 2026-06-17T15:30:38Z · sha256:660d8daec439 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Questions AOA answers with code

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [One question in twelve projections](#one-question-in-twelve-projections)
- [What the system knows about itself](#what-the-system-knows-about-itself)
- [What binds the steps](#what-binds-the-steps)
- [Who consumes the system](#who-consumes-the-system)

---

## One question in twelve projections

This is not about how AOA is better than others. It is about something else: which class of problems it makes **visible and manageable** — the one that in ordinary code stays either an agreement in the developer's head or an implicit fact of the runtime that you have nothing to point a cursor at.

The twelve questions below look different, but they are one question turned by different facets:

> What in AOA becomes a **formal object** — explicit, verifiable, accumulative — while in ordinary code it stays implicit?

Here is where the bet of [IOP](../reference/intents-and-invariants.md) runs: an intent must stop being a comment or a verbal agreement and become an **invariant of the architecture and execution** — explicit, enforced, accumulative. Checkers, the graph, the state x-ray, roles, the saga — behind them all is one move: turn an intent into an object the system checks instead of you.

The answers stay short — this is a map, not a textbook. Behind each is a mechanism and a link to the chapter where it is proven by code; and where the line between "can do today" and "open question" runs, it is said plainly.

---

## What the system knows about itself

Before asking what the system does, it is worth asking what it knows about itself — about its own structure, the course of an operation, its weak spots.

**1. What changes when a program's structure stops living in the head and becomes an object you can ask a question of?**
An operation's steps, roles, resources, entities, state transitions — AOA assembles them at startup into a **typed graph**, out of the same intents the code is written with. What changes is not the volume of documentation but the very genre of relations with the system: it can be not retold from memory but walked and questioned. What is usually kept in the README and in someone's head becomes a [formal model](../reference/formal-model.md) and an [operation graph](../tutorials/step-26-maxitor.md), available programmatically.

**2. Can a program explain itself — and at what moment?**
Before the first request it already knows the whole graph: which steps lie ahead, which roles the operation requires, which resources and entities it will touch. During execution the step-by-step immutable state is visible — the [state x-ray](../tutorials/step-02-state-as-x-ray.md) — and the typed events of each aspect. And afterward there remains the result and, if desired, a trace in the process-mining format [OCEL](../extensions/ocel.md). Three slices, and not one has to be assembled by hand: all are derived from [the same model](../tutorials/step-11-machine.md).

**3. Which defects stop being a matter of a reviewer's attentiveness and become a property of the structure?**
A role is a node of the graph, and [`@check_roles`](../tutorials/step-03-authorization-and-roles.md) is an edge from it to an operation; if no edge enters a role, it opens access to nothing. Catching this by eye at review is possible, but unreliable — whereas by walking the graph it is simply computed, without a single runtime request. The same walk uncovers other structural flaws too: a working [self-audit](../research/self-knowledge.md) is shown in [01_self_audit.py](../../examples/research_self_knowledge/01_self_audit.py).

**4. Can you ask the system where it risks leaving the world in a half-done state?**
A saga in AOA ([how it is built](../tutorials/step-04-saga-and-compensations.md)) is not a scatter of `try/except` but a structure: a step with a side effect either has a declared compensator or it does not, and this is a property of the graph. So "a step changed something, but it has no rollback" turns out not a matter of discipline but a **computable gap**, which [self-knowledge](../research/self-knowledge.md) shows already today. Beyond that begins the honest frontier: whether there even should be a rollback here is something the machine does not yet decide, and we assign that question to the [open part of the model](../reference/formal-model.md).

## What binds the steps

The graph shows what an operation is assembled from. But more interesting is the other thing — what holds its steps to one another.

**5. What happens to trust between steps when state is not inherited by default but re-declared anew?**
Each step is obliged to say explicitly, with a checker, what it leaves further on: which field, of which type, for whom. This is a discipline of distrust by default, and it pays off — the promise "here `txn_id` appears" becomes an invariant, while the violator does not survive to the build. Hence [`@result_*` checkers](../tutorials/step-02-state-as-x-ray.md) are a contract between steps, not a "check just in case".

**6. Why is a change in the middle of a long-written process a local event, not minefield work?**
In ordinary code a new step in the middle of a chain quietly tears others' expectations: someone below counted on the order or on a field that is now gone — and you learn about it in production. Here [state does not accumulate on its own](../tutorials/step-02-state-as-x-ray.md), each step re-declares its output, so a torn thread surfaces at [graph build](../tutorials/step-11-machine.md) — at the same place it arose, not three screens later.

**7. What is the difference between a program's story about itself and its model?**
A log is what a developer did not forget to print: a flat string from which the step's structure has already evaporated. The [state x-ray](../tutorials/step-02-state-as-x-ray.md) is the operation's step-by-step state itself as an object: what came into an aspect, what it added, what went on. One stays a narrative of execution, the other its model, and [OpenTelemetry](../extensions/opentelemetry.md) takes the second as is.

**8. What does it mean that observability cannot be forgotten to switch on?**
Bolted-on observability is held by hand: you placed spans and counters — you see; you missed one — a blind spot exactly where it is most interesting. In AOA traces, events, and state slices are [derived from the same graph and pipeline](../tutorials/step-09-plugins.md) the operation runs on, so observability turns out a byproduct of the model, not a separate line item of work ([OpenTelemetry](../extensions/opentelemetry.md)).

## Who consumes the system

A system has three kinds of consumers — other code, its own tests, and the external world, be it a human or an agent. To each the formal model gives what an ordinary service cannot.

**9. How does a promise given to the machine differ from a note left for a colleague?**
A decorator-comment is a note for a human: it obliges nothing and guarantees nothing. An intent in AOA — `@meta`, `@check_roles`, aspects, checkers — [becomes a node and an edge of the graph](../tutorials/step-01-action-and-pipeline.md), which the machine executes and checks. The difference is not in syntax but in the addressee: the promise is given not to a colleague but to the executor, and it has consequences — at runtime and at build.

**10. Why does an observer in AOA not need to reconstruct meaning from bytes?**
An ordinary hook sees opaque request and response and guesses the rest. A plugin receives [typed domain events](../tutorials/step-09-plugins.md): which operation, which aspect, which state, whether the saga rollback started, whether an error was left without a handler. So metrics and audit are written straight in business terms, not transport — and [writing such a plugin](../how-to/authoring-plugin.md) costs a few methods.

**11. Why can a test survive a refactoring that changes the whole internal mechanics?**
A test with mocks fixes that the code called exactly what we expected — and breaks at any rearrangement inside, even a correct one. [TestBench](../tutorials/step-23-testbench.md) runs the same operation through the same machine, [substituting only the environment](../tutorials/step-24-substitution.md) — the user, resources, nested operations. It checks the intent of the scenario, not the chain of calls, and therefore holds on to what should stay unchanged.

**12. What is an agent that already has logs and OpenAPI missing, to reason rather than guess?**
OpenAPI answers the question "how to address" — that is the syntax of the call. The second question is missing — "what it means": the operation's contract, the required roles, the steps, the state. AOA hands over this semantics through [MCP](../tutorials/step-14-mcp.md) and the [graph](../research/self-knowledge.md), and the agent stops being a blind caller — it can reason that an operation requires an admin, or that the payment step is failing right now and should not be called ([the MCP extension](../extensions/mcp.md)).

---

Twelve answers add up to one move: **an intent turned into an object the system checks for you.** Everything else in this documentation is the proof of this by code. Next — in order: [Contents](../index.md).

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
