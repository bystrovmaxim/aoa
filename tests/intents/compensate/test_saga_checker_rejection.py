# tests/intents/compensate/test_saga_checker_rejection.py
"""Saga frames when a regular aspect returns but result checkers reject."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from action_machine.exceptions import ValidationFieldError
from action_machine.testing import TestBench
from tests.scenarios.domain_model.compensate_actions import (
    CheckerRejectionSagaAction,
    CompensateTestParams,
)
from tests.scenarios.domain_model.compensate_plugins import SagaObserverPlugin
from tests.scenarios.domain_model.services import (
    PaymentServiceResource,
    SagaCompensateTraceService,
    SagaCompensateTraceServiceResource,
)


@pytest.fixture
def saga_observer() -> SagaObserverPlugin:
    observer = SagaObserverPlugin()
    observer.reset()
    return observer


@pytest.fixture
def mock_trace() -> AsyncMock:
    return AsyncMock(spec=SagaCompensateTraceService)


@pytest.fixture
def checker_reject_bench(
    mock_payment: AsyncMock,
    mock_trace: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> TestBench:
    return TestBench(
        mocks={
            PaymentServiceResource: PaymentServiceResource(mock_payment),
            SagaCompensateTraceServiceResource: SagaCompensateTraceServiceResource(mock_trace),
        },
        plugins=[saga_observer],
        log_coordinator=AsyncMock(),
    )


def _events_since_last_saga_start(observer: SagaObserverPlugin) -> list[dict]:
    events = observer.collected_events
    last_start = -1
    for i, e in enumerate(events):
        if e["event_type"] == "SagaRollbackStartedEvent":
            last_start = i
    if last_start == -1:
        return events
    return events[last_start:]


@pytest.mark.anyio
async def test_saga_checker_rejection_compensate_order(
    checker_reject_bench: TestBench,
    mock_payment: AsyncMock,
    mock_trace: AsyncMock,
    saga_observer: SagaObserverPlugin,
) -> None:
    """Second aspect fails checkers after the frame has merged state_after."""
    params = CompensateTestParams(
        user_id="u_checker_saga",
        amount=10.0,
        item_id="ITEM-CHK",
        should_fail=False,
    )

    with pytest.raises(ValidationFieldError):
        await checker_reject_bench.run(
            CheckerRejectionSagaAction(),
            params,
            rollup=False,
        )

    # ``TestBench.run`` stops on the first machine when the pipeline raises.
    assert mock_trace.record_second_rollback.await_count == 1
    assert mock_trace.record_second_rollback.await_args.kwargs["state_after_none"] is False

    assert mock_payment.refund.await_count == 1

    slice_events = _events_since_last_saga_start(saga_observer)
    started = next(e for e in slice_events if e["event_type"] == "SagaRollbackStartedEvent")
    assert started["stack_depth"] == 2
    assert started["aspect_names"] == ["second_aspect", "first_aspect"]

    before = [e for e in slice_events if e["event_type"] == "BeforeCompensateAspectEvent"]
    assert [e["aspect_name"] for e in before] == ["second_aspect", "first_aspect"]

    completed = next(
        e for e in slice_events if e["event_type"] == "SagaRollbackCompletedEvent"
    )
    assert completed["succeeded"] == 2
    assert completed["failed"] == 0
