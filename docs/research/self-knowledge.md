<!-- translated-from: self-knowledge_draft.md @ 2026-06-17T15:32:25Z · sha256:2da8f59f8e68 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# What the system knows about itself

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

The [formal model](../reference/formal-model.md) outlined the abstract questions. This note is about their applied side: since structure, contracts, and effects are **declared**, the system can analyze **itself** and point out things it was never asked about — gaps, risks, and places where a change suggests itself. None of this requires running a single business operation: everything is read from the graph the machine builds at startup.

In ordinary code there are no such questions — not because no one cares to ask, but because there is nothing to ask of: "where is a compensator missing", "which role opens nothing", "where will a failure flow to" are questions about intent, and in ordinary code intent is not recorded. Here it is recorded, so this is not the grammar of text but predicates over an object faithful to what executes.

The note is a map of such detections, with an honest status mark on each: what is computable from the graph today, what is a heuristic, what needs one more declaration, and what is still the frontier. Example for this note: [01_self_audit.py](../../examples/research_self_knowledge/01_self_audit.py).

---

## First — what already works

Two detections are read from the graph right now, with no operations run. The example [01_self_audit.py](../../examples/research_self_knowledge/01_self_audit.py) builds a small domain with deliberate flaws and finds them:

```text
Self-audit of the declared graph (no business call executed):

Dead roles — declared, but required by no operation:
  ⚠ AuditorRole

Rollback gaps — regular (state-changing) steps without a compensator:
  ⚠ ShipAction     regular=1 compensate=0
Has a declared rollback:
  ✓ ChargeAction   regular=1 compensate=1
```

`AuditorRole` is declared, but no operation requires it (there is no incoming `@check_roles` edge) — it is a permission that opens nothing. `ShipAction` has a regular step but not a single [compensator](../tutorials/step-04-saga-and-compensations.md) — on the failure of a later step there is no rollback. Exactly the questions you kept in your head, posed to the graph as an edge traversal.

## Gaps — what is missing

- **An unclosed rollback.** An operation with regular (state-changing) steps but no [`@compensate`](../tutorials/step-04-saga-and-compensations.md). *Computable today* via the pairing of `@regular_aspect`/`@compensate` edges; the *heuristic* part is that a purely computational step needs no compensator — the signal strengthens if the step works with a transactional [`@connection`](../tutorials/step-06-dependencies.md).
- **An unhandled failure.** An operation depending on an external (failure-prone) resource but with no [`@on_error`](../tutorials/step-05-error-handling.md): the failure escapes upward raw. *Close* — one declaration is needed: marking a resource as "unreliable" (the graph knows the dependency, but not its unreliability).
- **A dead role and an unreachable operation.** A [role](../tutorials/step-03-authorization-and-roles.md) required by no operation; an operation unreachable for any role; an entity created by no operation. *Computable today* through graph reachability.
- **A lifecycle dead end.** A non-final [`Lifecycle`](../tutorials/step-22-lifecycle.md) state with no outgoing transitions; an unreachable state; a **dead transition** — one no operation performs. The automaton's structure is already checked by the graph at build time; *close* — matching transitions against which of them are actually driven by operations.
- **A non-completable process.** A role can **start** a multi-step lifecycle (drive the initial transition) but has no access to the operation needed for a later mandatory transition — the process gets stuck specifically for it. *Close* — intersecting the use-case graph (role → operations) with the automaton's transitions.
- **A hole in the state contract.** A late step reads `state["x"]` that no postcondition further up the pipeline guarantees — a guaranteed runtime failure. *A frontier for today*: state reads are not yet declared (they are in the aspect body), so this requires either inference from checkers or a declaration of the keys read — a tempting but not yet closed task.

## Risks — where it will break

- **A load-bearing and fragile node.** A resource with high fan-in (many depend on it) that is also external, while the dependent operations have no `@on_error` — a single point of failure with a wide blast radius. *Computable* (fan-in/centrality) today; ranking by "fragility" is *close*.
- **A correlated compensation failure.** A compensator depends on the **same** resource whose failure triggers the rollback: when compensation is needed most, the compensation tool is also unavailable. *Computable* by intersecting the dependencies of the compensator and the failed step.
- **A write race.** Two operations write the same field of an [entity](../tutorials/step-21-relations.md) without a shared transaction — a risk of inconsistency. *Close* — you need to know that the operation actually writes this field (the direction of the effect).
- **Escalation through nesting.** A `box.run` to an operation whose [`@check_roles`](../tutorials/step-03-authorization-and-roles.md) requirements are softer than the parent's (a path to a less restricted operation) or stricter (a nested call will reject what the parent accepted — a broken flow). *Computable* by comparing role requirements along `box.run` edges.
- **A deep chain.** A long path along `@depends` or a deep pipeline — amplified latency and failures. *Computable* (the longest path in the DAG).
- **Rollback incompatibility.** A saga or transaction over a resource whose `check_rollup_support` is false where a rollback is needed — an integrity flaw. *Computable* once transactional boundaries are marked.

## Hints — what to add or change

- **Where a cache suggests itself.** An operation that only reads (does not write connections), is deterministic in `Params`, and is called often — a candidate for [`cache_key`](../tutorials/step-08-cache.md). *Close* (it needs the direction of the effect and the call frequency).
- **What can be parallelized.** Independent regular steps or adjacent `box.run` calls with non-overlapping dependencies and no shared mutable connection — the pipeline is currently a strictly sequential fold, but the structure says where parallelism is safe.
- **A god-operation.** An operation with a number of dependencies/steps above a threshold, or spread across several domains — a candidate for splitting. *Computable* by node degree and domain edges.
- **Where to draw a resource boundary.** A recurring access pattern — a hint to extract a [`Resource`](../tutorials/step-19-resource.md).

## How this is not an ordinary code linter

An ordinary code linter looks for patterns in **text**: long functions, unused imports, suspicious casts. Here the analysis goes not by text but by **intent**: "the rollback is not declared", "the role opens nothing", "the process cannot be completed by this role". This is possible precisely because intent is declared — roles, checkers, dependencies, automaton transitions — and verified by the machine, while the [Maxitor](../tutorials/step-26-maxitor.md) graph matches what executes. A code linter does not know that `ShipAction` *should* be able to roll back; the graph knows that it *has no* compensator and that it changes state.

## Invariant density

Behind all the detections above stands a single principle — and it is also the quantitative facet of the second pillar of [IOP](../explanation/philosophy.md) (*Intent Enforced*): a declared intent becomes a **verifiable invariant**. The set of intents is not closed; the larger the share of significant decisions the system expresses explicitly and hands over to the machine to check, the fewer hidden agreements remain. This can be measured. Let us call it **invariant density**: what fraction of the significant relationships in the system is fixed by verified declarations, and what fraction is left to convention and memory.

Density is not a metaphor but a quantity over a [formal object](../reference/formal-model.md): for each node and region of the graph you can count how many verified constraints hold it together — roles, checkers, declared dependencies, context slices, automaton transitions, entity relations. A low-density region is a "loose" spot: there are more degrees of freedom, more states are representable that are syntactically valid but wrong in meaning — and there the system can help with nothing, it has nothing to check.

Hence cohesion. Every shared invariant is a **verified agreement** between parts, not a silent assumption: if two operations are linked by a contract, a lifecycle, or an entity relation, the machine maintains that correspondence. It is important not to confuse this with harmful code coupling (tangled dependencies): invariant density precisely **replaces implicit connectedness with explicit and verified connectedness** — a hidden assumption that breaks silently becomes a declared rule that breaks loudly and at startup. The higher the density, the narrower the space of representable erroneous states; this is "make illegal states unrepresentable" lifted from the level of types inside a function to the level of the whole architecture — and, crucially, **measurable**.

The open questions here are concrete: does a density measure exist that predicts the defect rate on real projects; can the "size" of the erroneous-state space be computed and observed to shrink with each added invariant; where is the optimum — the point past which the next invariant costs more than it saves. There are no answers yet — but these are questions about a quantity over an object, not about taste.

## The boundary

Two honest caveats. First: **a detection is not a verdict.** A flagged "gap" may be intentional (a role reserved for the future; a step that is idempotent and needs no compensator). The object **suggests**, the engineer decides — so this is an advisor, not a ban. Second: some detections run up against the fact that the **direction of an effect** (does the step read a resource or write it) and a resource's **reliability** are not yet declared — they live in the aspect body. This is exactly where the nearest frontier of the research runs: what minimum of extra declarations turns a heuristic into a theorem without turning the contract declaration into bureaucracy.

The point of this note is to show the applied face of the [formal object](../reference/formal-model.md): a system able to point at its own flaws and risks before they surface in production, because its makeup is data, not a guess. This is part of the [open program](../index.md#open-research), not a finished tool.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
