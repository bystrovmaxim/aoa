# tests/ocel/test_ocel_pm4py_smoke.py
"""PM4Py smoke — ``read_ocel2_json`` accepts ``InMemoryOcelStoreResource`` output."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tests.ocel.pm4py_validation import assert_ocel2_pm4py_smoke

from aoa.action_machine.plugin.ocel.dto.ocel_attribute import OcelAttribute
from aoa.action_machine.plugin.ocel.dto.ocel_event import OcelEvent
from aoa.action_machine.plugin.ocel.dto.ocel_object import OcelObject
from aoa.action_machine.plugin.ocel.dto.ocel_object_ref import OcelObjectRef
from aoa.action_machine.plugin.ocel.resource import InMemoryOcelStoreResource


@pytest.fixture
def event_time() -> datetime:
    return datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)


def test_in_memory_export_loads_in_pm4py(tmp_path: Path, event_time: datetime) -> None:
    output = tmp_path / "pm4py-smoke.ocel.json"
    obj = OcelObject(
        id="aoa.shop.domain.order.OrderEntity:id=order_1",
        type="aoa.shop.domain.order.OrderEntity",
        attributes=[OcelAttribute(name="id", value="order_1")],
    )
    event = OcelEvent(
        id="trace-pm4py-001",
        type="aoa.shop.actions.CreateOrderAction",
        time=event_time,
        attributes=[OcelAttribute(name="domain", value="shop")],
        relationships=[OcelObjectRef(object_id=obj.id, qualifier="Created order")],
        objects=[obj],
    )

    async def _write() -> None:
        resource = InMemoryOcelStoreResource(output_file=output)
        await resource.open()
        await resource.add_event(event)
        await resource.close()

    asyncio.run(_write())

    assert_ocel2_pm4py_smoke(
        output,
        expected_event_count=1,
        expected_object_count=1,
        expected_event_id="trace-pm4py-001",
        expected_qualifiers={"Created order"},
    )
