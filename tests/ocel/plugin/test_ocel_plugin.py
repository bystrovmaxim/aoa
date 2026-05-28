# tests/ocel/plugin/test_ocel_plugin.py
"""OcelPlugin — frame collection and OcelEvent assembly."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from unittest.mock import MagicMock

import pytest
from pydantic import Field
from tests.action_machine.scenarios.domain_model.entities import (
    SampleEntity,
    TestDomain,
)

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.on import GlobalFinishEvent
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_schema import BaseSchema
from aoa.action_machine.plugin.ocel import OcelFrame
from aoa.action_machine.plugin.ocel.dto import OcelAttribute
from aoa.action_machine.plugin.ocel.exceptions import OcelContractError
from aoa.action_machine.plugin.ocel.plugin import OCEL_FRAMES_KEY, OcelPlugin
from aoa.action_machine.plugin.ocel.plugin.ocel_plugin import collect_ocel_frames
from aoa.action_machine.plugin.ocel.resource import InMemoryOcelStoreResource


class _Params(BaseParams):
    pass


class _Result(BaseSchema):
    pass


class _Action:
    __module__ = "tests.actions"
    __qualname__ = "SampleAction"


@pytest.fixture
def event_time() -> datetime:
    return datetime(2026, 5, 19, 12, 0, 0, tzinfo=UTC)


def _finish_event(
    event_time: datetime,
    *,
    snapshots: tuple[dict[str, object], ...] = (),
) -> GlobalFinishEvent:
    context = MagicMock()
    context.request.trace_id = "trace-001"
    context.request.request_timestamp = event_time
    return GlobalFinishEvent(
        action_class=_Action,
        action_name="sample_action",
        nest_level=0,
        context=context,
        params=_Params(),
        result=_Result(),
        duration_ms=1.0,
        all_aspect_states=snapshots,
    )


def test_collect_ocel_frames_uses_finish_event_snapshots() -> None:
    entity = SampleEntity(id="1", name="A", value=1)
    frame = OcelFrame(object=entity, qualifier="Primary")
    event = _finish_event(
        datetime.now(UTC),
        snapshots=({OCEL_FRAMES_KEY: [frame]},),
    )
    collected = collect_ocel_frames(event)
    assert len(collected) == 1
    assert collected[0].qualifier == "Primary"


def test_collect_ocel_frames_from_key_and_direct_value() -> None:
    entity = SampleEntity(id="1", name="A", value=1)
    frame = OcelFrame(object=entity, qualifier="Primary")
    payload = {
        OCEL_FRAMES_KEY: [frame],
        "other": OcelFrame(object=entity, qualifier="Secondary"),
    }
    collected = collect_ocel_frames(payload)
    assert len(collected) == 2


def test_merge_event_attributes_name_conflict_raises() -> None:
    entity = SampleEntity(id="1", name="A", value=1)
    plugin = OcelPlugin(store=MagicMock())
    frames = [
        OcelFrame(
            object=entity,
            qualifier="A",
            attributes=[OcelAttribute(name="domain", value="shop")],
        ),
        OcelFrame(
            object=entity,
            qualifier="B",
            attributes=[OcelAttribute(name="domain", value="billing")],
        ),
    ]
    with pytest.raises(OcelContractError, match="Conflicting OcelEvent attribute 'domain'"):
        plugin._merge_event_attributes(frames)


def test_build_ocel_event_root_only(event_time: datetime) -> None:
    entity = SampleEntity(id="1", name="A", value=1)
    frame = OcelFrame(
        object=entity,
        qualifier="Created sample",
        attributes=[OcelAttribute(name="channel", value="api")],
    )
    plugin = OcelPlugin(store=MagicMock())
    ocel_event = plugin.build_ocel_event([frame], _finish_event(event_time))

    assert ocel_event.id == "trace-001"
    assert ocel_event.type == "tests.actions.SampleAction"
    assert ocel_event.time == event_time
    assert len(ocel_event.relationships) == 1
    assert ocel_event.relationships[0].qualifier == "Created sample"
    assert len(ocel_event.objects) == 1


def test_build_ocel_event_one_hop_loaded_relation(event_time: datetime) -> None:
    @entity(description="Policy", domain=TestDomain)
    class PolicyEntity(BaseEntity):
        id: str = Field(description="id")
        code: str = Field(description="code")

    @entity(description="Child", domain=TestDomain)
    class ChildEntity(BaseEntity):
        id: str = Field(description="id")
        policy: Annotated[
            AssociationOne[PolicyEntity] | None,
            NoInverse(),
        ] = Rel(description="Policy")  # type: ignore[assignment]

    policy = PolicyEntity(id="pol-9", code="P9")
    child = ChildEntity(id="c1", policy=AssociationOne(id="pol-9", entity=policy))
    frame = OcelFrame(object=child, qualifier="Signed prescription")
    plugin = OcelPlugin(store=MagicMock())
    ocel_event = plugin.build_ocel_event([frame], _finish_event(event_time))

    qualifiers = {ref.qualifier for ref in ocel_event.relationships}
    assert qualifiers == {
        "Signed prescription",
        "Signed prescription.policy",
    }
    assert len(ocel_event.objects) == 2


def test_build_ocel_event_short_names(event_time: datetime) -> None:
    class SampleAction:
        __module__ = "tests.actions"

    entity = SampleEntity(id="1", name="A", value=1)
    frame = OcelFrame(object=entity, qualifier="Created sample")
    plugin = OcelPlugin(store=MagicMock(), short_names=True)
    finish = _finish_event(event_time)
    finish = GlobalFinishEvent(
        action_class=SampleAction,
        action_name=finish.action_name,
        nest_level=finish.nest_level,
        context=finish.context,
        params=finish.params,
        result=finish.result,
        duration_ms=finish.duration_ms,
        all_aspect_states=finish.all_aspect_states,
    )
    ocel_event = plugin.build_ocel_event([frame], finish)

    assert ocel_event.type == "Sample"
    assert ocel_event.objects[0].type == "Sample"


@pytest.mark.asyncio
async def test_on_export_reads_finish_snapshots(tmp_path, event_time: datetime) -> None:
    output = tmp_path / "plugin.ocel.json"
    store = InMemoryOcelStoreResource(output_file=output)
    await store.open()
    plugin = OcelPlugin(store=store)
    entity = SampleEntity(id="1", name="A", value=1)
    frame = OcelFrame(object=entity, qualifier="Created sample")
    event = _finish_event(
        event_time,
        snapshots=({OCEL_FRAMES_KEY: [frame]},),
    )
    state: dict[str, object] = {}
    await plugin.on_export_ocel(state, event, log=MagicMock())
    await store.close()
    assert state == {}
    assert output.exists()
