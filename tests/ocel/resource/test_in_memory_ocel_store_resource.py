# tests/ocel/resource/test_in_memory_ocel_store_resource.py
"""InMemoryOcelStoreResource (plan §5.27, §5.29)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aoa.action_machine.exceptions.connection_already_open_error import (
    ConnectionAlreadyOpenError,
)
from aoa.action_machine.plugin.ocel.dto.ocel_attribute import OcelAttribute
from aoa.action_machine.plugin.ocel.dto.ocel_event import OcelEvent
from aoa.action_machine.plugin.ocel.dto.ocel_object import OcelObject
from aoa.action_machine.plugin.ocel.dto.ocel_object_ref import OcelObjectRef
from aoa.action_machine.plugin.ocel.exceptions import OcelContractError
from aoa.action_machine.plugin.ocel.resource import InMemoryOcelStoreResource


@pytest.fixture
def event_time() -> datetime:
    return datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)


def _sample_event(event_time: datetime, event_id: str = "trace-001") -> OcelEvent:
    obj = OcelObject(
        id="aoa.shop.domain.order.OrderEntity:id=order_1",
        type="aoa.shop.domain.order.OrderEntity",
        attributes=[OcelAttribute(name="id", value="order_1")],
    )
    return OcelEvent(
        id=event_id,
        type="aoa.shop.actions.CreateOrderAction",
        time=event_time,
        attributes=[OcelAttribute(name="domain", value="shop")],
        relationships=[OcelObjectRef(object_id=obj.id, qualifier=obj.type)],
        objects=[obj],
    )


async def _run(resource: InMemoryOcelStoreResource, event: OcelEvent) -> None:
    await resource.open()
    await resource.add_event(event)
    await resource.close()


def test_close_writes_ocel_json(tmp_path: Path, event_time: datetime) -> None:
    output = tmp_path / "out.ocel.json"
    resource = InMemoryOcelStoreResource(output_file=output)
    asyncio.run(_run(resource, _sample_event(event_time)))

    doc = json.loads(output.read_text(encoding="utf-8"))
    assert set(doc) == {"eventTypes", "objectTypes", "events", "objects"}
    assert doc["events"][0]["id"] == "trace-001"
    assert doc["objects"][0]["id"].startswith("aoa.shop.domain.order.OrderEntity:")


def test_duplicate_event_id_raises(tmp_path: Path, event_time: datetime) -> None:
    output = tmp_path / "dup.ocel.json"
    resource = InMemoryOcelStoreResource(output_file=output)

    async def _add_twice() -> None:
        await resource.open()
        ev = _sample_event(event_time)
        await resource.add_event(ev)
        with pytest.raises(OcelContractError, match=r"Duplicate OcelEvent\.id:"):
            await resource.add_event(ev)

    asyncio.run(_add_twice())


def test_add_event_when_closed_raises(tmp_path: Path, event_time: datetime) -> None:
    resource = InMemoryOcelStoreResource(output_file=tmp_path / "closed.ocel.json")

    async def _add_closed() -> None:
        with pytest.raises(OcelContractError, match="Resource is not open"):
            await resource.add_event(_sample_event(event_time))

    asyncio.run(_add_closed())


def test_double_open_raises(tmp_path: Path) -> None:
    resource = InMemoryOcelStoreResource(output_file=tmp_path / "open.ocel.json")

    async def _double() -> None:
        await resource.open()
        with pytest.raises(ConnectionAlreadyOpenError):
            await resource.open()

    asyncio.run(_double())


def test_distinct_object_ids_for_same_pk_different_types(
    tmp_path: Path, event_time: datetime
) -> None:
    output = tmp_path / "types.ocel.json"
    obj_a = OcelObject(
        id="pkg.A.Entity:id=x",
        type="pkg.A.Entity",
        attributes=[OcelAttribute(name="id", value="x")],
    )
    obj_b = OcelObject(
        id="pkg.B.Entity:id=x",
        type="pkg.B.Entity",
        attributes=[OcelAttribute(name="id", value="x")],
    )
    ev = OcelEvent(
        id="trace-types",
        type="pkg.Action",
        time=event_time,
        objects=[obj_a, obj_b],
    )
    resource = InMemoryOcelStoreResource(output_file=output)
    asyncio.run(_run(resource, ev))
    doc = json.loads(output.read_text(encoding="utf-8"))
    ids = {o["id"] for o in doc["objects"]}
    assert ids == {"pkg.A.Entity:id=x", "pkg.B.Entity:id=x"}
