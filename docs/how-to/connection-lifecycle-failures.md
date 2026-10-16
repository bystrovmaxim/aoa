# Diagnose connection lifecycle failures

Start with [Step 17](../tutorials/step-17-connections.md) if the terms factory,
finalizer and resource scope are new. This guide separates declaration mistakes,
acquisition failures, execution failures and cleanup failures. Each link provides
an independent script and notebook; nothing depends on running an earlier example.

The small `TraceResource` records `open` and `close` in a list. It owns no external
handle, so these cases test the real `connection_scope` without a database. Where
an example deliberately raises from cleanup, it demonstrates a cleanup attempt,
not a successful release.

Run any script from the repository root with `uv run python <path>`. The following
outputs were captured from those scripts. Code blocks show each script's `main`
body; the linked script contains its complete setup.

## A per-call declaration must include cleanup

Omitting finalize fails when the declaration is constructed, before any call is served.

[Python](../../examples/step_17_connections/12_required_finalizer.py) · [Notebook](../../examples/step_17_connections/12_required_finalizer.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
try:
    PerCallConnection(factory=lambda: TraceResource([]))
except TypeError as error:
    assert "finalize" in str(error)
    print("TypeError: finalize is required")
else:
    raise AssertionError("Missing finalize was accepted")
```

Observed output:

```text
TypeError: finalize is required
```

Supply finalize=lambda resource: resource.close() when the resource owns a handle. Use an explicit harmless finalizer only when there is nothing to release.

## Registration rejects a non-callable finalizer

A present value is not enough: the adapter must be able to call finalize.

[Python](../../examples/step_17_connections/13_callable_finalizer.py) · [Notebook](../../examples/step_17_connections/13_callable_finalizer.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
try:
    validate_connection_entries({"db": PerCallConnection(lambda: TraceResource([]), finalize=None)})
except TypeError as error:
    assert str(error) == "PerCallConnection.finalize must be callable."
    print(str(error))
else:
    raise AssertionError("Non-callable finalize was accepted")
```

Observed output:

```text
PerCallConnection.finalize must be callable.
```

The route-record validation uses this check. It checks callability without running the factory or finalizer.

## A resource without open still has a finalizer

A resource may hold only Python data. Its per-call declaration still has to specify what happens when the call ends.

[Python](../../examples/step_17_connections/03_without_open.py) · [Notebook](../../examples/step_17_connections/03_without_open.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
@exclude_graph_model
class NoteResource(BaseResource):
    """Carry a note for one call."""
    def get_wrapper_class(self):
        """Allow direct use."""
        return None

events = []
declaration = PerCallConnection(NoteResource, lambda resource: events.append("finalize"))
async with connection_scope({"note": declaration}):
    events.append("use")
assert events == ["use", "finalize"]
print(events)
```

Observed output:

```text
['use', 'finalize']
```

No open method was called. The synchronous finalizer still ran after the body. BaseResource does not require open or close; the declaration supplies cleanup.

## A failed call still releases its resource

The body of the scope fails after acquisition. Watch the event order, then inspect the error outside the scope.

[Python](../../examples/step_17_connections/04_failed_call.py) · [Notebook](../../examples/step_17_connections/04_failed_call.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
declaration = PerCallConnection(lambda: TraceResource(events), lambda resource: resource.close())
try:
    async with connection_scope({"db": declaration}):
        events.append("use")
        raise ValueError("work failed")
except ValueError as error:
    print(type(error).__name__ + ": " + str(error))
assert events == ["open", "use", "close"]
print(events)
```

Observed output:

```text
ValueError: work failed
['open', 'use', 'close']
```

The finalizer ran before ValueError reached the caller. Releasing a resource does not mean that the work succeeded.

## Cancellation also runs cleanup

Cancellation asks an asynchronous task to stop. It is a separate exit path from a normal result or an ordinary exception.

[Python](../../examples/step_17_connections/05_cancelled_call.py) · [Notebook](../../examples/step_17_connections/05_cancelled_call.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
started = asyncio.Event()
async def work():
    """Wait until the caller cancels this task."""
    declaration = PerCallConnection(lambda: TraceResource(events), lambda resource: resource.close())
    async with connection_scope({"db": declaration}):
        started.set()
        await asyncio.Event().wait()
task = asyncio.create_task(work())
await started.wait()
task.cancel()
try:
    await task
except asyncio.CancelledError:
    print("CancelledError")
assert events == ["open", "close"]
print(events)
```

Observed output:

```text
CancelledError
['open', 'close']
```

The caller still receives CancelledError, but only after the finalizer has run. No delay or guessed scheduling interval is needed: the event ensures acquisition happened before cancellation.

## An earlier resource is cleaned up when a later factory fails

Two resources are declared. The first opens successfully; construction of the second fails before the operation starts.

[Python](../../examples/step_17_connections/06_factory_failure.py) · [Notebook](../../examples/step_17_connections/06_factory_failure.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
def fail_factory():
    """Fail before returning a resource."""
    raise ValueError("second factory failed")
try:
    async with connection_scope({
        "first": PerCallConnection(lambda: TraceResource(events), lambda resource: resource.close()),
        "second": PerCallConnection(fail_factory, lambda resource: events.append("unexpected")),
    }):
        raise AssertionError("The body must not run")
except ValueError as error:
    print(str(error))
assert events == ["open", "close"]
print(events)
```

Observed output:

```text
second factory failed
['open', 'close']
```

The first resource is not leaked. The second factory returned nothing, so there is no second resource to finalize.

## A resource whose open fails is finalized

Construction and acquisition are separate steps. A resource can exist even when opening it fails.

[Python](../../examples/step_17_connections/07_open_failure.py) · [Notebook](../../examples/step_17_connections/07_open_failure.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
@exclude_graph_model
class BrokenResource(TraceResource):
    """Fail while acquiring a connection."""
    async def open(self):
        """Report failed acquisition."""
        self.events.append("open failed")
        raise OSError("unavailable")
events = []
try:
    async with connection_scope({"db": PerCallConnection(
        lambda: BrokenResource(events), lambda resource: resource.close(),
    )}):
        raise AssertionError("The body must not run")
except OSError as error:
    print(str(error))
assert events == ["open failed", "close"]
print(events)
```

Observed output:

```text
unavailable
['open failed', 'close']
```

The finalizer must tolerate a partially opened resource. It is registered as soon as the factory returns, before open is awaited.

## Cleanup failure after successful work

The body succeeds, but its finalizer fails. A successful body does not make the entire call successful.

[Python](../../examples/step_17_connections/08_close_failure.py) · [Notebook](../../examples/step_17_connections/08_close_failure.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
try:
    async with connection_scope({"db": PerCallConnection(lambda: TraceResource(events), fail_close)}):
        events.append("use")
except OSError as error:
    print(type(error).__name__ + ": " + str(error))
assert events == ["open", "use", "close failed"]
print(events)
```

Observed output:

```text
OSError: release unavailable
['open', 'use', 'close failed']
```

With no earlier error to preserve, the closing error propagates out of the scope. This example reports an attempted release, not a successful release.

## A closing failure does not hide the work failure

Both the body and cleanup fail. The scope preserves the work error and attaches the operational closing error as a Python exception note.

[Python](../../examples/step_17_connections/09_two_failures.py) · [Notebook](../../examples/step_17_connections/09_two_failures.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
try:
    async with connection_scope({"db": PerCallConnection(lambda: TraceResource(events), fail_close)}):
        raise ValueError("work failed")
except ValueError as error:
    assert "release unavailable" in error.__notes__[0]
    print(type(error).__name__ + ": " + str(error))
    print(error.__notes__[0])
assert events == ["open", "close failed"]
```

Observed output:

```text
ValueError: work failed
a closing failure was recorded: OSError('release unavailable')
```

Inspect __notes__ when diagnosing this path. A resource contract violation follows a different precedence rule, demonstrated with an unfinished transaction on the PostgreSQL page.

## One failed finalizer does not skip the rest

Cleanup tries every created resource even when the first finalizer raises.

[Python](../../examples/step_17_connections/10_remaining_finalizers.py) · [Notebook](../../examples/step_17_connections/10_remaining_finalizers.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
try:
    async with connection_scope({
        "first": PerCallConnection(lambda: TraceResource(events), fail_close),
        "second": PerCallConnection(lambda: TraceResource(events), lambda resource: resource.close()),
    }):
        pass
except OSError:
    pass
assert events == ["open", "open", "close failed", "close"]
print(events)
```

Observed output:

```text
['open', 'open', 'close failed', 'close']
```

The last close belongs to the second resource. Cleanup does not stop at the first failure; resources that opened successfully are finalized first, in declaration order.

## A factory can return the same object

PerCallConnection calls the factory every time. It cannot guarantee that the factory creates a new resource.

[Python](../../examples/step_17_connections/11_shared_factory.py) · [Notebook](../../examples/step_17_connections/11_shared_factory.ipynb)

The following is the body of `main()` from the standalone example; the linked files include every definition and import.

```python
events = []
shared = TraceResource(events)
declaration = PerCallConnection(lambda: shared, lambda resource: resource.close())
for _ in range(2):
    async with connection_scope({"db": declaration}) as connections:
        assert connections["db"] is shared
assert events == ["open", "close", "open", "close"]
print("same object: True")
print(events)
```

Observed output:

```text
same object: True
['open', 'close', 'open', 'close']
```

This is a counterexample, not the recommended database configuration. Two calls applied their own lifecycle to the same object. Construct a new connection-owning resource inside the factory.

## Which error leaves the scope?

A **contract violation** reports a misuse of a resource, such as closing a transaction
without ending it. An **operational failure** reports an inability to perform cleanup,
such as a failed release. The distinction determines which error is primary.

| Work outcome | Cleanup outcome | Caller observes |
| --- | --- | --- |
| Success | Success | Result |
| Failure | Success | Work error |
| Success | Operational failure | Closing error |
| Failure | Operational failure | Work error, with a closing note |
| Success or failure | `ResourceContractViolationError` | Violation; any work error is its cause |
| Cancellation | Failure or violation | `CancelledError`, with a closing note |

All finalizers are attempted. If several fail, the current implementation retains
the first contract violation and the first operational failure; the precedence
above selects what is raised. It does not aggregate every failure. Resources opened
successfully are finalized first, then created resources that never finished opening,
in declaration order within each group.

The PostgreSQL examples demonstrate the exceptional precedence with real
`TransactionLeftOpenError`: [unfinished transaction](../extensions/postgresql.md#closing-with-a-transaction-open),
[work failure](../../examples/extensions/postgresql/12_contract_precedence.ipynb),
and [cancellation](../../examples/extensions/postgresql/13_cancel_precedence.ipynb).
These are exceptions observed at the scope boundary. An HTTP or MCP client receives
the adapter's response format, not these Python exception objects.
