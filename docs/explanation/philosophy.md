<!-- translated-from: philosophy_draft.md @ 2026-06-17T15:27:34Z · sha256:967ecba9084e -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# The philosophy of AOA

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

AOA is not only a set of rules but a way of thinking about business logic. This page explains *why* the architecture is built exactly this way: which ideas lie at its foundation and why they withstand the collision with real projects. If [The system from different altitudes](system-altitudes.md) shows *how* to read a system, here is *why* it is put together so. The precise rules and their checks are collected in [Intents and invariants](../reference/intents-and-invariants.md); the formal notation is in [The formal model](../reference/formal-model.md).

---

## The action as an atom

In ordinary code business logic is smeared: part in the controller, part in the service, part in the model, part in middleware. To understand what the system does, you have to read all of it at once, holding several contexts in your head simultaneously.

AOA says otherwise: every business operation is an atom. One class, one input, one output, a linear sequence of steps. Reading one `Action`, you see the scenario whole — from beginning to end, top to bottom. This is not cramping but liberation: the unit of understanding becomes the operation, not the file.

## The pipeline as predictability

Aspects execute strictly top to bottom, in the order they are declared in the class. At the machine level there are no branches, no hidden jumps, no magic hooks firing at an unexpected moment. The order is set by the method's position in the source file and does not depend on names, the alphabet, or the Python version.

Want to understand what will happen at execution — you read the aspects top to bottom. They will execute in exactly that order. Always. Predictability is not boring; it is reliable.

## Infrastructure outside the logic

When business logic knows about HTTP headers, about the format of an API response, about the layout of a table in the database — it stops being business logic and becomes a mix of domain and infrastructure that is hard to test and dangerous to change.

AOA draws a hard line: **`Action` makes decisions, `Resource` performs effects.** The operation does not know *how exactly* the data is stored — it only knows what it needs to get and what to return. The details are hidden behind ports, and a resource's implementation can be swapped without touching a line of logic.

## Immutability as protection from chaos

`Params`, `Result`, and `state` are immutable (`frozen`). This is not pedantry but protection. Since the input data cannot be changed mid-pipeline, an entire class of bugs is excluded — where one aspect quietly amended `params` and the next received something other than it expected.

`state` is not an exception but the most telling case: it is not a shared mutable bag but a **sequence of independent snapshots**. Each regular aspect receives a snapshot on input and returns a new snapshot on output — the previous one is not mutated. Intermediate data accumulates, but the accumulation is strictly confined within one call and visible as a sequence of verified states.

## Context — not an environment, but an explicit slice

The context carries user, request, and environment data — rich information and therefore dangerous. Let an operation read the context freely, and it will start depending on the transport: branches by IP or User-Agent will appear, behavior will differ depending on where the call came from. This is a straight road to chaos.

AOA does not make the context an ambient environment. An aspect receives not the whole context but its **explicitly declared slice** — through `@context_requires`. From the header it is visible which fields the operation needs, and `ContextView` will not let it read the undeclared. The full context is seen only by plugins — those who observe but do not interfere.

## Intents as a machine-readable specification

This, perhaps, is the main thing. When you write `@check_roles`, you do not merely guard a call — you formalize the access policy in machine-readable form. When you write `@depends` with a description, you create a living registry of what the operation depends on. When you hang checkers, you describe the step's contract in a form a program can read.

All these decorators forcibly turn business intent into data. And this is not documentation that goes stale — it is living, verified information, because without it the code will not run. From this follows a property rare for applied frameworks: every `Action` is a machine-readable specification of itself. Straight from the code, without a single extra line, you assemble the list of dependencies with descriptions, the role model, the ordered list of steps, the contract of each step, the declared connections. On this stand the system graph, the visualization in Maxitor, the "operation × role" matrix, the OpenAPI and MCP schemas — and the very ability to compare business intent between versions, rather than diffing lines of code.

## Dependencies — a contract, not a container

In most frameworks DI is a container: large, configurable, with its own modules, bindings, and providers. AOA looks at it more simply: DI is a contract between the operation and the infrastructure. The operation says "I need this", the machine provides. The `@depends` decorator and a factory that creates the needed object — and that is all; obtaining an undeclared dependency through `box.resolve(...)` is impossible. Simple, predictable, testable.

## Plugins — sensors, not participants

Plugins receive events and see what is happening: they can log, collect metrics, build traces. What they cannot do — change the system's behavior. This is fundamental: when observation is separated from execution, plugins can be added and removed without fear of breaking the logic, and a failure in a plugin does not bring down the request.

And the possibilities here are wider than "write to a log". A plugin of fifty lines can build a semantic execution tree — not a flat log but a graph with a `state` snapshot in each node, the duration of each aspect, and the full nesting of calls. Observability is built into the architecture not as an add-on but as a principle.

## Composition over inheritance

Classically logic is reused through inheritance: a base service, a child, overridden methods — and deep hierarchies grow that are hard to read and dangerous to change. AOA chooses composition: an operation calls another through `box.run(...)`, each is small and self-contained, complex processes are assembled from small ones, and a change in one does not break the others. The same thought as in functional programming: small pure units are easier to test and assemble than large classes with inheritance. It is no accident that aspects are not inherited into the pipeline automatically either — the composition of an operation must read from itself.

## Discipline that liberates

AOA requires following the rules: explicit `Params`, declared dependencies with descriptions, pure operations, linear aspects, immutable data, mandatory roles. At first glance — constraints. In practice — freedom: when the architecture does not let you write badly, you stop spending effort fighting the consequences of bad code and just write the logic.

Half a year later, code written by AOA's rules reads as easily as on the first day — the structure is the same, there are no surprises, and every operation carries a full description of its intents: who can call it, what it needs to work, which steps it passes through, what each step guarantees.

---

## In brief: the principles

1. `Action` — one business operation, readable whole.
2. An aspect — one step; the pipeline is linear and deterministic.
3. `Resource` — the single boundary with the external world.
4. `Params`, `Result`, `state` are immutable; `state` is a sequence of snapshots.
5. Context — not an environment, but a declared slice (`@context_requires`).
6. Dependencies — a contract (`@depends`), not a container.
7. Nested operations (`box.run`) instead of services; aspects are not inherited.
8. Plugins observe but do not interfere.
9. Intents are machine-readable — every `Action` is a specification of itself.
10. Testability is built in, not optional.

---

AOA does not invent new entities out of thin air. It takes the best of functional programming, clean and hexagonal architectures, pipeline and saga models — and brings them together into one small model that can be explained in an hour and that the machine checks for you. Minimum rules, maximum clarity. The precise, formal notation of these principles is in [The formal model](../reference/formal-model.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
