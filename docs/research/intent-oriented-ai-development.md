<!-- translated-from: intent-oriented-ai-development_draft.md @ 2026-07-01T11:29:00Z (filesystem mtime; draft is gitignored, no git history) · sha256:862fe10ebf76 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Intent-Oriented AI Development

<table width="100%"><tr>
  <td align="left"><a href="iop-foundations.md">IOP: Intents and Invariants</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [Where IOP comes from](#where-iop-comes-from)
- [The first reason: not losing a human's intent](#the-first-reason-not-losing-a-humans-intent)
- [The second reason: narrowing the solution space for AI](#the-second-reason-narrowing-the-solution-space-for-ai)
- [What an intent is in the strict sense](#what-an-intent-is-in-the-strict-sense)
- [Two theses of IOP for AI development](#two-theses-of-iop-for-ai-development)
- [A grammar instead of an endless repository](#a-grammar-instead-of-an-endless-repository)
- [Aspects as quanta of work for AI](#aspects-as-quanta-of-work-for-ai)
- [Static and dynamic intents](#static-and-dynamic-intents)
- [A catalog of capabilities](#a-catalog-of-capabilities)
- [Stopping correctly instead of hallucinating](#stopping-correctly-instead-of-hallucinating)
- [The ReAct loop in IOP](#the-react-loop-in-iop)
- [A prompt is not a boundary](#a-prompt-is-not-a-boundary)
- [Why AOA is stronger than an external intent language](#why-aoa-is-stronger-than-an-external-intent-language)
- [The short formula](#the-short-formula)

---

## Where IOP comes from

Intent-Oriented Programming doesn't come from a wish to invent a new coding style. It has two reasons, and they reinforce each other.

The first reason is human. In large systems, intent gets lost quickly. A requirement was in a ticket, discussed in a meeting, partly made it into the documentation, partly stayed in the author's head, and turned into a chain of conditionals, calls, and helper methods in the code. Six months later the team sees the implementation but no longer sees which order it was supposed to hold.

The second reason is AI. An LLM is good at generating local code, but in an ordinary repository the solution space is nearly infinite. A model can invent a helper, bypass DI, call the database directly, mix transport with business logic, or make up an API that doesn't exist. The problem isn't unique to AI: a human adapting to an unfamiliar project does the same thing, just more slowly.

IOP answers both reasons the same way: an intent must be expressed in code as a checkable invariant. Then a human can read it, a machine can check it, and AI can use it.

---

## The first reason: not losing a human's intent

If an intent isn't expressed in code, it can't be trusted as an architectural fact. It might be good documentation, a useful agreement, or a precise statement in a ticket, but the system can't hold onto it.

If a rule can't be checked, it isn't an invariant. If an invariant isn't expressed in code, it stays a convention that can be broken by accident or by not knowing about it.

Example:

```text
A convention:
  "CreateOrderAction must only be reachable by the customer."

An IOP intent:
  @check_roles(CustomerRole)
```

In the first case, the knowledge lives next to the code. In the second, it lives inside the code, in a form the runtime can check.

The same applies not only to business rules but to structure:

- an operation must have a domain;
- an operation must have an exit point;
- an aspect must declare what it puts into `state`;
- a compensator must reference an existing step;
- the dependency graph must have no cycles;
- access to the environment must be declared through `@context_requires`.

It becomes easier for a human to read the system, because the structure of intents is visible directly in the code. But that also makes the system clearer for AI: if a human sees the meaning without reconstructing it from the implementation, the LLM also gets a narrower, clearer task.

---

## The second reason: narrowing the solution space for AI

AI generation breaks down where there are no boundaries. If the space of admissible solutions isn't limited by anything, a model can pick any syntactically possible path. Some paths will work but violate the architecture.

IOP narrows the solution space. It says: not any code is admissible, even if it compiles. Only code that expresses intents in the system's grammar and passes invariant checks is admissible.

This matters for people too. A new developer on an ordinary project also has to guess where to write code, where to go for data, which helper methods are okay to use and which aren't, which rules are mandatory and which are just historical. In IOP, part of this guesswork stops being guesswork:

- a business scenario is written as an `Action`;
- the outside world is reached through a `Resource`;
- intermediate data passes through a checkable `state`;
- access is declared through roles;
- context is declared through `@context_requires`;
- recovery is declared through `@compensate` and `@on_error`;
- scenarios are checked through TestBench and WST.

The grammar doesn't make the system poorer. It removes meaningless options.

---

## What an intent is in the strict sense

This article uses the definition from [IOP: Intents and Invariants](iop-foundations.md):

> **An intent is a checkable invariant of behavior or structure, expressed in code, carrying knowledge of the system's capabilities and constraints.**

This definition is deliberately strict.

The phrase "create an order" is not yet an intent in the strict IOP sense. It might be a business goal. It becomes an intent once it gets boundaries:

- which `Params` are needed;
- which `Result` must be returned;
- which roles have access;
- which domain the operation belongs to;
- which steps are executed;
- which fields each step guarantees in `state`;
- which external ports are allowed;
- how the operation rolls back or handles an error;
- which test scenarios check its behavior.

Boundaries give meaning. Without boundaries, an intent is noise: it can't be checked, can't be reliably handed to another person, and can't be safely handed to AI.

---

## Two theses of IOP for AI development

Two theses follow from the definition of intent, and Intent-Oriented AI Development is built on them.

The first thesis:

> **An intent exists only where there is a checkable boundary.**

The boundary can be static or dynamic: a suffix, a mandatory `@summary_aspect`, `@check_roles`, `@result_*`, a lifecycle transition, `@context_requires`, a TestBench scenario. Without a boundary, AI sees not an intent but a code fragment or a text wish.

The second thesis:

> **A network of checkable intents forms a grammar that narrows the solution space.**

This is exactly what reduces hallucinations. The LLM no longer chooses from an infinite set of options. It works inside a language: what can be expressed, how it can be connected, where checks are needed, when it needs to stop and request a new port.

---

## A grammar instead of an endless repository

In an ordinary project, the repository looks like open space to AI. There are files, classes, functions, tests, configs, but often no machine-readable answer to questions like:

- where does the business scenario live;
- which external effects are allowed;
- which data must pass between steps;
- where does the domain end;
- what can be called directly, and what can't;
- which absence of a capability counts as an architectural fact.

AOA turns this into a grammar:

| Question | AOA's answer |
|--------|-------------|
| Where does the business scenario live? | `Action` |
| Where does the outside world live? | `Resource` |
| What does the operation accept? | `Params` |
| What does the operation return? | `Result` |
| How is the scenario structured? | aspects, top to bottom |
| What does a step promise the next one? | `@result_*` |
| Who can call the operation? | `@check_roles` |
| What's needed from the context? | `@context_requires` |
| How do you recover after a failure? | `@compensate` / `@on_error` |
| How do you check the scenario? | TestBench / WST |

For a human this is architectural discipline. For AI it's a language of admissible decisions.

---

## Aspects as quanta of work for AI

The pipeline of aspects isn't just for the runtime. It exists because a large intent is hard to generate and check as a single monolith.

An `Action` is a composite executable intent. An aspect is a quantum of work inside it: a bounded step that receives an input `state` snapshot, performs an action, and returns a new checkable snapshot.

If AI writes one large method, the error gets smeared across it. If AI writes a pipeline of aspects, the task is broken into manageable quanta:

- one aspect is one local intent;
- `@result_*` sets the boundary of the result;
- TestBench can check the whole scenario or a single step in a substituted world;
- an error is localized to a specific aspect's output.

One clarification matters: an aspect without a boundary isn't yet a full intent. It becomes an intent in the strict sense when its result or behavior can be checked — through checkers, runtime contracts, and tests with a substituted world.

This way AI gets not the task "write all of `CreateOrderAction`," but the task of assembling a meaningful sentence out of checkable words.

---

## Static and dynamic intents

Intents are checked at different moments.

Static invariants are checked when a class is defined, when the graph is built, at build time, or in CI:

- the `Action`, `Entity`, `_aspect`, `_summary` suffixes;
- the presence of `@summary_aspect`;
- the presence of `@check_roles`;
- domain binding;
- the correctness of a compensator reference;
- the acyclicity of dependencies;
- the validity of the lifecycle graph.

These intents give AI fast feedback: the code doesn't even get past this point before business execution.

Dynamic invariants are checked at runtime:

- `@result_*` on an aspect's output;
- the current user's role;
- access to a declared slice of Context;
- fulfillment of the include contract;
- the actual rollback;
- the operation's behavior in a specific world.

Dynamic intents are just as valid, but for AI they need tests. Without TestBench/WST, a model can write code that's structurally correct but semantically wrong. Tests turn the runtime check into a manageable feedback loop.

---

## A catalog of capabilities

An AI agent doesn't need the whole repository handed to it as chaotic text. It needs a map of the available capabilities.

The catalog of capabilities consists of:

- `Action`s as business capabilities;
- `Resource`s as ports to the outside world;
- `Entity` and `Lifecycle` as the domain model;
- `Params`, `Result`, and `state` as data contracts;
- roles, domains, dependencies, compensators, and error handlers;
- TestBench scenarios that describe checkable realities.

Technically the source of the catalog is the graph coordinator. But AI needs a compact projection: JSON, an intent schema, an MCP resource, or another format that states what exists, what it accepts, what it returns, which roles are needed, which ports are allowed, and which invariants are checked.

This is the key practical conclusion: don't ask an LLM to "study the whole project." Give it the grammar and the catalog of admissible intents.

---

## Stopping correctly instead of hallucinating

In an ordinary project, a gap in knowledge often turns into invention. The model didn't find the right service and wrote a workaround. Didn't find a resource method and made a direct SQL query. Didn't understand how to call payment, and invented `PaymentClient.charge()`.

In IOP, the correct behavior is different:

> "There's no `Resource` in the catalog that can check a customer's credit limit. A new port needs to be added, or an existing one pointed to."

This isn't an AI agent's failure. It's an architecturally correct stop. The absence of a capability becomes a fact, not a reason to hallucinate.

This is exactly where the grammar matters more than the prompt: AI shouldn't guess at a missing capability, but should detect its absence as a violation of the catalog's completeness.

---

## The ReAct loop in IOP

IOP naturally fits the ReAct loop, because every phase gets a structured foothold.

| Phase | What the AI agent does |
|------|---------------------|
| Reason | reads the task, the IOP grammar, and the catalog of available intents |
| Act | writes or changes an `Action`, a `Resource`, tests, and contracts |
| Observe | runs graph validation, runtime contracts, TestBench/WST, linters, and tests |
| Reflect | interprets an error as an invariant violation or a missing capability |
| Repeat | fixes the code or formulates a request for a new port / new intent |

In ordinary code generation, an error often sounds like "something isn't working." In IOP an error should sound structural: no role, no domain, no summary, `@result_*` not fulfilled, a broken include contract, a missing compensator, a violated domain boundary, no allowed `Resource`.

This kind of feedback is understandable to both a human and AI.

---

## A prompt is not a boundary

A phrase in a prompt like "don't call the network directly" is useful, but on its own it isn't an architectural guarantee. The model can get it wrong, and code with `requests.get(...)` inside an aspect stays valid Python.

For a boundary to become real, you need a checkable detector:

- a static AST check of aspect bodies: forbidding imports and calls to IO modules outside an allowlist;
- a sandbox where an aspect's body physically has no access to the network or the file system;
- a CI invariant for domain boundaries: an `Action` in one domain doesn't call a `Resource` in a different domain directly;
- graph validation that sees declared dependencies and forbids cycles or unauthorized links.

A prompt makes a request. An invariant makes the rule part of the system.

This is a direct continuation of the definition: an intent that can't be checked stays a description of an intent. An intent that is checked becomes an architectural fact.

---

## Why AOA is stronger than an external intent language

An external intent language solves the problem of expressing intent: a human writes a clear description, an LLM turns it into code.

AOA solves a harder problem: how to keep the intent from drifting apart from the implementation.

If intent lives separately, the link can break right after generation. The description says "issue a token," and the implementation returns the token without `opaque=True`, logs the secret, or bypasses a needed check.

In AOA, the equivalent intent looks like part of the executable structure:

```python
@regular_aspect("Issue token")
@result_string("token", opaque=True, required=True)
async def issue_token_aspect(...):
    ...
```

This isn't documentation or a hint to a generator. It's a checkable promise. If the aspect didn't return `token`, returned something other than a string, or exposed a sensitive field through the observability layer, the system gets a concrete point of violation.

That's why AOA is closer not to a code templating engine, but to a typed system for intents.

---

## The short formula

Intent-Oriented AI Development rests on two pillars.

The first:

> **For a human, IOP keeps the intent in the code: if a rule isn't expressed and isn't checked, it stays a convention.**

The second:

> **For AI, IOP narrows the solution space: the model doesn't work in an endless repository, but inside a grammar of checkable intents.**

The final formula:

> **AI shouldn't guess the architecture. It should move along a checkable map of intents.**

This map doesn't come from documentation layered on top of the code — it comes from the code itself: from invariants of behavior and structure that the system can read, check, and connect into a grammar.

---

<table width="100%"><tr>
  <td align="left"><a href="iop-foundations.md">IOP: Intents and Invariants</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
