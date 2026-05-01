# tests/domain/test_testing.py
"""
Tests for `action_machine.domain.testing.make`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers heuristic defaults for primitive fields and merge behavior with overrides.

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

`make()` is a **test helper** — not used in production pipelines. It does not
replace real fixtures or exhaustive field generation for every entity shape.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from action_machine.domain import BaseEntity, Lifecycle
from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.testing import make
from action_machine.intents.entity import entity
from tests.scenarios.domain_model.entities import SampleEntity


def test_make_generates_primitive_defaults() -> None:
    entity = make(SampleEntity)
    assert entity.id == "test_id"
    assert entity.name == "test_name"
    assert entity.value == 1


def test_make_overrides_merge() -> None:
    entity = make(SampleEntity, id="custom", value=42)
    assert entity.id == "custom"
    assert entity.name == "test_name"
    assert entity.value == 42


class _TestDomain(BaseDomain):
    name = "td"
    description = "test domain for make()"


@entity(description="float default", domain=_TestDomain)
class _FloatDefaultEntity(BaseEntity):
    id: str = Field()
    amount: float = Field(ge=0)


def test_make_float_default() -> None:
    entity = make(_FloatDefaultEntity, id="f1")
    assert entity.amount == 1.0


@entity(description="e", domain=_TestDomain)
class _LifecycleGetterEntity(BaseEntity):
    id: str = Field()
    state: Lifecycle = Field()

    @classmethod
    def get_state(cls) -> Lifecycle:
        raise RuntimeError("getter failed")


def test_make_swallows_exception_from_lifecycle_getter() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        make(_LifecycleGetterEntity, id="1")
