# packages/aoa-examples/aoa_examples_tests/test_store_ocel_export.py
"""StoreDomain OCEL export — single trace smoke via ``ActionProductMachine``."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aoa.action_machine.context import Context, RequestInfo

# Completes coordinator/runtime imports before ``Context`` (avoids cycles when this tree is collected alone).
from aoa.action_machine.testing import TestBench  # noqa: F401  # pylint: disable=unused-import
from aoa.examples.model.store.actions import PublishOrderCreatedOcelAction, RecordOrderOcelAction
from aoa.examples.model.store.actions.store_ocel_traces import STORE_OCEL_CONNECTION_KEY
from aoa.examples.model.store.ocel_export import build_store_ocel_machine
from tests.ocel.pm4py_validation import assert_ocel2_pm4py_smoke


def _ctx_with_trace() -> Context:
    return Context(
        request=RequestInfo(
            trace_id="store-ocel-trace",
            request_timestamp=datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC),
        ),
    )


@pytest.mark.asyncio
async def test_publish_order_created_ocel_writes_json(tmp_path: Path) -> None:
    assert RecordOrderOcelAction is PublishOrderCreatedOcelAction

    output = tmp_path / "store.ocel.json"
    machine, store = build_store_ocel_machine(output)
    await store.open()

    result = await machine.run(
        _ctx_with_trace(),
        PublishOrderCreatedOcelAction(),
        PublishOrderCreatedOcelAction.Params(order_id="ord-42", customer_id="cust-42"),
        connections={STORE_OCEL_CONNECTION_KEY: store},
    )
    await store.close()

    assert result.order_id == "ord-42"
    assert result.trace_id == "store-ocel-trace"
    assert result.lifecycle_step == "created"
    assert output.exists()

    assert_ocel2_pm4py_smoke(
        output,
        expected_event_count=1,
        expected_object_count=2,
        expected_event_id="store-ocel-trace",
        expected_qualifiers={"Created order", "Created order.customer"},
    )

    doc = json.loads(output.read_text(encoding="utf-8"))
    assert doc["events"][0]["attributes"][0]["name"] == "payment_status"
