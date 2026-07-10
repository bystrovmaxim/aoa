<!-- translated-from: environment-context-port_draft.md @ 2026-07-01T11:29:00Z (filesystem mtime; draft is gitignored, no git history) · sha256:b100a149f114 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Environment Context Port

<table width="100%"><tr>
  <td align="left"><a href="iop-foundations.md">IOP: Intents and Invariants</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [The problem: environment as a hidden dependency](#the-problem-environment-as-a-hidden-dependency)
- [The idea: environment as an explicit Context port](#the-idea-environment-as-an-explicit-context-port)
- [Why a provider, not a value](#why-a-provider-not-a-value)
- [What it could look like](#what-it-could-look-like)
- [The main risk: a Context with execution logic](#the-main-risk-a-context-with-execution-logic)
- [The access invariant via context_requires](#the-access-invariant-via-context_requires)
- [Request-cache semantics](#request-cache-semantics)
- [TestBench and substituting the environment](#testbench-and-substituting-the-environment)
- [Types, sensitivity, and observability](#types-sensitivity-and-observability)
- [Open questions](#open-questions)
- [The short formula](#the-short-formula)

---

## The problem: environment as a hidden dependency

AOA consistently pulls dependencies out of the body of the code and into explicit contracts. `Params` describes the input, `Result` the output, `state` the contract between steps, `@depends` and `@connection` the allowed external capabilities, `@context_requires` a slice of the call's context.

But one channel is often left in the dark: the execution environment.

Feature flags, environment variables, runtime settings, tenant config, A/B parameters, and operational limits are usually read directly:

```python
@regular_aspect("Select flow")
async def select_flow_aspect(self, params, state, box, connections):
    if os.getenv("ENABLE_NEW_FLOW") == "true":
        ...
```

For Python this is ordinary code. For AOA this is a hidden dependency. The graph doesn't see it, TestBench can't substitute it as part of a scenario, observability doesn't know the decision depended on `ENABLE_NEW_FLOW`, and a reader doesn't see from the aspect's header that the operation relies on the environment.

If the environment influences a business decision, it must become part of an explicit contract.

---

## The idea: environment as an explicit Context port

Proposal: add a separate `environment` block to `Context` — an explicit environment port.

This isn't a replacement for `Resource`. `Resource` describes the outside world an operation interacts with as a source of data or effects: a database, an API, a queue, file storage. `environment` describes a read-oriented layer of the execution environment: flags, settings, limits, modes, deployment characteristics, tenant-specific configuration.

The key principle:

> **An Action doesn't read the environment directly. It declares which environment slice it needs, through `@context_requires`.**

So the environment becomes an extension of the existing Context model: not an ambient global, but an explicitly requested part of the call.

---

## Why a provider, not a value

If you read every environment variable when the machine starts, the system gets a static snapshot. That's convenient, but it doesn't fit live parameters: a feature flag changed, a limit was updated, tenant config changed, and an Action only sees the new value after a restart.

So `environment` should store not the actual value but a provider:

```python
@environment("enable_new_flow", lambda: read_flag("new_flow"), cache="request")
```

The provider is called lazily: only when an Action actually requests the environment field. This gives three properties:

1. **Freshness.** The next call may see an updated value.
2. **Economy.** Values that aren't used aren't read.
3. **Controlled stability.** The cache scope can hold a value stable within a single request, so it doesn't change between aspects of one operation.

Lazy reading matters especially for AOA: if the environment becomes a port, the port has to be live, but not chaotic.

---

## What it could look like

A possible API:

```python
@environment("enable_new_flow", provider=lambda: read_flag("new_flow"), type_=bool, cache="request")
@environment("risk_limit", provider=lambda: read_limit("risk"), type_=int, cache="ttl", ttl_seconds=30)
class AppContext(BaseContext):
    ...
```

Used inside an Action:

```python
@regular_aspect("Select order flow")
@context_requires(AppContext.Env.enable_new_flow)
async def select_flow_aspect(self, params, state, box, connections, context):
    if context.env.enable_new_flow:
        return {"flow": "new"}
    return {"flow": "classic"}
```

The point isn't the exact syntax. What matters is the shape:

- the environment key is declared on the Context class;
- the provider is registered declaratively;
- the result type is known to the system;
- an Action gets access only through `@context_requires`;
- reading it can be reflected in trace/log as a dependency fact, without exposing the sensitive value.

---

## The main risk: a Context with execution logic

The current `Context` is conceptually close to a value object: it's call data, passed into `machine.run()`. Adding providers changes the object's nature. Inside Context there's now the possibility of running code when a field is read.

That's a dangerous boundary.

If it gets blurred, `Context` can become a new `os.environ`: seemingly elegant, typed, and decorated, but still a global source of hidden logic. Then AOA loses one of its main properties — the local explicitness of dependencies.

So the research question isn't "what's the most convenient way to read a flag." The question is harder:

> How do you add a live environment without turning Context into a hidden service locator?

The answer has to be an invariant, not a recommendation.

---

## The access invariant via context_requires

The base rule:

> **An environment field's provider can only be called for a field declared through `@context_requires` by the current aspect.**

This must be checked by the machine.

Not allowed:

```python
async def select_flow_aspect(self, params, state, box, connections, context):
    # No @context_requires(AppContext.Env.enable_new_flow)
    if context.env.enable_new_flow:
        ...
```

Allowed:

```python
@context_requires(AppContext.Env.enable_new_flow)
async def select_flow_aspect(self, params, state, box, connections, context):
    if context.env.enable_new_flow:
        ...
```

This preserves AOA's main principle: an aspect's header shows what it relies on. The environment becomes not a loophole into global state, but one more declared slice of the context.

If this rule can't be checked, the idea weakens the architecture. If the rule is checked, environment becomes a new IOP atom.

---

## Request-cache semantics

The subtlest question is what counts as one request.

In AOA a root `machine.run()` can trigger nested `box.run()` calls. These calls logically belong to a single root session and share one Context. If an environment provider has `cache="request"`, the natural expectation is: the value is read once for the root run and then stays stable for every aspect and nested Action in that session.

This guards against strange behavior:

1. `ValidateOrderAction` read `enable_new_flow=True`.
2. Between aspects, the flag changed.
3. `CreateOrderAction`, inside the same root run, read `False`.
4. One business scenario ran across two different realities.

Request-cache should prevent this kind of desync.

But there are edge cases:

- does a nested `box.run()` inherit the root session's cache, or get its own?
- what happens with `asyncio.create_task()` inside an Action?
- does the cache carry over into a background task?
- should the cache live in `Context`, in the execution session, in `ContextView`, or in a separate `EnvironmentScope`?
- what counts as a "request" for a cron/job/CLI call, where there's no HTTP request?

Preliminary position: `request` in AOA should mean a **root machine execution session**, not an HTTP request. Nested `box.run()` calls inherit the scope. Background activity should either explicitly create a new scope or explicitly inherit an existing one, or cache leaks will be unpredictable.

---

## TestBench and substituting the environment

The environment port must be substitutable just as explicitly as a Resource.

Otherwise a test ends up tied to the machine's real environment again:

```python
bench = TestBench(CreateOrderAction).with_environment(
    enable_new_flow=True,
    risk_limit=10_000,
)
```

or:

```python
bench = TestBench(CreateOrderAction).with_environment_provider(
    AppContext.Env.risk_limit,
    lambda: 10_000,
)
```

Two modes matter here:

- substituting a value — for simple scenarios;
- substituting a provider — for checking lazy reading, cache scope, provider errors, and the value changing between requests.

This lets TestBench check not just the business scenario but also the environment it runs in. It's an extension of WST: a test substitutes not the Action's internals, but the world around it. The environment is part of that world.

---

## Types, sensitivity, and observability

Environment shouldn't be a `str -> Any` dict.

Minimal requirements:

| Area | Requirement |
|---------|------------|
| Types | the provider declares the result type, or the schema is inferred from the declaration |
| Validation | the value is checked on read, and an error is localized to the environment key |
| Cache | scopes like `none`, `request`, `ttl` are supported |
| Sensitivity | secret values are masked and never reach the state x-ray / logs |
| Observability | the system records the fact that an environment key was read, the provider's latency, and the cache hit/miss |
| Errors | the provider's failure policy is declared explicitly: fail-fast, default, fallback, degraded |

Observability matters especially, but it must not expose secrets. A useful event looks like this:

```text
Environment read:
  action=CreateOrderAction
  aspect=select_flow_aspect
  key=enable_new_flow
  cache=request_hit
  value_masked=true
```

The system should show the dependency on the environment, but doesn't have to show the value itself.

---

## Open questions

1. **Where are providers declared?** On the `Context` class through decorators, when a `Context` instance is created, in a separate registry, or a mix?
2. **What syntax is best?** `@environment(...)`, a nested `Env` class, field descriptors, `Annotated`, Pydantic fields with provider metadata?
3. **What is the request scope?** The root `machine.run()`, the adapter request, the `Context` instance, or the execution session?
4. **How should this behave in background tasks?** Inherit the environment cache, create a new scope, or require an explicit choice?
5. **How is the failure policy described?** Always fail-fast, or support `default`, `fallback_provider`, `degraded_mode`?
6. **How do you substitute the environment in TestBench?** With values, with providers, with scenarios of change over time?
7. **How do you avoid exposing secrets?** Do you need `opaque=True`, `@sensitive`, a separate `secret=True`, or a single masking mechanism?
8. **How do you forbid a hidden global?** Is `ContextView` enough, or do you need static analysis that forbids `os.getenv()` and direct access to settings inside an Action?
9. **How is environment reflected in the graph/Maxitor?** Should it show key-level dependencies, cache scope, sensitivity, the provider's owner?
10. **Should environment be read-only?** If an Action wants to change a feature flag or a runtime config, that's no longer an environment read — it's a separate `Resource` or a management `Action`.

---

## The short formula

The Environment Context Port closes the last implicit gap in AOA's model.

Before:

```text
Action -> os.environ / settings / feature flags
```

That's a hidden dependency.

After:

```text
Action -> @context_requires(Context.Env.key) -> environment provider
```

That's a declared and checkable environment port.

The main principle:

> **The environment can be live, but access to it must stay explicit.**

If this principle holds, `environment` won't become a new form of global state — it will become one more IOP atom: an intent turned into a checkable invariant.

---

<table width="100%"><tr>
  <td align="left"><a href="iop-foundations.md">IOP: Intents and Invariants</a></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>
