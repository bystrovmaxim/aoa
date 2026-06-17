<!-- translated-from: step-01-action-and-pipeline_draft.md @ 2026-06-17T17:53:37Z · sha256:c48e9f5907e0 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Step 01 — Action and the pipeline

<table width="100%"><tr>
  <td align="left"><a href="step-00-get-started.md">← Step 00 — Getting started</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-02-state-as-x-ray.md">Step 02 — State: the operation's x-ray →</a></td>
</tr></table>

- [Hello, world!](#hello-world)
- [Params, Result, and box](#params-result-and-box)
- [Multiple aspects](#multiple-aspects)
- [Inheritance](#inheritance)
- [Intents and runtime contracts](#intents-and-runtime-contracts)
- [Review questions](#review-questions)

---

Everything in AOA revolves around a single figure — the `Action`. It is a business operation cast as a class: one typed input (`Params`), one output (`Result`), and between them a straight chain of steps you read top to bottom, like a page. No branches, no side exits: open the class and you see the whole operation. The constraint is deliberate, and it is the whole point. A service method can only be understood by tracing where it calls and what it throws; an `Action` is built so its intent reads in place, without leaving the page.

This chapter introduces the `Action` up close: what it is made of, how the pipeline enforces linear execution, and — what sets AOA apart from familiar approaches — which of the declared rules the machine checks before the very first run. Each section maps to a file in `examples/step_01_Action_and_pipeline/`; keep it open alongside.

The code assumes fluency in Python: decorators, `async`/`await`, and [Pydantic](https://docs.pydantic.dev/) are used as given, without preamble.

---

## Hello, world!

[▶ Try in Colab](https://drive.google.com/file/d/1hHNELkgJY2Wo5HYp_480xlPDTkfOf0R3/view?usp=drive_link) · [Open in project](../../examples/step_01_Action_and_pipeline/01_hello_world.py)

Let's start with an operation that does nothing useful — it prints a line and returns an empty stub. Its value is elsewhere: it shows the minimum of declarations AOA requires before it will run anything at all.

```python
class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greetings domain"


@meta(description="Say hello to the world", domain=GreetingDomain)
@check_roles(NoneRole)
class SayHelloAction(BaseAction[ParamsStub, ResultStub]):

    @summary_aspect("Print greeting and return stub")
    async def output_summary(self, params, state, box, connections):
        print("Hello, world!")
        return ResultStub()
```

That is a fair number of lines for a plain greeting. But none of them is a ritual: each declares something without which an operation in AOA is not considered complete.

It all begins with a **domain**. An operation must belong to one — the domain defines a logical area ("orders", "payments", "greetings") and serves as the anchor for the system graph, the access matrix, and the visualization. A domain class name must end with `Domain`; write `class Greeting(BaseDomain)` and you get a `NamingSuffixError` right at class declaration, at import time. That is the first of the rules AOA guards itself.

Next come two required decorators. **`@meta`** is the operation's passport: its `description` is not a note for a colleague but part of the system contract, and it lands in the OpenAPI schema, the MCP tool description, and the operation graph; `domain` ties the operation to its area. **`@check_roles(NoneRole)`** declares access. Here AOA takes a principled stance: access must be declared explicitly, and silence does not count as a decorator. `NoneRole` is "this operation is open to everyone" said out loud — a conscious decision, not a forgotten check. Skip `@check_roles` entirely and the machine refuses to run the operation.

The class itself inherits `BaseAction[ParamsStub, ResultStub]`; in the brackets are the input and output types, stubs for now. The name must end with `Action`. And finally **`@summary_aspect`** — the single exit point: exactly one such method per operation, and it is the one that assembles and returns the `Result`. Without it — `MissingSummaryAspectError` at startup. The method has a fixed signature: `params`, `state`, `box`, `connections` are passed by the machine itself — respectively the input, the shared pipeline state (the whole next chapter is about it), the structured logger, and the open resources. `print` is here for the moment; the operations' proper output is `box`, and it is one step away.

The machine runs the operation:

```python
machine = ActionProductMachine()
await machine.run(Context(), SayHelloAction(), ParamsStub())
```

`ActionProductMachine` reads the declarations and leads the operation through the pipeline. `Context()` is the call environment: empty for now, but later it will hold the user, their roles, the request id. An empty object is mandatory — the machine will not accept `None`. `ParamsStub()` is an instance of the declared input.

**Run:**

```
uv run python examples/step_01_Action_and_pipeline/01_hello_world.py
```

**Output:**

```
Hello, world!
```

The takeaway is worth stating plainly. Even an empty operation already carries a passport, an access declaration, and an exit point — and all of it is checked before it ever runs. Explicitness here is not a style but an invariant: the composition of an operation is visible from the class and guaranteed by the machine.

---

## Params, Result, and box

[▶ Try in Colab](https://drive.google.com/file/d/1g7TxGauYe-lIoXk2d9A4-CpU5J9D9kr1/view?usp=drive_link) · [Open in project](../../examples/step_01_Action_and_pipeline/02_params_result_and_box.py)

Stubs are fine for introductions; a real operation works with data. Let's give it an input and an output — and at the same time swap `print` for the instrument operations in AOA use to speak with the outside world.

```python
class GreetParams(BaseParams):
    name: str = Field(description="Name of the person to greet")


class GreetResult(BaseResult):
    message: str = Field(description="Assembled greeting message")


@meta(description="Greet a person by name", domain=GreetingDomain)
@check_roles(NoneRole)
class GreetPersonAction(BaseAction[GreetParams, GreetResult]):

    @summary_aspect("Build greeting and return result")
    async def greet_summary(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "Greeting: Hello, {%var.name|cyan}!",
            name=params.name,
        )
        return GreetResult(message=f"Hello, {params.name}!")
```

`BaseParams` and `BaseResult` are Pydantic models, and `Field(description=...)` is again not a comment: the description goes into the external schema. Input fields are read directly: `params.name`. This is the operation's external contract — what its caller sees.

`box` is more interesting. The machine passes it into every aspect; it is a structured logger bound to the current step, with three levels — `box.info`, `box.warning`, `box.critical`. It differs from `print` not in convenience but in the nature of the record. `print` tosses a context-free string into a stream: who wrote it, how important it is, whether it can be found later — all unknown. `box.info` gives birth to an event — it carries the channel, level, domain, operation name, and aspect name, and so it lends itself to filtering, routing, export. Inside operations you speak through `box`, not `print` — and that is not a stylistic preference but the boundary between business code and its observability.

The arguments read naturally. The first is the **channel**: `Channel.business` marks the record as a business event (there are also `debug`, `security`, `compliance`, `error`, and they can be combined with `|`). The second is the **template**: `{%var.name}` substitutes the passed value, and `{%var.name|cyan}` also colors it (`red`, `green`, `yellow`, `blue`, `cyan`, `magenta`, `white`, `grey` and their `bright_` variants). Then come the values themselves: `name=params.name`.

There is a neat decoupling hidden here. Where the event goes the operation does not decide — that is the machine's concern. Without a logger `box.info` is simply dropped silently; to make a record reach the console, you give the machine a coordinator:

```python
machine = ActionProductMachine(
    log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
)
```

The operation's code does not change by a single character — whether logging is on or off is decided from the outside. Business logic does not know who delivers its events, or where.

**Run:**

```
uv run python examples/step_01_Action_and_pipeline/02_params_result_and_box.py
```

**Output:**

```
  Greeting: Hello, Alice!

Result: Hello, Alice!
```

*("Alice" is shown in cyan in the terminal.)*

---

## Multiple aspects

[▶ Try in Colab](https://drive.google.com/file/d/1sxwC9n4P7ArCU155zBnUhF15EDhUKI1E/view?usp=drive_link) · [Open in project](../../examples/step_01_Action_and_pipeline/03_multiple_aspects.py)

One step is rarely enough. Usually there are several, and intermediate data must pass between them. In ordinary code such data settles wherever it can — in local variables, in object fields, in thread-locals — and either vanishes with the call or, conversely, lingers and turns the object into an unnoticed store of state between calls. AOA leaves no such freedom: intermediate data flows through the pipeline in an explicit `state`, while the `Action` itself stays empty between calls.

A pipeline step is called an **aspect**. There are two kinds: intermediate (`@regular_aspect`) and terminal (`@summary_aspect`).

```python
@meta(description="Process input string through multiple steps", domain=ProcessingDomain)
@check_roles(NoneRole)
class ProcessInputAction(BaseAction[ProcessParams, ProcessResult]):

    @regular_aspect("Step 1: Strip whitespace and lowercase")
    @result_string("cleaned", required=True)
    async def validate_aspect(self, params, state, box, connections):
        cleaned = params.raw_input.strip().lower()
        return {"cleaned": cleaned}

    @regular_aspect("Step 2: Enrich data")
    @result_string("cleaned", required=True)
    @result_string("enriched", required=True)
    async def enrich_aspect(self, params, state, box, connections):
        enriched = f"enriched::{state['cleaned']}"
        return {"cleaned": state["cleaned"], "enriched": enriched}

    @summary_aspect("Step 3: Assemble final result")
    async def assemble_summary(self, params, state, box, connections):
        return ProcessResult(
            cleaned=state["cleaned"],
            enriched=state["enriched"],
            final=f"{state['cleaned']} → {state['enriched']}",
        )
```

A regular aspect runs before the terminal one and returns not a result but a dictionary, which becomes the new `state`. Let's follow it. The pipeline starts with an empty `state`; the first step puts `cleaned` into it; the second reads `cleaned`, adds `enriched`, and returns both; the terminal step assembles the result from `state`. A simple picture — but it hides a detail that surprises people at first.

The returned dictionary **replaces** `state` entirely; it does not extend it. Keys from the previous step do not carry over on their own — which is why the second aspect explicitly returns `"cleaned": state["cleaned"]`: had it not, `cleaned` would not have survived to the third step. It looks like an extra line, but it is not an API oversight — it is a direct consequence of `state` being a sequence of independent snapshots rather than a shared mutable bag. What this means for testability and observability we'll work through in full in the next chapter.

A new entry has appeared above the methods — `@result_string("cleaned", required=True)`. This is a **checker**, a verifiable contract on an aspect's output: "after this step `state["cleaned"]` holds a non-empty string." Break the promise and the machine stops the aspect on the spot, never letting the spoiled `state` pass further. You can hang as many checkers on one aspect as you like — one per field; the whole next chapter is devoted to them.

And one last thing, quiet but important: aspects execute in the order they are declared in the class. This is not an agreement between developers but a guarantee of the machine — the pipeline is linear, and the linearity is enforced, not assumed.

**Run:**

```
uv run python examples/step_01_Action_and_pipeline/03_multiple_aspects.py
```

**Output:**

```
  [Step 1] cleaned=hello world
  [Step 2] enriched=enriched::hello world
  [Step 3] final=hello world → enriched::hello world

Result:
  cleaned  = 'hello world'
  enriched = 'enriched::hello world'
  final    = 'hello world → enriched::hello world'
```

*(the log lines are colored: green → yellow → cyan)*

---

## Inheritance

[▶ Try in Colab](https://drive.google.com/file/d/1lpjOhb7nrtrUpuF3r8VLjSJInanG9Csc/view?usp=drive_link) · [Open in project](../../examples/step_01_Action_and_pipeline/04_inheritance.py)

> If operation inheritance is of no use to you right now, you can skip this section and come back later; it does not affect the other chapters.

Operations inherit like ordinary classes — but with one caveat that runs against intuition and so deserves a separate word. Imagine that a parent's aspects automatically entered the child's pipeline. Then, to understand what an operation does, you would have to read not it but the whole chain of ancestors — and the idea "open the class, see the operation" would fall apart. So in AOA **aspects are not inherited into the pipeline**: the machine builds the pipeline only from what is declared in the class itself. You can reuse a parent's logic — but consciously and explicitly.

```python
# Parent: two aspects in the pipeline
class BaseOrderAction(BaseAction[OrderParams, OrderResult]):
    @regular_aspect("Validate order")
    async def validate_aspect(self, ...): ...

    @summary_aspect("Base result")
    async def base_summary(self, ...): ...


# Child: declares only its own summary
# validate_aspect from the parent will NOT enter the pipeline
class ChildOrderAction(BaseOrderAction):
    @summary_aspect("Child result")
    async def child_summary(self, ...): ...


# The right way: declare the aspect explicitly and call super()
class ExtendedOrderAction(BaseOrderAction):
    @regular_aspect("Validate order")           # explicitly declared — enters the pipeline
    @result_instance("steps", list, required=True)
    async def validate_aspect(self, params, state, box, connections):
        result = await super().validate_aspect(params, state, box, connections)
        return {**result, "extended": True}     # add our own on top of the parent's
```

`ChildOrderAction` will run fine and return a result — but its pipeline contains only `child_summary`, and the parent's `validate_aspect` does not execute. `ExtendedOrderAction` does it right: it re-declares `validate_aspect` in the desired place and calls `super()` to run the ancestor's logic and build on it. The moment of execution is set by the method's position in the child's body, not in the parent's. The checker `@result_instance("steps", list, required=True)` is a relative of `@result_string` for non-string types: it guards that `state["steps"]` holds a non-empty list.

**Run:**

```
uv run python examples/step_01_Action_and_pipeline/04_inheritance.py
```

**Output:**

```
────────────────────────────────────────────────────────────
  1. BaseOrderAction (direct parent run)
────────────────────────────────────────────────────────────
  [BaseOrderAction.validate_aspect] order_id=ord-001
  [BaseOrderAction.base_summary] done
  → steps executed: ['validate']

────────────────────────────────────────────────────────────
  2. ChildOrderAction (parent aspects are NOT inherited)
────────────────────────────────────────────────────────────
  [ChildOrderAction.child_summary] order_id=ord-001
  → steps executed: ['child_only']

────────────────────────────────────────────────────────────
  3. ExtendedOrderAction (explicit declaration + super())
────────────────────────────────────────────────────────────
  [BaseOrderAction.validate_aspect] order_id=ord-001
  [ExtendedOrderAction.validate_aspect] steps: ['validate', 'extended_validate']
  [ExtendedOrderAction.extended_summary] done
  → steps executed: ['validate', 'extended_validate']
```

The difference is plain: `ChildOrderAction` has a single-step pipeline with no `validate` in it; `ExtendedOrderAction` has both steps, because the aspect is declared explicitly.

---

## Intents and runtime contracts

This chapter has accumulated quite a few rules — name suffixes, required decorators, non-empty descriptions, checker coverage of fields. What matters is not their number but one shared property: almost all of them are checked **at class declaration**, that is, at module import — not at the operation's call.

This is the central idea of AOA: code here is an executable specification. A contract violation surfaces not one night in production but immediately, before the first run — the fail-fast principle, which shifts the cost of an error to the earliest possible point. Below is the full list of this chapter's contracts; keep it at hand until the model settles.

### Naming

Suffixes are checked at class declaration or at decorator application. Violation → `NamingSuffixError`.

| Element | Rule | Violation example |
|---------|------|-------------------|
| Domain class | ends with `Domain` | `class Greeting(BaseDomain)` |
| Action class | ends with `Action` | `class SayHello(BaseAction[...])` |
| `@summary_aspect` method | ends with `_summary` | `async def output(self, ...)` |
| `@regular_aspect` method | ends with `_aspect` | `async def validate(self, ...)` |

### Required decorators

| What's missing | Error |
|----------------|-------|
| `@meta` | `MissingMetaError` |
| `@check_roles` | `MissingCheckRolesError` |
| `@summary_aspect` | `MissingSummaryAspectError` |

`NoneRole` in `@check_roles(NoneRole)` is an intent spoken out loud, not a default value. The absence of the decorator is not "open to everyone" — it is `MissingCheckRolesError`.

### Non-empty descriptions

The description enters external schemas and documentation. An empty string → `ValueError`:

```python
@meta(description="")       # ValueError
@summary_aspect("")         # ValueError
@regular_aspect("")         # ValueError
```

### Result contracts

A `@regular_aspect` must return a dictionary, and every field of a non-empty dictionary must be covered by a checker — otherwise `ValidationFieldError`:

```python
# Violation: field "cleaned" is not covered by a checker
@regular_aspect("Step 1")
async def validate_aspect(self, ...):
    return {"cleaned": "value"}   # ValidationFieldError

# Correct: the field is declared
@regular_aspect("Step 1")
@result_string("cleaned", required=True)
async def validate_aspect(self, ...):
    return {"cleaned": "value"}   # OK
```

The checkers met in this chapter:

| Checker | Checks |
|---------|--------|
| `@result_string("key", required=True)` | `state["key"]` is a non-empty string |
| `@result_instance("key", SomeType, required=True)` | `state["key"]` is an instance of `SomeType`, not `None` |

Several checkers per aspect — one per field. Their full set and parameters are in the next chapter.

### Aspects are not inherited

The deliberate constraint discussed above: the pipeline is built only from aspects explicitly declared in the class. This is what secures readability — the composition of any operation is visible from its body, without a journey through the chain of ancestors.

---

## Summary

The core of the model is already in hand. An operation is an `Action` with a typed boundary (`Params` and `Result`), a linear pipeline of aspects, and contracts that are mostly checked at initialization. Behavior is expressed in the structure of the code, not in documentation lying next to it.

We have only touched the `@result_string` checker in passing, as a detail. The next chapter — **[State: the operation's x-ray](step-02-state-as-x-ray.md)** — raises it to the foundation of the model: `state` as a sequence of verifiable snapshots, all the checker types, optional fields, and finally how `state` becomes an x-ray of the whole operation and ties into observability through OpenTelemetry.

---

## Review questions

1. Which invariant secures an operation's "from one class" readability, and at what moment is it checked?
2. Why is the absence of `@check_roles` an error and not a silent "open to everyone"? Which property of the system does this protect?
3. The AOA pipeline is linear — no branches, no side exits. What does this constraint buy, and at what cost?
4. How does the declarative contract of an `Action` (`Params`/`Result` plus aspects) differ from a service method with several inputs and implicit outputs via `return`, exceptions, and side effects?
5. Why are aspects not inherited into the pipeline automatically? Compare with ordinary method inheritance in OOP.
6. What does "code is an executable specification" mean, and why are most contracts checked at initialization rather than at runtime?

> **Exercise.** Insert a new `@regular_aspect` into the operation from `03_multiple_aspects.py`, between the existing steps — so that it does not change the business meaning. What must it return for the pipeline to stay valid, and why will the machine not pass a step that "forgot" some of the fields? (The breakdown is in the next chapter.)

---

<table width="100%"><tr>
  <td align="left"><a href="step-00-get-started.md">← Step 00 — Getting started</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"><a href="step-02-state-as-x-ray.md">Step 02 — State: the operation's x-ray →</a></td>
</tr></table>
