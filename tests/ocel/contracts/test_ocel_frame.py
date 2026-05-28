# tests/ocel/contracts/test_ocel_frame.py
"""OcelFrame contract (plan §5.26)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from tests.action_machine.scenarios.domain_model.entities import SampleEntity

from aoa.action_machine.plugin.ocel import OcelFrame
from aoa.action_machine.plugin.ocel.dto import OcelAttribute
from aoa.action_machine.plugin.ocel.exceptions import OcelContractError


def test_ocel_frame_holds_entity() -> None:
    entity = SampleEntity(id="1", name="A", value=1)
    frame = OcelFrame(object=entity, qualifier="Primary entity")
    assert frame.object is entity
    assert frame.qualifier == "Primary entity"
    assert frame.attributes == []


def test_ocel_frame_is_frozen() -> None:
    frame = OcelFrame(
        object=SampleEntity(id="1", name="A", value=1),
        qualifier="Primary entity",
    )
    with pytest.raises(FrozenInstanceError):
        frame.object = SampleEntity(id="2", name="B", value=2)  # type: ignore[misc]


def test_empty_qualifier_raises() -> None:
    with pytest.raises(OcelContractError, match="qualifier must be non-empty"):
        OcelFrame(object=SampleEntity(id="1", name="A", value=1), qualifier="   ")


def test_attributes_optional() -> None:
    frame = OcelFrame(
        object=SampleEntity(id="1", name="A", value=1),
        qualifier="Primary entity",
        attributes=[OcelAttribute(name="domain", value="shop")],
    )
    assert frame.attributes[0].name == "domain"
