# packages/aoa-action-machine/tests/action_machine/graph/test_field_type_label.py
"""
field_type_label — every rule of spec 029, FR-030, and the full annotation beside it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One case per row of the rule's table; the label is idempotent on the names it makes;
an ``EntityField`` vertex ships the clean label as ``field_type`` and the full
annotation as ``field_annotation``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    annotation ──field_type_label──► label     EntityFieldGraphNode ──to_dict──► properties
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

import pytest

from aoa.action_machine.domain.relation_containers import AggregateMany, AssociationOne, CompositeOne
from aoa.action_machine.domain.specialization_containers import Generalization, Specialization
from aoa.action_machine.graph.field_type_label import field_type_label
from aoa.action_machine.graph.nodes.entity_field_graph_node import EntityFieldGraphNode
from tests.action_machine.graph.test_entity_specialization_graph import (
    _FirstSpecEntity,
    _HeadCoreEntity,
    _HeadKindEnumEntity,
    _SecondSpecEntity,
)


class _Plain:
    """A plain class, as a field type."""


@pytest.mark.parametrize(
    ("annotation", "label"),
    [
        (str, "str"),
        (int, "int"),
        (_Plain, "_Plain"),
        (str | None, "str | None"),
        (Optional[str], "str | None"),  # noqa: UP045 — the old spelling is the case under test
        (Union[str, None], "str | None"),  # noqa: UP007 — the old spelling is the case under test
        (None | int, "int | None"),
        (int | str, "int | str"),
        (AssociationOne[_Plain], "_Plain"),
        (CompositeOne[_Plain], "_Plain"),
        (AggregateMany[_Plain], "_Plain[]"),
        (AssociationOne[_Plain] | None, "_Plain | None"),
        (Generalization[_HeadCoreEntity], "_HeadCoreEntity"),
        (Specialization[_FirstSpecEntity | _SecondSpecEntity, _HeadKindEnumEntity], "_FirstSpecEntity | _SecondSpecEntity"),
        (list[str], "str[]"),
        (set[int], "int[]"),
        (frozenset[str], "str[]"),
        (tuple[int, ...], "int[]"),
        (tuple[int, str], "tuple[int, str]"),
        (dict[str, int], "dict[str, int]"),
        (Literal["a", "b"], '"a" | "b"'),
        (Literal[1, 2], "1 | 2"),
        (Annotated[str, "meta"], "str"),
        (Annotated[str | None, "meta"], "str | None"),
    ],
)
def test_every_rule_of_the_table(annotation: Any, label: str) -> None:
    """Each annotation reads as the table of FR-030 says."""
    assert field_type_label(annotation) == label


@pytest.mark.parametrize("annotation", [str | None, AssociationOne[_Plain], list[str], Literal["a"]])
def test_no_python_internals_show(annotation: Any) -> None:
    """None of Python's internal spellings leak into a label."""
    label = field_type_label(annotation)
    assert not any(word in label for word in ("UnionType", "NoneType", "Union[", "Optional[", "AssociationOne[", "Generalization["))


def test_a_field_vertex_ships_the_label_and_the_full_annotation() -> None:
    """``field_type`` is the clean label; ``field_annotation`` is the annotation as Python spells it."""
    node = EntityFieldGraphNode(_HeadCoreEntity, "nickname", annotation=str | None)
    properties = node.to_dict()["properties"]
    assert properties["field_type"] == "str | None"
    assert properties["field_annotation"] == "UnionType[str, NoneType]"
