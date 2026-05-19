# tests/ocel/contracts/test_ocel_frame.py
"""OcelFrame contract (plan §5.26)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from aoa.ocel import OcelFrame
from tests.action_machine.scenarios.domain_model.entities import SampleEntity


def test_ocel_frame_holds_entity() -> None:
    entity = SampleEntity(id="1", name="A", value=1)
    frame = OcelFrame(object=entity)
    assert frame.object is entity


def test_ocel_frame_is_frozen() -> None:
    frame = OcelFrame(object=SampleEntity(id="1", name="A", value=1))
    with pytest.raises(FrozenInstanceError):
        frame.object = SampleEntity(id="2", name="B", value=2)  # type: ignore[misc]


def test_isinstance_for_pipeline_discovery() -> None:
    frame = OcelFrame(object=SampleEntity(id="1", name="A", value=1))
    assert isinstance(frame, OcelFrame)
