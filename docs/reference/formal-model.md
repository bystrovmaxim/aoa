<!-- translated-from: formal-model_draft.md @ 2026-06-17T15:35:35Z · sha256:cea33f82cd1a -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# The formal model: open questions

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

---

This is not a description of a ready feature and not a list of features. It is an attempt to outline **which questions about the system become correctly posed** when the system itself is a formal object, not text. Most of them have no answer yet. The value here is not in the answers but in the fact that the questions can be posed at all — and, in principle, handed to a machine.

A word about the claims, right away. **AOA introduces no new mathematics.** Hoare logic and contracts, acyclic graphs and topological order, finite automata, ports-and-adapters — all of this has been known for decades. The single shift: the architecture here does not stay an implicit structure in heads and comments but is **raised to an object** — a typed graph with operational semantics and verifiable invariants. An object can be studied. Text cannot.

A prose exposition of the ideas is in [Philosophy](../explanation/philosophy.md); the list of the active checks is in [Intents and invariants](intents-and-invariants.md).

- [The object of study](#the-object-of-study)
- [What ordinary code lacks](#what-ordinary-code-lacks)
- [Strength and load](#strength-and-load)
- [Proof instead of checking by examples](#proof-instead-of-checking-by-examples)
- [Identity, synthesis, algebra](#identity-synthesis-algebra)
- [Intent versus the observed](#intent-versus-the-observed)
- [What is computable today, and what is frontier](#what-is-computable-today-and-what-is-frontier)

---

## The object of study

An operation `A` is a tuple

```
A = ⟨ P, R, (a₁, …, aₙ), s, K, D, χ ⟩
```

where `P`, `R` are the immutable input and output spaces; `(a₁, …, aₙ)` are the regular aspects in total order by source position; `s` is the single summary aspect; `Kᵢ` is a step's declared context slice (`@context_requires`); `D` is the declared dependencies (`@depends`); `χᵢ` is a step's postcondition from checkers (`@result_*`). A run is a linear fold without branches:

```
run(ctx, A, p) = s ∘ aₙ ∘ … ∘ a₁ ,   σ₀ = ∅,   a transition is allowed only if σᵢ ∈ χᵢ
```

The whole system is a **typed graph** `G` of such objects: nodes (`Action`, aspects, `Resource`, `Entity`, `Role`, `Lifecycle`, contract fields) and typed edges (`@depends`, `@check_roles`, entity relations, automaton transitions, `params`/`result`). The important property: **every node and every edge is declared and checked by the machine** — the graph is not reconstructed from code by a heuristic and is not an approximation, it coincides with what is executed. This is exactly what makes `G` fit for calculation: there is no "maybe" on it.

## What ordinary code lacks

To see the shift, it helps to name what ordinary code lacks in principle.

- **Structure is implicit.** The call graph is recovered by analysis, and in the general case this is undecidable: dynamic dispatch, reflection, name-strings. The question "what depends on what" has no exact answer without execution.
- **Effects are not declared.** What a function reads from the environment, what it writes, which resources it touches — is not known until its whole transitive code is read. So "information flow" or "blast radius" are not questions but archaeology.
- **Contracts are not written down.** Pre- and postconditions live in heads and tests. There is nothing to prove a property of the whole system on — one can only check individual examples.

Hence the practice: a system is **tested, profiled, reviewed** — that is, its behavior is observed — but not **calculated**, because there is nothing to calculate on. AOA changes exactly the substrate: the structure is declared (nothing to reconstruct), the effects are declared (the context slice, the dependencies, `params`/`result`), the contracts are declared (roles as preconditions, checkers as postconditions, lifecycle automata) — and all of it is checked. The object is complete enough to **pose** questions about the system as a whole. Below — which ones.

## Strength and load

Engineering strength-of-materials lets you compute a structure before building it: where stress concentrates, what load a node holds, where the margin is exhausted. Carrying this discipline over to software always ran into the absence of the structure as an object. Here the object exists — and the questions become meaningful.

- **The load field.** Can one define a "load" that propagates along the `@depends` graph, like a force through a truss, assign resources a throughput, and **compute the yield point** — where the system saturates — *before* a load test? The seed: the absence of branches in the fold makes propagation unambiguous, and the graph sets the paths; this is a queueing network on top of the architecture. Open: which capacity model is correct and how to solve it. In ordinary code the propagation path itself is undefined.
- **Concentration and load-bearing nodes.** Centrality by `@depends` is an analog of stress concentration: a resource that dozens of operations depend on is a load-bearing wall. The graph already gives this (it is drawn by [Maxitor](../index.md#vii-maxitor)). Open and empirical: does centrality predict real incident hotspots — and which measure of "stress" is the right one.
- **Failure propagation and minimal cut sets.** Resources fail; `@on_error` and `@compensate` set the recovery boundaries. From this a **fault tree** is automatically extracted. Can one compute the minimal cut sets — the smallest sets of failures that bring down a scenario — and availability from the declared structure? The seed: fault-tree analysis has long been applied in aviation; the novelty is that the structure is extracted, not drawn by hand and not stale.

## Proof instead of checking by examples

A test checks individual points of the input space. Contracts on the object let you ask about **all** of them at once.

- **The end-to-end contract of an operation and a system.** Each step is a Hoare triple `{χᵢ₋₁} aᵢ {χᵢ}`, the pipeline is a fold, and `box.run` glues contracts along the DAG. Can one compute the strongest postcondition of a whole tree of operations and thereby **prove a business invariant** ("an order is never shipped unpaid") across the whole system, rather than test it on examples? The seed: Hoare composition plus acyclicity; open — how rich the checker predicates must be and whether inference is decidable in practice.
- **Non-interference (information flow).** The context is a declared read slice, `@sensitive` marks fields, roles form an access lattice. Can one **prove non-interference** — that a high-sensitivity field never flows to an output with a low access level — by tracking the declared flows along the operation graph? The seed: declared reads, a declared output, and a role lattice are exactly the ingredients of an information-flow type system; open — how to carry the flow through state snapshots and nested calls. In ordinary code reads and writes are not declared, and flow tracking fights the whole language.

## Identity, synthesis, algebra

The farthest edge is where the presence of the object changes not the speed of the answer but the very class of questions.

- **Semantic diff and safe refactoring.** Can one define a refinement/equivalence relation on AOA systems such that "a refactoring preserves behavior" becomes a **theorem**, not a hope: the same "role → operation" reachability, the same lattice of postconditions, the same surface of effects? The seed: contracts and the graph give comparable quantities; the relation itself is not yet built. On text a diff is line-by-line, and the question "did the intent change" is not formally posed.
- **Synthesis of operations.** Operations are typed (`Params → Result`) and carry declared dependencies and contracts — this is a typed space of components. Can one, given a target postcondition and the available `Action`/`Resource`, **synthesize a scenario** that achieves it — program synthesis at the level of business operations? The seed: typed components with contracts are the classic setting for type-driven synthesis; open — the scale and depth of the semantics. A side consequence: an agent reasoning over this graph has a **correct** search space — it cannot propose an undeclared dependency, because it is not in the object (see [MCP](../tutorials/step-14-mcp.md)).
- **Process algebra.** State snapshots are objects, aspects are arrows, the fold is composition, lifecycles are automata. Is there a categorical or process-algebraic semantics in which business operations are reasoned about with **equations**: does "cancel, then refund" commute with "refund, then cancel"? The seed: the algebra is literally present here; open — to formalize it and obtain laws by which processes can be transformed like expressions.

## Intent versus the observed

Since every version of the system is a formal object, one more class of questions appears: about the correspondence of the intended and the happening.

- **Temporal verification of a process.** Lifecycles and operations together constrain the set of possible event sequences. Can one check temporal properties ("every reserved order is eventually shipped or cancelled") against the architecture, the way models are checked? The seed: `Lifecycle` is a finite automaton, already fit for model checking; open — to raise the check to the logic of the whole process, not one entity.
- **Correspondence of intent and logs.** The code sets the *intended* process; the [OCEL](../tutorials/step-09-plugins.md) log gives the *observed* one. Can one automatically find the **divergence** — where reality drifted from the declared model — given that both are now formal objects of the same kind? The seed: conformance checking exists in process mining; here the "code → specification" bridge is extracted itself, not modeled by hand.
- **The dynamics of evolution.** A system's history is a sequence of formal objects. Do nodes that are simultaneously **load-bearing and volatile** (high centrality × high change frequency) predict where the next failure or major refactoring will fall? The seed: graph snapshots over git history plus centrality and churn; open — the predictive model itself. In ordinary code there is no stable object to track through versions.

## What is computable today, and what is frontier

An honest boundary, so the questions do not look like promises.

| Level | What |
|-------|------|
| **Computable today** | centrality and load-bearing nodes, reachability and blast radius, the critical path, the access surface by roles, cycle and dead-operation detection — on the live graph `G` (part is drawn by Maxitor) |
| **Close range** | the fault tree and minimal cut sets, Hoare composition for proving invariants, typed information-flow analysis — the ingredients are in the object, a model and a tool are needed |
| **Frontier** | synthesis of operations, process-algebra equations, OCEL ↔ model correspondence, evolution prediction — open research tasks |

And a hard line not to blur: **absolute performance the object does not derive** — it is measured. The graph tells *where* to measure and what the structural ceiling is (the fold depth, the load-bearing nodes), but the millisecond numbers come from experiment, not topology. The same goes for the whole list: the object makes a question **correctly posed and, in principle, machine-checkable** — it does not make the answer free.

The meaning of this page is therefore not that AOA answers the listed — it does not. The meaning is that on ordinary code these are not even questions: there is nothing to ask "where will the system leak" or "did the refactoring preserve the meaning" of. Here there is something to ask of — because the system stopped being text and became an object faithful to what is executed. This is an open window, not a finished room.

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
