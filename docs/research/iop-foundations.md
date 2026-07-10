<!-- translated-from: iop-foundations_draft.md @ 2026-07-01T11:29:00Z (filesystem mtime; draft is gitignored, no git history) · sha256:fb8ffa88a2cd -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# IOP: intents, invariants, and architectural molecules

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="intent-oriented-ai-development.md">Intent-Oriented AI Development</a></td>
</tr></table>

- [The problem: intent as text drifts away from code quickly](#the-problem-intent-as-text-drifts-away-from-code-quickly)
- [IOP's basic thesis](#iops-basic-thesis)
- [Atoms: intents as invariants](#atoms-intents-as-invariants)
- [Molecules: Action and Resource](#molecules-action-and-resource)
- [Why an Action is not just a service](#why-an-action-is-not-just-a-service)
- [Why a Resource is not just an adapter](#why-a-resource-is-not-just-an-adapter)
- [How atoms assemble into an operation](#how-atoms-assemble-into-an-operation)
- [IOP in AOA: intent is already code](#iop-in-aoa-intent-is-already-code)
- [What this gives the system](#what-this-gives-the-system)
- [The short formula](#the-short-formula)

---

## The problem: intent as text drifts away from code quickly

Intent-Oriented Programming is often described as a way to express *what* a system should do before deciding *how* it will do it. In that form IOP looks like a language layered on top of code: a person describes the components, the flow, the rules, and the errors, and then an AI or a generator turns the description into an implementation.

That's an important idea, but it has a weak spot: if intent lives next to code, it has to be constantly synchronized with the code. Today the description says one thing, tomorrow the implementation does another, and the day after the tests check a third. Drift arises between intent, implementation, observability, and tests.

AOA takes a harder line: intent shouldn't be an external description. It should become a checkable part of the program itself.

---

## IOP's basic thesis

In AOA, Intent-Oriented Programming can be stated like this:

> **An intent is a checkable invariant of behavior or structure, expressed in code, carrying knowledge of the system's capabilities and constraints.**

This definition matters on two counts. First, an intent isn't just a wish, a task, or a description. If a statement can't be checked, it isn't an architectural intent — it's a comment, a wish, or a team agreement. It may be useful for communication, but the system can't hold onto it.

Second, an intent doesn't have to be only a business action. It can describe behavior (an `Action` is only reachable by the right roles, an aspect must return a field of the right type) or structure (an aspect method must have the `_aspect` suffix, an operation must have exactly one `@summary_aspect`, the dependency graph must be acyclic). In both cases it's knowledge about the system expressed not as external text but as part of the code itself.

Examples of intents that become invariants:

- An `Action` is reachable only by the roles declared through `@check_roles`.
- An operation has a domain, set through `@meta(domain=...)`.
- Every scenario has exactly one `@summary_aspect`.
- An aspect that declares `@result_string("order_id")` must return `order_id` of the right type.
- A compensator declared through `@compensate` must reference an existing step.
- Dependencies between operations must not form a cycle.
- A `Resource` from one domain must not be called directly from an `Action` in a different domain, if such an invariant is part of the project's architectural rules.

The last example matters: IOP isn't limited to the decorators that already exist. If a team formulates a new architectural rule and can make it checkable, that rule becomes a new atom of the language.

---

## Atoms: intents as invariants

An IOP atom is a minimal intent: an indivisible, checkable invariant, expressed in code.

In AOA these atoms aren't lines of documentation — they're declarations that the runtime, the graph inspector, the build, or CI can read and check:

| Atom | What it means | Where it's checked |
|------|-----------------|-----------------|
| `@check_roles` | who has the right to call the operation | runtime |
| `@meta(domain=...)` | which domain the operation belongs to | startup / graph |
| `@regular_aspect` | a scenario step with a human-readable description | startup / runtime |
| `@summary_aspect` | the single point where the result is assembled | startup |
| `@result_*` | the data contract on a step's output | runtime |
| `@depends` | a declared dependency on another capability | startup / runtime |
| `@connection` | an allowed external port | runtime / adapter |
| `@context_requires` | an explicit slice of context | runtime |
| `@compensate` | the intent to recover after a failure | startup / rollback |
| `@on_error` | explicit error handling | runtime |
| `Entity` relations | the domain model's structure | build |
| `Lifecycle` | admissible states and transitions | build / runtime |

Every atom answers one question: what must be true for the system to be considered correct?

This is exactly why `@result_*` isn't just validation. Validation usually checks data. An invariant checks an architectural promise: if an aspect said that after it `state` will hold `validated_order_id`, the next step has the right to rely on that. The error must occur at the point the promise is broken, not later as a `KeyError`, an incorrect sum, or a corrupted database record.

The boundary here is essential: it turns a statement into meaning. Without a boundary, "create an order" or "validate the cart" remains a phrase. With a boundary — roles, types, requiredness, domain, an admissible transition, an exit point — it becomes an intent the system can read, check, and admit into its grammar.

---

## Molecules: Action and Resource

Atoms on their own don't yet give you architecture. They have to assemble into stable units of behavior.

In AOA those molecules are `Action` and `Resource`.

`Action` is the molecule of a business scenario. It ties together the input, roles, domain, a linear pipeline of aspects, an intermediate `state`, dependencies, recovery, and the final `Result`.

`Resource` is the molecule of the outside world. It describes an allowed way to reach a database, an API, a queue, file storage, or another data source, without mixing that access with a business decision.

This gives a simple grammar:

- if it's a business intent, it must become an `Action`;
- if it's an exit to the outside world, it must go through a `Resource`;
- if data passes between steps, it must go through a checkable `state`;
- if there's an effect, a dependency, a role, a context, or a rollback, it must be declared as an invariant.

---

## Why an Action is not just a service

A typical service method often combines everything: authorization, reading data, a business decision, writing, logging, an error, transport details, and sometimes caching. The code may work, but its intent has to be reconstructed from the implementation.

An `Action` is built differently. It makes the scenario readable before you dive into the details:

```python
@meta(description="Create order draft", domain=OrderDomain)
@check_roles(CustomerRole)
class CreateOrderDraftAction(BaseAction[CreateOrderDraftParams, CreateOrderDraftResult]):
    @regular_aspect("Validate requested items")
    @result_string("validated_cart_id", required=True)
    async def validate_cart_aspect(...):
        ...

    @regular_aspect("Calculate draft totals")
    @result_int("total_cents", min_value=0)
    async def calculate_totals_aspect(...):
        ...

    @summary_aspect("Return order draft")
    async def build_summary(...):
        ...
```

Even without reading the method bodies, you can see the roles, the domain, the steps, the intermediate promises, and the exit point. This isn't comments on top of code. It's code that runs, is checked, is traced, and is shown on the system graph.

---

## Why a Resource is not just an adapter

A `Resource` doesn't make business decisions. It doesn't check roles, doesn't orchestrate a scenario, and doesn't decide what happens next. Its job is to be an allowed port to the outside world.

This constraint makes the system stronger:

- external access becomes enumerable;
- hidden SQL queries and stray HTTP calls don't get smeared across business code;
- tests can substitute the world around an operation without rewriting its internals;
- an AI agent gets a catalog of available capabilities, not an endless repository with arbitrary traversals.

If the method you need isn't in the `Resource`, the correct architectural behavior is not to write a direct query inside the `Action`, but to stop and record the absence of that port.

---

## How atoms assemble into an operation

IOP in AOA doesn't work through one big, universal contract, but through the accumulation of small, checkable promises.

An operation consists of several layers:

| Layer | What becomes explicit |
|------|----------------------|
| `Params` | what the operation accepts from outside |
| `@check_roles` | who has the right to call the operation |
| `@meta(domain=...)` | where the operation lives on the system map |
| `@regular_aspect` | which steps the scenario consists of |
| `@result_*` | what each step promises to the next |
| `state` | what checked information passed through the pipeline |
| `@depends` / `@connection` | which capabilities and ports are allowed |
| `@compensate` | how an already-executed effect is rolled back |
| `@on_error` | how an error turns into a managed outcome |
| `Result` | what the operation returns as its outcome |

These layers add up to an executable specification. That's why AOA can build a graph, generate OpenAPI and MCP schemas, collect traces, draw Maxitor diagrams, and check TestBench scenarios from one source of truth.

---

## IOP in AOA: intent is already code

The main difference between AOA and an external intent-language is that intent doesn't need to be compiled into a separate implementation and then hoped to stay in sync.

In AOA, intent is already built into the implementation:

- `Action` — the intent of a business operation;
- `Params` and `Result` — the external contract;
- `@regular_aspect` — the steps of the intent;
- `@result_*` — checkable promises of a step;
- `@summary_aspect` — the point where the final result is accepted;
- `@depends`, `@connection`, `@context_requires` — the allowed exits beyond local logic;
- `@compensate` and `@on_error` — the intent to recover;
- `TestBench` and WST — checking the scenario in a different reality;
- graph and Maxitor — a map of the available capabilities.

Here intent isn't a preliminary text for a generator. It's a falsifiable part of the program. If a promise is broken, the system fails at the point of the violation.

---

## What this gives the system

IOP gives AOA several properties that are hard to get through ordinary conventions:

1. **Local readability.** An operation reads top-to-bottom as a scenario, rather than having to be reconstructed from a chain of controllers, services, and helper methods.
2. **Checkability.** Intents don't stay in the team's head: they turn into invariants that the machine checks.
3. **Observability from the model.** Plugins see not just technical events but semantic nodes: an Action, an aspect, state, a rollback, an error.
4. **Testability through world substitution.** TestBench checks the scenario in a different reality, not internal mocks.
5. **A system map.** The graph and Maxitor get architectural meaning from the code, not from hand-written documentation.
6. **A foundation for AI development.** An LLM gets not a chaotic repository, but a grammar of admissible intents.

---

## The short formula

IOP in AOA can be compressed into three statements:

1. An intent is a checkable invariant of behavior or structure, expressed in code.
2. Minimal intents become the atoms of the system.
3. `Action` and `Resource` assemble these atoms into molecules of business behavior and the outside world.

This is exactly the foundation on which the next layer can be built: **Intent-Oriented AI Development**, where an AI agent works not in the open space of arbitrary code, but inside a checkable architectural grammar.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="intent-oriented-ai-development.md">Intent-Oriented AI Development</a></td>
</tr></table>
