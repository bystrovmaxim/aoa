# tests/ocel/test_type_id.py
"""Short OCEL type prefixes and object IDs."""

from __future__ import annotations

from tests.action_machine.scenarios.domain_model.entities import SampleEntity

from aoa.action_machine.plugin.ocel.type_id import make_oid


class _SameShortNameA:
    pass


class _SameShortNameB:
    pass


def test_prefix_stable_per_type() -> None:
    a = make_oid(SampleEntity)
    b = make_oid(SampleEntity(id="1", name="n", value=1))
    assert a == b
    assert len(a) == 8


def test_prefix_differs_for_different_full_names() -> None:
    p_a = make_oid(_SameShortNameA)
    p_b = make_oid(_SameShortNameB)
    assert p_a != p_b
    assert p_a[:4] == p_b[:4] == "_sam"


def test_make_oid_with_original_id() -> None:
    entity = SampleEntity(id="1", name="A", value=1)
    prefix = make_oid(entity)
    assert make_oid(entity, "order_1") == f"{prefix}_order_1"
    assert make_oid(entity, 123) == f"{prefix}_123"
