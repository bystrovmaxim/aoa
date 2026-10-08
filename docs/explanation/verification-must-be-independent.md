<!-- translated-from: verification-must-be-independent_draft.md @ 2026-10-08T15:24:09Z (filesystem mtime; draft is gitignored, no git history) · sha256:8b846dbffabe -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Verification must be independent

## Why generated code needs a contract the model did not write

<table width="100%"><tr>
  <td align="left"><a href="comparison.md">Comparison with other frameworks</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="../research/intent-oriented-ai-development.md">Intent-Oriented AI Development</a></td>
</tr></table>

---

## Contents

- [The thing that actually changed](#the-thing-that-actually-changed)
- [Phase 1 — the model writes code](#phase-1--the-model-writes-code)
- [Phase 2 — the model writes code from a specification](#phase-2--the-model-writes-code-from-a-specification)
- [Phase 3 — the model writes code inside an executable grammar](#phase-3--the-model-writes-code-inside-an-executable-grammar)
  - [What actually separates phase 2 from phase 3](#what-actually-separates-phase-2-from-phase-3)
- [Phase 4 — the variants, and how to tell a phase from an extension](#phase-4--the-variants-and-how-to-tell-a-phase-from-an-extension)
  - [The criteria a variant must pass](#the-criteria-a-variant-must-pass)
  - [Two axes, not one](#two-axes-not-one)
  - [What already exists](#what-already-exists)
  - [Variant A — contracts derived from facts](#variant-a--contracts-derived-from-facts)
  - [Variant B — synthesis over the graph](#variant-b--synthesis-over-the-graph)
  - [Variant C — the graph as the agent's environment](#variant-c--the-graph-as-the-agents-environment)
  - [Variant D — the graph as a protocol between systems](#variant-d--the-graph-as-a-protocol-between-systems)
  - [Variant E — a runtime that restores its own architecture](#variant-e--a-runtime-that-restores-its-own-architecture)
  - [Variant F — acceptance by proof](#variant-f--acceptance-by-proof)
  - [Order and dependencies](#order-and-dependencies)
  - [Four invariants that hold in every variant](#four-invariants-that-hold-in-every-variant)
  - [What would falsify the direction](#what-would-falsify-the-direction)
  - [Open questions](#open-questions)
- [The problem nobody automated](#the-problem-nobody-automated)
- [What "independent verification" means](#what-independent-verification-means)
  - [Independence is affordable only because it is deterministic](#independence-is-affordable-only-because-it-is-deterministic)
- [Why the architectural layer is the one that can be verified](#why-the-architectural-layer-is-the-one-that-can-be-verified)
- [What the gate actually catches](#what-the-gate-actually-catches)
- [The gap nobody asked about](#the-gap-nobody-asked-about)
- [The argument this answers](#the-argument-this-answers)
- [Acceptance by blueprint: Maxitor](#acceptance-by-blueprint-maxitor)
- [Human and machine in one loop](#human-and-machine-in-one-loop)
- [What would prove this wrong](#what-would-prove-this-wrong)
- [The short version](#the-short-version)

---

## The thing that actually changed

For the whole history of the discipline, writing code was expensive and reading code was cheap. Every practice we inherited is built on that ratio: code review, pull requests, diffs, style guides, "keep functions short", "a change should be readable in one sitting". All of them assume that a competent person can look at what changed and decide whether it is right.

That assumption is now false, and it is worth being exact about why. Reading did not become expensive per line: it works only because code is **structurally coherent**, so a reader almost never reads — the reader extrapolates from a sample. Generation breaks exactly that property. It produces code that is locally correct and globally incoherent, and incoherent code cannot be extrapolated from, however little of it there is. Coherent code a hundred thousand lines long reads more easily than spaghetti ten thousand lines long. The volume multiplies the consequence; the loss of coherence is the cause.

This is not a story about model capability. It is a story about **where the bottleneck moved**. Generation was automated; verification was not. Everything that follows in this document is a consequence of taking that sentence seriously.

---

## Phase 1 — the model writes code

**The practice.** The model is given a task in prose and returns code. The human reads it, runs it, pastes it, fixes it. Fast iterations, no ceremony, and a real gain in speed for small, well-scoped work.

**What it assumes.** That the human reading the output has the capacity to judge it. That assumption held while the output was a function or a file.

**Where it breaks.** At the scale of a repository. The model invents a helper because it does not know one exists. It reaches past the dependency-injection seam because nothing stopped it. It mixes transport concerns with business logic because the prompt did not forbid it and the compiler does not care. None of these are syntax errors, so nothing complains.

Phase 1 never disappeared. It retreated into places where being wrong is cheap: prototypes, scripts, notebooks, throwaway code. That is a sensible retirement, not a defeat.

---

## Phase 2 — the model writes code from a specification

**The practice.** The prose is structured first. A specification, a plan, a task list — reviewed before implementation, and then handed to the model. The repository you are reading uses exactly this: the Spec Kit flow of `/speckit-specify` → `/speckit-plan` → `/speckit-tasks`, with the resulting artifacts kept in the tree.

**What it assumes.** That a well-written text narrows the solution space enough for the model to land in the right place, and that a reviewer who reads the text can predict the code that will follow.

**What it genuinely fixes.** It fixes the loss of human intent — the requirement that lived in a ticket, was discussed in a meeting, partly reached the code, and partly stayed in the author's head. Now the intent is written down before implementation, and the human approves it while it is still cheap to change.

**Where it breaks.** The specification is text, and text cannot be checked by a machine. Nothing binds the implementation to the plan except the model's compliance and the reviewer's attention. The gap between "what the plan said" and "what the code does" is exactly as wide as it was before — it has simply moved one level up. A specification that has drifted from the code cannot complain, because it has no way to complain.

---

## Phase 3 — the model writes code inside an executable grammar

**The practice.** The admissible shape of the solution is not described in prose but declared in code, in a form the runtime itself enforces. A business operation is an `Action`: a class with typed input and output, a declared domain, a declared access rule, a linear pipeline of steps, declared dependencies, and declared postconditions for every step.

```python
@meta(description="Create order draft", domain=OrderDomain)
@check_roles(GuestRole)
class CreateDraftAction(BaseAction[CreateDraftParams, CreateDraftResult]):

    @regular_aspect("Normalise SKU")
    @result_string("sku", required=True, min_length=3)
    async def normalise_aspect(self, params, state, box, connections):
        return {"sku": params.raw_sku.strip().upper()}

    @summary_aspect("Build draft result")
    async def build_summary(self, params, state, box, connections):
        return CreateDraftResult(sku=state["sku"])
```

The important part is not the decorators. It is that these declarations are **not comments about the program**. They are read by the engine, compiled into a graph at startup, and — where they do not hold — the program stops. A declaration that nothing enforces is a convention, and a convention is what phase 2 already had.

**What it assumes.** That the architectural layer of a system can be stated completely enough to be checked, and that checking it is worth the cost of writing it down.

**Where it breaks.** It requires the grammar to actually cover the system. Everything below is an examination of that requirement, its limits, and its price.

### What actually separates phase 2 from phase 3

Phase 2 has **two participants**: the model that wrote, and the person who is supposed to check. Neither is fit for the job, and it is worth naming why separately. The model cannot check itself — a verifier drawn from the same process as the author shares its blind spots and its failure modes, which is why its "I checked it" is indistinguishable from its own mistake. The person is not careless; the volume is simply not theirs to carry. Verifying intent requires reading, reading does not scale with generation, and so the person cannot be the verifier of what is produced at this rate. Phase 2 is therefore not a weak form of verification — it is **the absence of verification, dressed as a process**: there is a review, but there is no verdict.

Phase 3 adds a **third participant**: one that did not write the code, does not form an opinion, and does not get tired. Two of its properties are the whole point. It is **independent** — drawn from outside the author's process, and therefore capable of the one thing a self-report cannot do: failing loudly. And it is **deterministic** — the verdict is reproducible, the same input giving the same answer without mood, context or fatigue. Determinism is what turns a check into something that can be **disputed**: "run it again" is a meaningful argument, unlike "this looks wrong to me".

---

## Phase 4 — the variants, and how to tell a phase from an extension

Phase 3 is where the repository stands. What follows it is open, and the honest position is that it should be argued rather than assumed: most of what gets called "phase 4" in conversation is an **extension of AOA wearing a phase's clothes**. This section is the whole map — the criteria, the six directions, the order, the invariants that hold across all of them, and what would falsify the direction.

Nothing here is implemented, and no variant has a prototype.

### The criteria a variant must pass

A phase is not "more of the previous one". A phase is a change in **what is authoritative** and **what the human does**. Phase 4 is therefore not "phase 3, faster, with better models" — these four rows have to move:

| | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| The human's role | writes code | approves text | declares the grammar, approves the blueprint |
| What the machine does | generates | generates from a plan | checks admissibility |
| The primary artifact | code | specification | graph |
| The failure class it treats | speed | intent loss | silent inadmissibility |

If a proposal does not move at least one of these rows, it is **an extension, not a phase**.

### Two axes, not one

The obvious way to get this wrong is to mix two different questions:

| Axis | The question | What lives there |
|---|---|---|
| **How systems are built** | What is authoritative, and what does the human do? | Phases 1–3, and any true phase 4 |
| **How systems connect, or run** | What do systems exchange, and what does the runtime decide? | Interoperability standards, runtime policy, self-repair |

Variants D and E live on the second axis. They are legitimate directions, but calling either of them phase 4 is a category error: they change neither the human's role nor the primary artifact. That is why they are marked **not a phase** below, and why they are still described — they matter, just not here.

### What already exists

Two variants depend on pieces that are already shipped:

| Piece | What it gives | Status |
|---|---|---|
| Plugin lifecycle events | Every run emits `GlobalStart`/`GlobalFinish` and per-aspect before/after events, each carrying `action_name`, `aspect_name`, `nest_level` | **shipped** |
| `box.info(Channel.business, ...)` | Business events routed through the machine's logger, not `print` | **shipped** |
| OCEL plugin (`aoa-ocel`) | An object-centric event log with typed events and objects | **shipped, separate package** |
| Graph nodes and edges for aspects, compensators, error handlers, checks, roles, dependencies | The structure every observation can be indexed against | **shipped** |
| Edges for the transitions a `Lifecycle` contains | State machines are in the graph | **shipped** |
| An edge for *which operation drives which transition* | — | **missing** — see Variant A |
| Declared state reads | — | **frontier** (see [self-knowledge.md](../research/self-knowledge.md)) |

The decisive property is the first row: **the events are already keyed by graph node.** This is not a stream of arbitrary logs that would have to be aligned with the architecture afterwards. It is evidence already addressed to an `Action`, to a named aspect, to a run at a nested level. That is what makes Variant A a different layer rather than a second source of truth.

### Variant A — contracts derived from facts

**In one line.** The graph knows what is *declared*; it has never known what *happened*. Phase 4 begins when execution evidence flows back into the declarations.

**Why it is a phase.** The human's role changes from **author** to **adjudicator**: declarations stop being written from a developer's understanding of the domain and start being proposed from production evidence and judged by a person. The new failure class is *declared but not true*: a checker that has never once rejected anything, an `@on_error` missing on the step that actually fails most, a declared role nobody holds, a `Lifecycle` transition that nothing ever drives.

**Why nothing breaks.** It is tempting to object that a second source of truth appears and the identity of graph and execution is lost. It does not, because the observations are **not a competing structure** — they are indexed by the existing one. An event carries `action_name`, `aspect_name`, `duration_ms`; an OCEL event carries objects and types. Evidence attaches to nodes and edges; it never claims to *be* structure. The graph stays authoritative and gains annotations. Here is what a plugin sees on one real run of an operation with one regular aspect, one summary aspect and one declared dependency:

```
GlobalStartEvent          action_name=CheckStockAction  nest_level=1
BeforeRegularAspectEvent  action_name=CheckStockAction  aspect_name=count_aspect
AfterRegularAspectEvent   action_name=CheckStockAction  aspect_name=count_aspect  duration_ms=0.012
BeforeSummaryAspectEvent  action_name=CheckStockAction  aspect_name=report_summary
AfterSummaryAspectEvent   action_name=CheckStockAction  aspect_name=report_summary  duration_ms=0.013
GlobalFinishEvent         action_name=CheckStockAction  duration_ms=0.205
```

Every row names a node. A signal aggregator can therefore count failures *per edge*, not per service.

**The first concrete step, and why it is exactly this one.** The graph has `Lifecycle` transition nodes (six states and eight transitions in the sample scope measured earlier) but **no edge saying which operation performs a transition**. So "a dead transition" cannot be computed from the graph today. It becomes visible from evidence the moment the binding exists: if an operation that must drive a transition runs and the transition never occurs, that is a fact from the log, not a hypothesis. Variant A's first task is therefore the missing edge — after which a family of detectors becomes computable, and each one is a candidate for its own declaration.

**What it deliberately is not.** It is not [Supervisor Actions](../research/supervisor-actions.md). That note builds the **operational** loop — observe, interpret, adapt within a policy allowlist — and it is explicit that its genome is untouchable: a Supervisor must not change contracts, aspect structure, roles or invariants. Variant A is the other half of that loop: the part that feeds evidence **back into development**, where a human adjudicates. The Supervisor regulates the running system; Variant A edits the genome under human approval. Without A, the supervisor's observations have nowhere to go except configuration; with A, they have somewhere to go that a person can review.

**Where it fails.** Inference needs volume: over ten runs a rate is noise, and on low-frequency operations the honest behaviour is to abstain rather than guess. Cascading false proposals would be worse than no proposals.

### Variant B — synthesis over the graph

**In one line.** The human states intent and constraints; the machine proposes **a change to the graph** as an object; a solver rejects the illegal; the person approves a blueprint.

**The analogy, and why it is more than decoration.** This is Stark and JARVIS, and the analogy carries the mechanics:

| JARVIS | The AOA counterpart |
|---|---|
| "Build me a suit that flies and takes a hit" | The human states **intent and constraints**, not declarations |
| JARVIS drafts candidates and discards the ones that will not fly | The machine proposes **nodes, edges and contracts**; the solver discards illegal graphs |
| "Sir, at this mass it will not fly — I need a lighter alloy" | The solver refuses and **asks for a missing declaration**, the port from IOP |
| Stark looks at the blueprint and says "yes" or "not that" | Maxitor: the human approves a **drawing**, not code |

The engineer does not disappear; the engineer stops being a **constructor** and becomes a **director**. That is precisely the row "the human's role" moving, which is why B is a phase and not an improvement.

**How it differs from A, and why the two must not be merged.** A is about **what exists**: it audits and sharpens declared things using facts. B is about **what does not exist yet**: it proposes new operations, new dependencies, a reshaped pipeline. A is audit; B is design. Merged into one story they produce a fog in which nobody can tell whether the system is being corrected or invented.

**The shape of a proposal** — a change-set over the graph rather than a diff over files: nodes to add or remove, edges to rewire, contracts to attach, and the constraints it claims to satisfy. It is a graph object, so it can be checked before anything is written; it is small, so a person can read it.

**Where it fails, and it fails precisely here.** JARVIS errs confidently: he will propose a suit that formally flies. A solver checks **admissibility, not meaning** — it cannot tell a legal but pointless architecture from the intended one. The person is therefore not optional in B; the person is the only carrier of intent. Direct consequence: **B without [Maxitor](../../packages/aoa-maxitor/README.md) is incomplete**, because the blueprint becomes the only acceptance interface. And a second trap: the temptation to let the machine modify the solver itself. That is leaving phase 3 for phase 1 under a better name.

### Variant C — the graph as the agent's environment

**In one line.** The agent works inside the graph, never reads a step body, and — the part that matters — **stops instead of working around a gap**.

**The mechanism.** Working in the graph, the agent has operations, contracts, roles, lifecycles and dependencies in view. While the graph is complete for its task, it works with confidence. The moment a declaration is missing, it has two behaviours available:

1. **Work around it** — invent a helper, bypass a seam, take the shortest path. This is phase 1 running inside phase 3, and it is what happens today.
2. **Ask for a port** — stop and say: to do this legally, declaration X has to exist.

The second behaviour is the shift. Development becomes a loop: *the agent hits a gap → the human declares a port → the agent continues inside the grammar*. The human's work turns from writing code into **opening ports**, which is exactly the role IOP calls "stopping correctly instead of hallucinating".

**Why this is the measurable one.** It hands over a test that can be run today rather than predicted: **if an agent can complete a task without reading step bodies, the graph is complete.** It cannot today — "a hole in the state contract" is marked a frontier in [self-knowledge.md](../research/self-knowledge.md), because state reads are not declared; they live inside the step. And it hands over a metric instead of an opinion: how many times per week the agent was forced to leave the grammar.

**Honest placement.** C is a consequence of A, not an independent phase: completeness of the graph is reached in part through evidence from execution. It earns its own subsection because it supplies the criterion and the metric, not because it needs its own mechanism.

### Variant D — the graph as a protocol between systems

**Not a phase.** No row of the criteria table moves: the human's role, the primary artifact, the machine's work and the failure class are all unchanged. This is a change in **how systems are stitched together** — an interoperability question, and a standards question at that.

Worth keeping on the map anyway, for one consequence adjacent to development: if a service publishes its graph as its contract — operations, types, roles, invariants, lifecycles — then integrating with it becomes a **static check** rather than an integration-test project. `machine.check_access_decide(...)` is already the shape of that question: "would this be allowed?" without running anything. But that changes the work only for teams **consuming** somebody else's contracts, not for teams developing. Hence: important, on the other axis, not a phase.

### Variant E — a runtime that restores its own architecture

**Not a phase, and worse: it is a regression against phase 3.** It does not change how the system is authored, and it attacks the central guarantee directly: if the structure may change while running, then "what executed" stops being "what was checked". Independent verification requires the verified object to hold still between the check and the execution.

A repaired version survives: self-repair is legitimate **inside a pre-verified set of alternatives** — a declared fallback resource, a declared alternative path, a declared escalation. Then it is not a phase; it is a well-designed phase 3 feature. The distinction is worth stating because the failure mode is attractive: "the system fixes itself" sounds like progress right up to the point where nobody can say what was verified.

### Variant F — acceptance by proof

**A phase, but exogenously driven.** The human's role changes substantially: nobody approves code; somebody maintains a **compliance artifact** — the graph, the check report, the blueprint. The failure class changes too: not "the system did something undeclared" but "you cannot prove it does what is declared".

It passes the criteria, and it is the only variant whose driver is institutional rather than technical: a regulator, an auditor, a customer with procurement rules. That is also why it cannot lead. It arrives after A and B have made the graph both complete and reviewable — or it does not arrive, because no institution accepts a graph as evidence until several organisations already do.

### Order and dependencies

| Variant | A shift in development? | What changes | When |
|---|---|---|---|
| **A.** Contracts from facts | **Yes** | The human **adjudicates** what evidence proposes; audit replaces authorship | First — needs no new mechanism (events and OCEL exist), no institution, and risks no guarantee |
| **B.** Synthesis over the graph | **Yes** | The human **directs**: intent instead of cells; design replaces filling | After A — it relies on a graph that A has made complete and checkable |
| **C.** The graph as the agent's environment | Yes, as a consequence of A | A new signal (**port request**) replaces working around gaps; completeness becomes measurable | Alongside and after A |
| **D.** The graph as a protocol | No — another axis | Interoperability; static integration checks | Independent of A and B |
| **E.** Self-restoring runtime | No — a runtime policy | Adaptive behaviour within pre-verified alternatives | A phase 3 feature, not a phase |
| **F.** Acceptance by proof | Yes, exogenously | The acceptance criterion moves from code to artifact | After A and B, on institutional demand |

**The formula, if one is useful:** *phase 3 — the human declares the grammar and the machine checks; phase 4 — production shows where the grammar is wrong, the machine proposes how to change it, and the human says "yes" or "not that".*

### Four invariants that hold in every variant

These are the reasons phase 3's guarantee survives its own successors:

1. **The genome is untouchable by the machine.** A Supervisor does not change contracts; a proposal is a proposal; only a human converts one into a declaration. (This is also [Supervisor Actions](../research/supervisor-actions.md)' own constraint — the nucleus decides, the genome does not move.)
2. **The verified object holds still.** No structure changes between check and execution. This is what rules out Variant E as a phase.
3. **Inference proposes, it does not dictate.** A derived contract is a candidate for review, never a silent edit to the graph. Otherwise the identity of graph and execution — the source of all of phase 3's force — is lost.
4. **Legal is not the same as meaningful.** A solver can reject an illegal graph; it cannot reject a pointless one. The human stays in the loop for exactly this reason, and no amount of solver strength removes the need.

### What would falsify the direction

**If coherence, not volume, turns out not to be the binding problem.** Then summarisation and better navigation tools would be the answer, and a grammar would be over-engineering: if a large volume of *coherent* generated code is the normal outcome, the case for a grammar weakens considerably.

**If the graph's coverage stalls.** The benefit is linear in the share of the system declared inside the grammar. A grammar covering the domain layer while boundaries, adapters and infrastructure stay ordinary code buys verification for a fraction of the system and creates a second place for truth to hide.

**If behavioural verification becomes cheap.** Refinement types, contracts on arbitrary code, verified synthesis — any of these would make the architectural gate no longer the only decidable layer, and the argument for checking shape instead of meaning weakens. This is the only one of the three that would be a change in what is possible rather than in how much is produced.

### Open questions

Per variant, the questions above stand: how much evidence earns a proposal the right to be shown; who owns a graph change; what is the review artifact when the artifact is a declaration; what the stable serialisation of a proposed change-set is; what "asking for a port" costs per occurrence before a team starts ignoring it. Four more belong to the direction as a whole:

**Sampling.** How much evidence is enough before a derived contract may be shown to a human — and does the answer differ per detector?

**Ownership.** A graph change touches roles, domains and dependencies at once. Whose approval is required, and how is that encoded rather than agreed verbally?

**Review at density.** A proposal that touches twenty operations is not reviewable as twenty diffs. What is the review unit for a graph change — the node, the domain, the path?

**The completeness threshold.** Variant C supplies the test ("can the agent work without step bodies?") but not the threshold: how complete must the graph be before agents may work unattended, and who decides that it is?

---

## The problem nobody automated

State it plainly:

> **We automated writing code. We did not automate deciding whether code is right.**

The consequences are not hypothetical, and they are not about model quality:

**Review stops scaling.** A diff of forty files is not reviewed; it is skimmed and approved. The practice of review was sized for the volume a human team produced, not for the volume a model produces.

**Reading does not survive volume.** There is a threshold beyond which nobody reads the artifact at all — they read its summary, or its tests, or its description. Beyond that threshold, "it was reviewed" is a statement about process, not about content.

**Tests cover behaviour, not shape.** A test suite can be green while the architecture is wrong: dependencies reached around their seams, one operation performing another's work, a step that mutates state it never declared. Tests check what someone thought to assert; they do not check what nobody thought about.

**The obvious shortcut does not work.** "Let the model review the model" fails for a reason that has nothing to do with how clever the model is: a process checking its own output shares the failure modes of the process that produced it. Whatever the generator is blind to, the reviewer is blind to as well. This is the same reason a compiler is not audited by the compiler.

**The decisions are taken again and again.** Not merely "the model invented a helper", but worse: it invented *six* ways to do the same thing in six places, because each time it decided afresh. Locally that is fine; globally it is six truths instead of one. This is the most expensive kind of debt, because the debt is not in the code — it is in the absence of a decision.

**Boundaries erode because nobody feels them.** A boundary is held in place by effort: one check, one reviewer, one linter. Breaking it costs nothing — the shortest path to a working result is what generation takes. So generation tilts the balance toward entropy: it does not violate boundaries on purpose, it simply cannot feel them.

**Locality is lost.** Human code grows around what changes together: to fix one thing you touch one place. Generated code lands wherever the prompt pointed. A month later a single logical change requires edits in ten unrelated modules — and that is not "bad code", it is the absence of any structure from which the location could be predicted.

**The vocabulary drifts.** The model reinvents terminology: `order`, `purchase`, `transaction` — three words for one thing. The reader can no longer trust names, and names are half of what makes reading cheap.

**Intent becomes unverifiable even if everything is read.** This is the limit of "it works, but it is spaghetti": across a large body of locally correct decisions there is **no signal** separating design from accumulation. The diffs show no drift, the tests are green, nothing is broken — and the system is no longer the one that was meant to be built. The classical instruments do not help here: code smells and refactoring catch what is *badly written*, not what is *incoherently assembled*. Generated code reads smoothly line by line, and that is what masks the problem.

Volume is therefore the last of these, not the first. Coherent output still meets the limit of human attention — beyond a threshold nobody accepts the system, however even it is — but that limit has its own answer: what gets accepted is the description, two orders of magnitude smaller than the code.

The sharpest way to see the whole problem is that a person reading code does **two different jobs**: checking **coherence** ("does this fit the way things are done here?") and checking **intent** ("is this what we wanted?"). Volume destroys only the second. Incoherence destroys the first — and with it the second, because there is nothing left to compare against.

---

## What "independent verification" means

Independence is a structural property, not a statement about capability or intelligence. Verification is independent when three conditions hold:

1. **A different kind of object is checked.** Not the artifact again, but a specification of it — one that is small enough to be stated completely and formal enough to be decided.
2. **It is executed by a different process.** A separate mechanism, run separately, with its own failure modes.
3. **It can fail loudly and specifically.** The verdict names what was violated, where, and which declaration the violator contradicted.

None of the three conditions mentions intelligence, and that is not an accident: a verifier earns trust structurally, not by being clever. This is why the verifier is a graph rather than a smarter model — and it is also where its boundaries lie.

**A deterministic verifier can compare, not discover.** It finds nothing that is absent from the model. "A step with no postcondition" is computable because the postcondition is a slot in the graph; "a step that does the wrong thing" is not computable at all. Hence the grading used throughout this project — *computable today*, *heuristic*, *needs one more declaration*, *frontier* — where the frontier is precisely what cannot be reduced to a slot.

**It costs a second artifact.** The declarations must now be kept in step with the code. That is cheaper than reading the code, but it is not free, and its characteristic failure is a **formal declaration with nothing behind it**: a checker that is always satisfied, a declared role nobody holds. Closing that hole is what phase 4's variant A is for — a deterministic verifier cannot close it by construction.

**A person does not disappear; a person changes what they read.** The volume stays with the machine, and the person receives a description two orders of magnitude smaller. It follows that **the graph must be readable by a person**, not merely traversable by a machine. A drawing nobody can understand has not solved the problem — it has moved it.

The last condition is what makes verification usable. "This looks wrong" is an opinion. "Step `normalise_aspect` declares postcondition `sku` with `min_length=3`; it returned a value failing that constraint" is a result.

Under these conditions, a model reviewing its own work fails condition 2 no matter how capable it becomes. A human reading the diff fails condition 1 and, increasingly, condition 3. A typed contract checked by a separate engine satisfies all three — and does so without requiring anyone to read the generated code at all.

This is why the phrase "the model will soon be smart enough not to need a grammar" describes the wrong problem. The grammar is not a crutch for a weak model. It is the only available form of independent verification when the volume of generated code exceeds human attention.

### Independence is affordable only because it is deterministic

Every other independent verifier — a person, an auditor, a second model — is either expensive, or non-deterministic, or both. A deterministic verifier is cheap per check and identical every time, which is the only reason independence can be had at the scale of every run rather than at the scale of a sample. There is no other form of cheap independence on offer here.

**And it forces the choice of object.** Independence requires that something *other than the artifact* be checked. But any other description of code is normally either as large as the code itself — and therefore useless — or incomplete, and therefore lying. The one object that is both **independent and small** is the **declared shape**: finite, enumerable, and small enough to be a graph. Phase 3 is therefore not "we verify code better". It is: **we narrowed what is verified down to what can be decided at all, and accepted explicitly that the rest is not.** The body of a step is an opaque node to the graph, and that is a **price paid on purpose** — not a defect.

**The inversion, stated exactly.** Verification used to check *everything*, inexactly and expensively. It now checks *little*, exactly and for free. The architectural work is the choice of what goes into that little.

---

## Why the architectural layer is the one that can be verified

Correctness of behaviour is undecidable in general. That is not a limitation of tooling; it is a property of the problem. No grammar, no engine, and no model will change it.

But there is one layer of a program that is **finite, declared, and therefore decidable**: its architecture. Which operations exist, what each declares as input and output, which steps compose it and in what order, what each step promises, what external things it may touch, who is allowed to call it, and what a failure rolls back.

AOA raises that layer to an object — a typed graph of nodes and edges, built from the declarations themselves:

```
Action          | CreateDraftAction
SummaryAspect   | CreateDraftAction:build_summary      {"description": "Build"}
RegularAspect   | CreateDraftAction:normalise_aspect  {"description": "Normalise"}
Checker         | CreateDraftAction:normalise_aspect:sku
                  {"TypeChecker": "String", "min_length": 2, "required": true}

@check_roles    Association  -> GuestRole
@regular_aspect Composition  -> CreateDraftAction:normalise_aspect
@result_checker Composition  -> CreateDraftAction:normalise_aspect:sku
domain          Aggregation, is_dag -> OrderDomain
```

Two properties make this object trustworthy rather than decorative:

**It cannot drift from the code, because it is not derived from the code — it is the same object.** A graph node holds the class it describes, and the engine takes a run's steps, dependencies, checkers, and role rules *from the node*. There is no second source of truth to fall out of sync, and no heuristic reconstruction of a call graph that may or may not be accurate. The graph is what executes.

**It is validated at construction.** Duplicate node identifiers, edges pointing at nothing, and cycles among ordering edges are rejected while the graph is built — before any business operation runs.

The readable consequence: a change that does not fit the declared structure fails immediately, not in production. In the appendix below, ten such cases are shown with their exact messages and the moment they fire.

---

## What the gate actually catches

Enforced declarations buy a specific class of guarantees. In the shipped environment, these fire with the messages shown (see [Appendix: the ten enforcements](#appendix-the-ten-enforcements) for the runnable reproduction):

| Violation | Result |
|---|---|
| Class-`Action` name without the `Action` suffix | `NamingSuffixError`, at class definition |
| An operation without `@meta` | `MissingMetaError` |
| An operation without `@check_roles` | `MissingCheckRolesError` |
| An operation without an exit point | `MissingSummaryAspectError` |
| A step whose value breaks its declared postcondition | `ValidationFieldError` — and the next step does not run |
| `box.resolve(...)` of a dependency that was never declared | `ValueError: Dependency ... not declared in @depends` |
| Duplicate graph node, or an edge to a missing node | `DuplicateNodeError` / `InvalidGraphError`, at graph build |
| A cycle among ordering edges | `InvalidGraphError`, at graph build |
| Declared access that no operation requires | reported by the self-audit |
| An operation that changes state and declares no rollback | reported by the self-audit |

The last two are worth separating from the first eight. They are not rejections — they are **gaps the graph can name without being asked about a specific operation**.

---

## The gap nobody asked about

This is where a declared model stops being a schema and starts behaving like a table of elements. From the structure alone, before any business operation runs, questions become computable that ordinary code cannot answer at all — not because nobody cares, but because in ordinary code intent is not recorded and there is nothing to ask.

The repository ships a runnable demonstration:

```bash
python examples/research_self_knowledge/01_self_audit.py
```

```
Self-audit of the declared graph (no business call executed):

Dead roles — declared, but required by no operation:
  ⚠ AuditorRole

Rollback gaps — regular (state-changing) steps without a compensator:
  ⚠ ShipAction     regular=1 compensate=0
Has a declared rollback:
  ✓ ChargeAction   regular=1 compensate=1
```

No business operation executed. `AuditorRole` is a permission that opens nothing. `ShipAction` changes state and has no way back if a later step fails.

The honest part is that each such detector has a status, and the project marks it: *computable today*, *heuristic*, *needs one more declaration*, *frontier*. An operation that depends on an unreliable external resource but handles no failure is close — it needs one declaration marking the resource unreliable, because the graph knows the dependency but not its reliability. A step reading a `state` key that no earlier postcondition guarantees is a frontier, because state reads are not declared yet; they live in the body of the step.

That list is the interesting object, not the demo. It shows how this kind of model grows: **not by a leap, but by one declaration at a time**. Each new declaration widens the grammar and adds a detector. A model that can state its own gaps is a model that has somewhere to go.

---

## The argument this answers

**The objection.** *If models become good enough, the grammar becomes unnecessary overhead. A capable model reads the whole repository and checks itself.*

**Why it fails.** It treats verification as a capability problem. It is an independence problem.

A model checking its own output is one process talking to itself, regardless of how capable that process is. Make it arbitrarily strong and it still shares its blind spots, its priors, and its failure modes with the thing it is checking. Capability changes how often it is wrong; it does not change the fact that the check and the artifact come from the same source. Independence is not a property you can train into a verifier — it is a property of the relationship between the verifier and the verified.

There are two supporting arguments, and the second is the one that bites.

**Attention does not scale with generation.** Whatever a model can check, the organisation is still accountable, and accountability requires that *someone* — a person, an auditor, a regulator, a successor engineer — be able to see what was accepted. If the code is too voluminous to read, the only thing left to accept is a description of it. Then the description must be smaller than the code, formal enough to check, and *not authored by the same process that authored the code*. A declared graph is precisely such a description.

**Self-review is not merely weaker; it is unfalsifiable.** When a model reviews its own work and reports "this is correct", that report cannot be distinguished from a report generated by the same failure mode that produced the error. An external contract can fail loudly. A self-report can only agree with itself.

The practical consequence: the more capable the generator becomes, the **more** valuable an independent contract is, not less — because capability increases the volume that must be accepted and decreases the human capacity to accept it. The grammar is not a phase we grow out of. It is the thing that makes further autonomy safe to grant.

---

## Acceptance by blueprint: Maxitor

A machine gate answers *"is this admissible?"*. It does not answer *"is this the system we meant to build?"* — and no engine can, because that question is about intent, and intent lives with people.

That is the second half of verification, and it is the reason [Maxitor](../../packages/aoa-maxitor/README.md) exists. Maxitor renders the same graph — the one the engine already built and already executes — as interactive diagrams in a browser. Not diagrams drawn by hand. Diagrams generated from the code that runs, so they cannot go stale and do not need to be maintained:

| View | What a reviewer sees |
|---|---|
| **Full graph** | Domains, operations, pipeline steps, compensators, error handlers, resources, dependencies |
| **ERD** | Entities, fields, relations, and cardinality by domain |
| **Use case** | Roles and the operations each role can reach, read from `@check_roles` |
| **Lifecycle** | The finite automaton of an entity: states, transitions, initial and final |

Three things follow, and they are why this belongs in a document about verification rather than in a product page.

**Different reviewers need different projections of one object.** An architect reads the full graph; an auditor reads the use-case view; a domain expert reads the lifecycle; a data owner reads the ERD. All four are looking at the same graph, which means four review conversations cannot produce four irreconcilable pictures of the system. In a hand-drawn world they routinely do — that is what a stale Confluence diagram is.

**The blueprint is independent of the generator for the same reason the gate is.** It is produced by a separate process reading the declarations, not by asking the model to describe what it did. A model's own summary of its work is testimony. A graph rendered from the code is evidence.

**Acceptance becomes reviewable at volume.** The code may be too large to read. The graph of the code is two orders of magnitude smaller and can be looked at. Reviewing the plan instead of the code is what phase 2 already tried, and it failed because the plan was prose with no binding to the result. Reviewing the graph is plan-review with the binding included: the picture is generated from the artifact that executes, so what is on screen is what will run.

The backend is itself an AOA application — a graph snapshot in DuckDB, exposed as Actions over an adapter, with the client a separate process. The endpoints (`/api/v1/full-graph`, `/api/v1/domain-use-case-diagram`, `/api/v1/lifecycle-finite-automaton`, and the rest) return JSON, so the same views can be embedded in a portal, a CI report, or a pull-request comment rather than only opened by hand.

---

## Human and machine in one loop

The two halves are not alternatives. They check different things, and both are needed.

| Layer | Question it answers | Who runs it |
|---|---|---|
| **Engine invariants** | Can this declaration exist at all? | The machine, at graph build and at run |
| **Self-audit** | What is declared but missing, dead, or unreachable? | The machine, on demand, before any run |
| **Maxitor blueprint** | Is this the system we meant to build? | People, per role, per view |
| **Tests** | Does this behaviour hold for these inputs? | The machine, on every change |

Read down that column and the division of labour is clean: **machines check admissibility, people check intent.** Neither can do the other's job, and the failure mode of both phases 1 and 2 was asking one to do both.

Maxitor closes the loop for people at the same moment the engine closes it for machines: the picture is generated from the graph, the graph is generated from the declarations, and the declarations are what executes. A reviewer who approves a blueprint has approved the structure of the real system — not a description of it, and not a promise about it.

---

## What would prove this wrong

A claim worth writing down is a claim worth falsifying. Three observations would weaken this position, and none of them are refuted by argument:

**If the bottleneck turns out not to be verification.** If code generation plateaus at a scale where human review remains adequate — because models settle at "assists a team" rather than "produces the volume of a team" — then the cost of the grammar buys less than it costs, and phases 1 and 2 are simply where the industry lives. This is an empirical question about volume, and it will be answered by practice, not by opinion.

**If the grammar's coverage stalls.** The benefit of a declared architecture is linear in the share of the system declared inside it. A grammar that covers the domain layer but leaves boundaries, adapters, and infrastructure as ordinary code provides verification for a fraction of the system and creates a second place for truth to hide. The test is whether a real application — not a sample — can be written end to end inside the grammar without an escape hatch becoming the normal path.

**If behavioural verification becomes cheap.** Should it become practical to decide properties of step bodies at scale — refinement types, contracts on arbitrary code, verified synthesis — then the architectural gate is no longer the only decidable layer, and the argument for checking shape instead of behaviour weakens. Note that this is the *only* one of the three that would be a genuine change in what is possible rather than in how much is produced.

And the honest limitation of the current implementation, stated plainly because a document that hides it is marketing: **the gate checks the shape of a system, not the meaning of its steps.** The body of an aspect is a single opaque node to the graph. A model can invent a helper, bypass a seam, or implement a step that is formally correct and semantically wrong, and the graph will not complain. What the graph guarantees is that the *architecture* of such a step cannot be quietly wrong: the dependencies it may reach, the state it must produce, the access it requires, and the rollback it owes are all declared, all checked, and all visible in the blueprint.

That is a bounded guarantee. It is also a guarantee nobody currently has by any other means at this scale.

---

## The short version

- Writing code was automated; **deciding whether code is right was not**. That is where the bottleneck moved, and every other conclusion follows from it.
- Phase 1 assumed a human could read the output. Phase 2 wrote the intent down as text and gained traceability, but text cannot be machine-checked, so nothing binds it to the result.
- Phase 3 declares the admissible shape in code, in a form the runtime enforces and a separate process can decide.
- Verification must be **independent**: a different kind of object, checked by a different process, failing loudly and specifically.
- The architectural layer is the one that is **decidable** — finite and declared — which is why a declared graph is where verification is possible rather than merely desired.
- A model checking itself fails independence no matter how capable it becomes. **The more capable the generator, the more valuable the independent contract**, because volume grows and attention does not.
- **Maxitor** closes the human half of the loop: the same graph, rendered as blueprints, so people can accept structure rather than read code — and can be sure the blueprint is current, because it is generated from what executes.
- The guarantee is bounded: **shape, not semantics**. The graph does not check what a step means. It checks that nothing about that step's architecture can be quietly wrong.

---

## Appendix: the ten enforcements

The two audit findings below are reproduced by `python examples/research_self_knowledge/01_self_audit.py`, run in the repository's own environment. The eight refusals were produced by running each violating declaration in its own process — several of them fail at class-definition time, which cannot be undone inside one interpreter — and each message is quoted exactly as the engine emitted it.

### Refusals at declaration, graph build, or run

| # | Violation | Message | Fires |
|---|---|---|---|
| 1 | Class name without the `Action` suffix | `NamingSuffixError: Class 'NoSuffix' inherits BaseAction but lacks the 'Action' suffix. Rename to 'NoSuffixAction'.` | at class definition |
| 2 | No `@meta` | `MissingMetaError: NoMetaAction has no usable @meta 'description' required for graph metadata resolution.` | at graph resolution |
| 3 | No `@check_roles` | `MissingCheckRolesError: NoRolesAction has no @check_roles declaration; '_role_info['spec']' is required.` | at graph resolution |
| 4 | No `@summary_aspect` | `MissingSummaryAspectError: Action interchange 'NoSummaryAction' has no summary_aspect edges; this helper requires a declared @summary_aspect.` | at run |
| 5 | Postcondition breached | `ValidationFieldError: Parameter 'y' must be greater than or equal to 10` | at the step boundary; the next step does not run |
| 6 | Undeclared dependency | `ValueError: Dependency SecretStorage not declared in @depends. Available: []` | at `box.resolve(...)` |
| 7 | Dangling edge | `InvalidGraphError: Edge 'probe_link' from 'probe.Source' references missing target_node_id 'probe.Nowhere'.` | at graph build |
| 8 | Cycle among ordering edges | `InvalidGraphError: Edges with is_dag=True form a directed cycle. Review interchange link wiring.` | at graph build |

Case 5 is the one worth reading twice. The violating step is not merely reported: the pipeline stops at its boundary, and the summary step behind it never runs. The example asserts this — it would report `!!! a later step ran anyway` if that step ever printed.

### Findings read from the graph, with no business call executed

| # | Finding | Output |
|---|---|---|
| 9 | Declared role that no operation requires | `⚠ AuditorRole` |
| 10 | State-changing step with no compensator | `⚠ ShipAction     regular=1 compensate=0` |

### Related reading

- [Intent-Oriented AI Development](../research/intent-oriented-ai-development.md) — the two reasons intents must be checkable, and the grammar that narrows the solution space.
- [What the system knows about itself](../research/self-knowledge.md) — the catalogue of graph detections, each marked with its honest status.
- [The formal model: open questions](../reference/formal-model.md) — an operation as a tuple, and which questions become well-posed.
- [The AOA Architectural Constitution](architectural-constitution.md) — the nine primitives and the algorithm for choosing between them.
- [Comparison with other frameworks](comparison.md) — where AOA sits next to FastAPI, Django, Clean/DDD, CQRS, and workflow engines.
- [Maxitor](../../packages/aoa-maxitor/README.md) — the blueprint view of the same graph.
