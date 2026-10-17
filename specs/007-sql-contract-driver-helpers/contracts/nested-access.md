# Contract: nested access after the proxy stops delegating

**Feature**: `specs/007-sql-contract-driver-helpers/spec.md` · **Date**: 2026-10-17

This contract fixes what a nested action receives, what it may reach, and how a domain gives it something of its own.
It is normative for the implementation and for the documentation tasks, because the example cases are part of the
contract a reader copies.

## 1. What the runtime hands a nested action

**NA-1.1** The framework MUST keep building the proxy in one place — `ToolsBox._wrap_connections`
(`packages/aoa-action-machine/src/aoa/action_machine/runtime/tools_box.py:191`) asks the resource for
`get_wrapper_class()` and constructs whatever class comes back, or hands the resource over unwrapped when the answer
is `None`.

**NA-1.2** `SqlResource.get_wrapper_class()` MUST keep answering `WrapperSqlResource`; a resource that wants nested
access MUST override it with its own class instead of the framework gaining a second mechanism.

**NA-1.3** The wrapped mapping handed to a nested action MUST keep its shape: the same keys, and values that still
satisfy the contract the caller's declaration names.

## 2. What the default proxy answers

| Member | Answer |
| --- | --- |
| `rollup` | delegated to the owner |
| `check_rollup_support()` | delegated to the owner |
| `open`, `begin`, `commit`, `rollback`, `close` | `TransactionProhibitedError`, with the message that says the operation belongs to the action that created the resource |
| `__aenter__`, `__aexit__` | `TransactionProhibitedError` |
| `get_wrapper_class()` | itself, so a second and a third wrap behave as the first |
| a query member of any kind | **nothing** — it MUST NOT exist on the proxy, and MUST NOT be delegated |

**NA-2.1** The absence is the contract: `hasattr(proxy, "execute")`, `hasattr(proxy, "_execute")` and
`hasattr(proxy, "_fetchrow")` MUST all be false. A refusal was the old answer; the absence is the new one, and a
proxy that raised a refusal for a query member would still expose one.

**NA-2.2** The proxy MUST still satisfy the structural contract, so `isinstance(proxy, ProtocolSqlResource)` MUST be
true. That is a consequence of removing the member from the protocol and the proxy in the same change, and it is
asserted by the tests.

**NA-2.3** The proxy MUST NOT offer any way to acquire a connection — no `acquire`, no `_conn`, no accessor.

## 3. The domain wrapper — how nested access is given

**NA-3.1** A resource that wants a nested action to do something MUST declare its own wrapper class, return it from
`get_wrapper_class()`, and delegate its own semantic methods there. The repository's existing example is
`OcelStoreWrapper` (`packages/aoa-ocel/src/aoa/ocel/resource/ocel_store_wrapper.py`): it delegates `add_event` and
refuses the lifecycle.

**NA-3.2** A domain wrapper MUST keep refusing the lifecycle operations, and MUST keep refusing context-manager use,
exactly as the default proxy does. Delegation is added; refusal is not dropped.

**NA-3.3** A domain wrapper MUST delegate only methods the domain chose to publish. There MUST be no automatic
delegation of the owner's public surface: a nested action's reach is what the domain wrote, not what the owner
happens to have.

**NA-3.4** An error raised by a delegated method MUST reach the nested action as the domain's own error, with the
underlying error chained, rather than as a raw driver error.

**NA-3.5** A domain wrapper MUST be excluded from the graph model (`@exclude_graph_model`), exactly as
`WrapperSqlResource` and `OcelStoreWrapper` are. It is a proxy rather than a resource the graph describes, and the
metadata resolver refuses a class it can see without a `@meta` description — which means an undeclared proxy breaks
every machine build, not only the nested call. The example case is what established this: the first run of the
enriched nested-action case failed at `ActionProductMachine()` construction, before any nested call.

## 4. What the example cases show afterwards

| Case | Before | After |
| --- | --- | --- |
| `examples/step_19_resource/04_wrapper_execute.py` (+ `.ipynb`) and the tutorial section `## A wrapper can execute a statement` | builds a proxy by hand and runs a statement through it, printing the status | **deleted** — script, notebook, section and the tutorial's link to it; its subject no longer exists |
| `examples/step_19_resource/07_nested_action.py` (+ `.ipynb`) and `## A real nested action receives a restricted view` | a parent hands the proxy to a child, the child tries to close and is refused | the same refusal, **plus** the domain wrapper: the resource declares its own wrapper class and its own semantic method, the child calls that method successfully, and `close` stays refused |
| The pages that explain the proxy | the wrapper forwards the removed member | the wrapper forwards nothing; the domain wrapper is how access is given |

**NA-4.1** The later example cases MUST keep their numbers; the deletion leaves a gap rather than renaming every
later notebook and rewriting every link to it.

**NA-4.2** The examples runner (`tests/examples/test_examples_run.py`) discovers scripts by walking
`examples/**/*.py`, so the deletion and the edit MUST both leave it green with no database running.

## 5. What the contract deliberately does not say

- **Nothing about mode 1 (a ready resource).** A resource supplied ready is not wrapped for a nested action at all;
  that is the caller's own choice and is unchanged by this feature.
- **Nothing about the OCEL store.** `OcelStoreWrapper` is cited as the pattern; it is not migrated, and its protocol
  is its own.
- **Nothing about a passthrough a domain might want anyway.** A resource may publish its own public method that runs
  a statement; the framework neither provides nor forbids it, and the domain owns its name, its return type and its
  documentation.
