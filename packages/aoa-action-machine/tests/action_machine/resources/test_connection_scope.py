# tests/action_machine/resources/test_connection_scope.py
"""
The per-call lifecycle: open what this call created, and finalize it exactly once.

A per-call declaration is a pair — a ``factory`` that creates the resource and a
``finalize`` that closes it. ``connection_scope`` is the half the boundary owns:
it walks the declaration, opens what has something to open, hands the run the
mapping it expects, and finalizes on every path out.

The three rules that are easy to get wrong, and that this module pins:

* a **ready** resource is passed through untouched — the scope opens and closes
  only what a per-call declaration created;
* a finalizer runs **exactly once** on success, on exception and on cancellation,
  and the connection is already back when one of them raises;
* a **contract violation** raised while finalizing is the error the caller sees,
  with the run's error as its cause, while an **operational** closing failure
  keeps the old precedence — and a cancellation still wins over both.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    connection_scope(declaration)
        │  ready resource  -> untouched
        │  PerCallConnection -> factory(), then open() if it has one
        v
      block runs
        │
      finally: finalize() once per created resource, opened ones first

"""

from __future__ import annotations

import asyncio

import pytest

from aoa.action_machine.exceptions.transaction_left_open_error import TransactionLeftOpenError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.connection_scope import connection_scope
from aoa.action_machine.resources.per_call_connection import PerCallConnection

WAIT = 2.0


class BoomError(RuntimeError):
    """What the run raises in the tests that need a failing run."""


class ClosingError(RuntimeError):
    """What an operational closing failure raises."""


class FactoryError(RuntimeError):
    """What a factory raises in the test that needs a failing factory."""


@exclude_graph_model
class _LoggedResource(BaseResource):
    """A resource with a lifecycle that records what the scope did to it.

    Excluded from the interchange graph like every framework resource: it is a test
    double with no domain, and a bare ``BaseResource`` subclass would otherwise make
    every machine built in the same session fail on ``MissingMetaError``.
    """

    def __init__(self, log: list[str], name: str = "res") -> None:
        self.log = log
        self.name = name

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """This test double needs no nested-action proxy."""
        return None

    async def open(self) -> None:
        """Record being opened."""
        self.log.append(f"{self.name}:open")

    async def close(self) -> None:
        """Record being closed."""
        self.log.append(f"{self.name}:close")


@exclude_graph_model
class _LifecyclelessResource(BaseResource):
    """A resource with nothing to open and nothing to close on its own."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """This test double needs no nested-action proxy."""
        return None


def _pair(resource: BaseResource, log: list[str] | None = None):
    """Declare a per-call resource whose finalizer closes it."""
    return PerCallConnection(
        factory=lambda: resource,
        finalize=lambda res: res.close(),  # type: ignore[attr-defined]
    )


async def test_finalize_runs_exactly_once_on_success() -> None:
    """Open before the run, finalize after it — once, and in that order."""
    log: list[str] = []
    resource = _LoggedResource(log)

    async with connection_scope({"ledger": _pair(resource)}) as connections:
        assert connections == {"ledger": resource}
        log.append("run")

    assert log == ["res:open", "run", "res:close"]


async def test_a_ready_resource_is_passed_through_and_never_touched() -> None:
    """What the lifetime supplied is not the scope's to open or to close."""
    log: list[str] = []
    ready = _LoggedResource(log, "ready")

    async with connection_scope({"svc": ready}) as connections:
        assert connections == {"svc": ready}
        log.append("run")

    assert log == ["run"]


async def test_no_declaration_yields_nothing() -> None:
    """An absent or empty declaration is what the machine already expects: nothing."""
    async with connection_scope(None) as connections:
        assert connections is None
    async with connection_scope({}) as connections:
        assert connections is None


async def test_the_run_raising_does_not_stop_finalization() -> None:
    """A run that fails is still a path out: the resource is closed."""
    log: list[str] = []
    resource = _LoggedResource(log)

    with pytest.raises(BoomError):
        async with connection_scope({"ledger": _pair(resource)}):
            raise BoomError("run failed")

    assert log == ["res:open", "res:close"]


async def test_a_resource_without_open_is_not_opened_but_is_finalized() -> None:
    """The scope opens only what has something to open; it still finalizes."""
    log: list[str] = []
    resource = _LifecyclelessResource()

    async with connection_scope(
        {"cache": PerCallConnection(lambda: resource, finalize=lambda res: log.append("finalized"))}
    ):
        log.append("run")

    assert log == ["run", "finalized"]


async def test_a_failing_factory_leaves_the_earlier_resources_finalized() -> None:
    """Resources created before a later factory fails are not lost — they are finalized."""
    log: list[str] = []
    first = _LoggedResource(log, "first")

    def failing_factory() -> BaseResource:
        raise FactoryError("cannot build the second resource")

    with pytest.raises(FactoryError):
        async with connection_scope(
            {
                "first": _pair(first),
                "second": PerCallConnection(failing_factory, finalize=lambda res: None),
            }
        ):
            log.append("run")  # must never be reached

    assert log == ["first:open", "first:close"]


async def test_every_remaining_finalizer_runs_after_one_raises() -> None:
    """One failing finalizer does not strand the others."""
    log: list[str] = []
    first = _LoggedResource(log, "first")
    second = _LoggedResource(log, "second")

    async def failing_finalize(resource: BaseResource) -> None:
        raise ClosingError("release failed")

    with pytest.raises(ClosingError):
        async with connection_scope(
            {
                "first": PerCallConnection(lambda: first, finalize=failing_finalize),
                "second": _pair(second),
            }
        ):
            log.append("run")

    assert log == ["first:open", "second:open", "run", "second:close"]


async def test_an_operational_closing_failure_is_recorded_when_the_run_failed() -> None:
    """The run's error is what the caller sees; the closing failure is recorded beside it."""
    log: list[str] = []
    resource = _LoggedResource(log)

    async def failing_finalize(res: BaseResource) -> None:
        raise ClosingError("release failed")

    with pytest.raises(BoomError) as caught:
        async with connection_scope({"ledger": PerCallConnection(lambda: resource, finalize=failing_finalize)}):
            raise BoomError("run failed")

    notes = getattr(caught.value, "__notes__", [])
    assert any("ClosingError" in note for note in notes), notes


async def test_a_contract_violation_outranks_the_run_error() -> None:
    """The violation is raised, the run's error becomes its cause, and it is never a note."""
    log: list[str] = []
    resource = _LoggedResource(log)
    violation = TransactionLeftOpenError("the resource was closed with a transaction still open")

    async def finalize(res: BaseResource) -> None:
        raise violation

    with pytest.raises(TransactionLeftOpenError) as caught:
        async with connection_scope({"ledger": PerCallConnection(lambda: resource, finalize=finalize)}):
            raise BoomError("run failed")

    assert caught.value is violation
    assert isinstance(caught.value.__cause__, BoomError)
    assert not getattr(caught.value, "__notes__", [])


async def test_a_contract_violation_surfaces_on_a_clean_run() -> None:
    """A clean run does not hide it either."""
    log: list[str] = []
    resource = _LoggedResource(log)

    async def finalize(res: BaseResource) -> None:
        raise TransactionLeftOpenError("left open")

    with pytest.raises(TransactionLeftOpenError):
        async with connection_scope({"ledger": PerCallConnection(lambda: resource, finalize=finalize)}):
            log.append("run")

    assert log == ["res:open", "run"]


async def test_cancellation_runs_the_finalizer_and_propagates() -> None:
    """A cancelled call is a path out too: the release completes, then the cancellation goes on."""
    log: list[str] = []
    resource = _LoggedResource(log)
    inside = asyncio.Event()

    async def finalize(res: BaseResource) -> None:
        await asyncio.sleep(0.01)  # a real release takes an await
        await res.close()  # type: ignore[attr-defined]

    async def body() -> None:
        async with connection_scope({"ledger": PerCallConnection(lambda: resource, finalize=finalize)}):
            inside.set()
            await asyncio.Event().wait()  # never set: the test cancels the task

    task = asyncio.create_task(body())
    await asyncio.wait_for(inside.wait(), timeout=WAIT)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert log == ["res:open", "res:close"]


async def test_cancellation_wins_over_a_contract_violation() -> None:
    """The cancellation propagates; the violation is recorded beside it."""
    log: list[str] = []
    resource = _LoggedResource(log)
    inside = asyncio.Event()

    async def finalize(res: BaseResource) -> None:
        await asyncio.sleep(0.01)
        raise TransactionLeftOpenError("left open")

    async def body() -> None:
        async with connection_scope({"ledger": PerCallConnection(lambda: resource, finalize=finalize)}):
            inside.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(body())
    await asyncio.wait_for(inside.wait(), timeout=WAIT)
    task.cancel()

    with pytest.raises(asyncio.CancelledError) as caught:
        await task

    notes = getattr(caught.value, "__notes__", [])
    assert any("TransactionLeftOpenError" in note for note in notes), notes
