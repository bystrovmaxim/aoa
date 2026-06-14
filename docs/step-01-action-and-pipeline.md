# Step 01 — Action and Pipeline

<p align="center">
  <a href="step-00-get-started.md">00 · Get Started</a> &nbsp;·&nbsp;
  <strong>01 · Action and Pipeline</strong> &nbsp;·&nbsp;
  <em>02 · State (coming soon)</em>
</p>

---

Every business operation in AOA is a class called an `Action`. It has a typed input (`Params`), a typed output (`Result`), and between them — a straight chain of steps from top to bottom. No branching, no side exits. Open the class — see the entire operation.

This is a step-by-step tutorial. Each section corresponds to one file in `examples/step_01_Action_and_pipeline/`. Read the section, run the file, move to the next.

---

## 01_hello_world.py

[▶ Try in Colab](https://colab.research.google.com/drive/18pg9YvgScxVj-8CQaFS7ohbnqX_TvT6z?usp=sharing) · [View in project](../examples/step_01_Action_and_pipeline/01_hello_world.py)

Let's start with the minimum: an Action that prints "Hello, world!" and nothing else. No input, no result — just to see what the simplest possible structure looks like.

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

Let's break it down.

**`BaseDomain`** — every Action must belong to a domain. A domain is a logical grouping: operations from the same subject area live together. The class name must end with `Domain` — try writing `class Greeting(BaseDomain)` and you'll get a `NamingSuffixError` at class declaration time, not at runtime.

**`@meta`** — the first required decorator. It declares what this operation is and which domain it belongs to. The `description` ends up in OpenAPI, MCP tools, and the operation graph in Maxitor — this is not a comment, it's part of the system contract.

**`@check_roles(NoneRole)`** — the second required decorator. The machine will not run any operation without an explicit access declaration. `NoneRole` means "open to everyone" — but you need to write this explicitly; silent absence of a check doesn't count.

**`BaseAction[ParamsStub, ResultStub]`** — the base class for all operations. The type parameters are the input and output types. `ParamsStub` and `ResultStub` are placeholders for when there's no real data. The class name must end with `Action`.

**`@summary_aspect`** — the single exit point of an Action. This is where the result is assembled and returned. Without it the machine raises `MissingSummaryAspectError` at startup. The method must end with `_summary`; the description cannot be empty.

You can run the operation like this:

```python
machine = ActionProductMachine()
await machine.run(Context(), SayHelloAction(), ParamsStub())
```

**`ActionProductMachine`** — the executor: it reads the operation declarations and runs the pipeline. **`Context()`** — the call context, currently empty. Later it will hold the current user, their roles, and the request trace_id — but that's a topic for a separate step. You cannot pass `None`: the machine requires an explicit object, even an empty one. **`ParamsStub()`** — an instance of the stub we declared as the input type.

**Run:**

```
uv run python examples/step_01_Action_and_pipeline/01_hello_world.py
```

**Output:**

```
Hello, world!
```

> **Experiment:** try renaming `SayHelloAction` to `SayHello`, or the method to `output`, or writing `@summary_aspect("")`. In each case you'll get an error at declaration time — not at runtime, but the moment you write the code. Read the messages: they tell you what's wrong and how to fix it.

---

## 02_params_result_and_box.py

[▶ Try in Colab](#) · [View in project](../examples/step_01_Action_and_pipeline/02_params_result_and_box.py)

Now let's build an operation with real data: we accept a name and return a greeting. We'll also move from `print` to structured logging via `box`.

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

Instead of `ParamsStub` and `ResultStub`, we declare real models. `BaseParams` and `BaseResult` are Pydantic models; fields are described with `Field(description=...)`. The description in `Field` is not a code comment: it ends up in the OpenAPI schema and MCP tool. Params fields are accessible directly inside the aspect: `params.name`.

Now about `box`. Inside every aspect there's a `box` parameter — a structured logger bound to the current step. It has three methods: `box.info(...)`, `box.warning(...)`, `box.critical(...)`.

How is it different from `print`? `print` just dumps a string to stdout — no context, no level, no filtering. `box.info(...)` creates an event that carries the channel, level, domain, operation name, and aspect name. These events can be filtered, routed to different storages, and exported to an OCEL log. Inside aspects — always use `box`.

The first argument to `box.info` is the channel. `Channel.business` means "this is a business event". There are several channels: `business`, `debug`, `security`, `compliance`, `error`. You can combine them: `Channel.business | Channel.security`.

The second argument is a substitution template. `{%var.name}` inserts the value from kwargs. `{%var.name|cyan}` inserts it colored cyan. Available colors: `red`, `green`, `yellow`, `blue`, `cyan`, `magenta`, `white`, `grey`, and their `bright_` variants.

By default `ActionProductMachine` doesn't know where to write events — `box.info` is simply ignored. To see output:

```python
machine = ActionProductMachine(
    log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
)
```

If you don't need a logger — just don't pass `log_coordinator`. The `box.info` calls stay in the code and won't break it: events simply have nowhere to go and are silently discarded.

**Run:**

```
uv run python examples/step_01_Action_and_pipeline/02_params_result_and_box.py
```

**Output:**

```
  Greeting: Hello, Alice!

Result: Hello, Alice!
```

*(«Alice» is highlighted in cyan in the terminal)*

---

## 03_multiple_aspects.py

[▶ Try in Colab](#) · [View in project](../examples/step_01_Action_and_pipeline/03_multiple_aspects.py)

So far we've had only one aspect — `@summary_aspect`. But operations usually consist of multiple steps. Data needs to flow between them. For this there are intermediate steps — `@regular_aspect` — and a `state` dictionary that flows through the pipeline.

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

`@regular_aspect` — an intermediate pipeline step. It runs before `@summary_aspect` and returns not a result but a `dict`. That `dict` becomes the new `state`.

Here's how `state` works. The pipeline starts with `state = {}`. Step 1 returns `{"cleaned": "hello world"}` — now `state` is exactly that. Step 2 reads `state["cleaned"]`, adds `"enriched"`, and returns both keys — `state` is updated again. Step 3 (`@summary_aspect`) reads `state` and assembles the final result.

Important: every `@regular_aspect` returns a `dict` that **completely replaces** the previous `state`. Keys from the previous step are not saved automatically — you need to pass them explicitly. That's why in Step 2 we write `"cleaned": state["cleaned"]` — otherwise Step 3 won't see it.

Rules for `@regular_aspect`: the method must end with `_aspect`, must be `async def`, and the description cannot be empty.

Now about `@result_string("cleaned", required=True)`. This is a contract: "after this aspect, `state["cleaned"]` must contain a non-empty string". If the aspect returns a dict without this key — the machine catches it immediately, preventing the next step from receiving a broken `state`. Contracts stack — you can declare multiple on a single aspect.

Aspects run strictly in the order they are declared in the class. This is not a convention — it's a machine guarantee.

**Remember about `state`:**
- Each `@regular_aspect` returns a `dict` that **completely replaces** `state`.
- Need data from the previous step — return it explicitly in the dict.
- `@result_string` and other checkers catch errors immediately, preventing a broken `state` from reaching the next step — use them.

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

*(log lines are colored: green → yellow → cyan)*

> **Experiment:** swap `validate_aspect` and `enrich_aspect`. Run it. `enrich_aspect` will try to read `state["cleaned"]`, which doesn't exist yet — and you'll get a `KeyError`. This clearly shows that declaration order is execution order, and `state` contains only what the last step returned.

---

## 04_inheritance.py

[▶ Try in Colab](#) · [View in project](../examples/step_01_Action_and_pipeline/04_inheritance.py)

> If you don't need Action inheritance right now — feel free to skip this section and come back when you do.

Actions can be inherited. But there's an important behavior you need to know upfront.

Aspects declared in a parent class **do not automatically enter the child's pipeline**. If a child declares its own `@summary_aspect`, the machine builds a pipeline only from the aspects explicitly declared in the child itself.

Why? AOA requires the pipeline to be readable from the class itself. If aspects were inherited automatically, understanding what an operation does would require reading the entire parent chain — which defeats the whole idea of explicit declaration.

Let's look at three variants:

```python
# Parent: two aspects in the pipeline
class BaseOrderAction(BaseAction[OrderParams, OrderResult]):
    @regular_aspect("Validate order")
    async def validate_aspect(self, ...): ...

    @summary_aspect("Base result")
    async def base_summary(self, ...): ...


# Child: declares only its own summary
# validate_aspect from parent — will NOT enter the pipeline
class ChildOrderAction(BaseOrderAction):
    @summary_aspect("Child result")
    async def child_summary(self, ...): ...


# The right way: declare the aspect explicitly and call super()
class ExtendedOrderAction(BaseOrderAction):
    @regular_aspect("Validate order")           # explicitly declared — will enter the pipeline
    @result_instance("steps", list, required=True)
    async def validate_aspect(self, params, state, box, connections):
        result = await super().validate_aspect(params, state, box, connections)
        return {**result, "extended": True}     # add our own on top of parent's

    @summary_aspect("Extended result")
    async def extended_summary(self, ...): ...
```

`ChildOrderAction` will run and return a result — but its pipeline contains only `child_summary`. The `validate_aspect` from `BaseOrderAction` will not execute. There will be no `"validate"` in the steps list.

`ExtendedOrderAction` solves this explicitly: it re-declares `validate_aspect` in the right position and calls `super()` to execute the parent's logic. The method's position in the class body determines when it runs — its position in the parent class doesn't matter.

`validate_aspect` in the example has `@result_instance("steps", list, required=True)` — the equivalent of `@result_string` for non-string types. It verifies that `state["steps"]` is a `list` and is not empty. The rule is the same: if an aspect returns a non-empty `dict`, every field must be covered by a checker — otherwise the machine will reject that result.

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

It's plain to see: in `ChildOrderAction` the pipeline has one step, `validate` is not there. In `ExtendedOrderAction` — both steps, because `validate_aspect` is explicitly declared.

> **Experiment:** add your own `validate_aspect` to `ChildOrderAction` with `@regular_aspect` (without `super()`). Run it. Now it will execute — because it's explicitly declared. This confirms once again: the machine sees only what is explicitly written in the class.

---

## Summary

Four examples — and you already know the entire AOA core: how to declare an operation, pass data to it, run it through multiple steps, and return a typed result. Every concept lives in the code, not in the documentation alongside the code.

Next up: roles and authorization, sagas and compensation (`@compensate`), error handling (`@on_error`), caching, resources, and external connections.

---

<p align="center">
  <a href="step-00-get-started.md">00 · Get Started</a> &nbsp;·&nbsp;
  <strong>01 · Action and Pipeline</strong> &nbsp;·&nbsp;
  <em>02 · State (coming soon)</em>
</p>
