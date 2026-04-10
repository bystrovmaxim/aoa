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

from action_machine.domain.testing import make
from tests.domain_model.entities import SampleEntity


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
