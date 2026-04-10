# tests/domain/test_relation_containers.py
"""
Smoke tests for relation **containers** (`AssociationOne`, `AssociationMany`,
`CompositeMany`) and `RelationNotLoadedError`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Containers represent foreign keys or id lists before/after hydration. Tests
cover proxy behavior when a row is present, **lazy** access errors when data is
missing, id validation, and frozen semantics.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **RelationNotLoadedError** — attribute or index access without hydrated
  payload.
- **ValueError** — e.g. `AssociationOne(id=None)`.
- **AttributeError** — setattr on frozen containers.

Not a full hydration suite — see `tests/domain/test_hydration.py` for `build()`.
"""

import pytest

from action_machine.domain.exceptions import RelationNotLoadedError
from action_machine.domain.relation_containers import (
    AssociationMany,
    AssociationOne,
    CompositeMany,
)


class _Row:
    label = "hydrated"


def test_association_one_proxy_when_loaded() -> None:
    ref = AssociationOne(id="1", entity=_Row())
    assert ref.id == "1"
    assert ref.label == "hydrated"


def test_association_one_relation_not_loaded_error_message() -> None:
    ref = AssociationOne(id="CUST-001")
    with pytest.raises(RelationNotLoadedError, match="Related object in AssociationOne"):
        _ = ref.name


def test_association_one_id_cannot_be_none() -> None:
    with pytest.raises(ValueError, match="id cannot be None"):
        AssociationOne(id=None)  # type: ignore[arg-type]


def test_association_one_frozen_setattr() -> None:
    ref = AssociationOne(id="1")
    with pytest.raises(AttributeError, match="is frozen"):
        ref.foo = 1  # type: ignore[misc]


def test_composite_many_index_not_loaded() -> None:
    bag = CompositeMany(ids=("a", "b"))
    with pytest.raises(RelationNotLoadedError, match="Related object in CompositeMany"):
        _ = bag[0]


def test_association_many_iter_not_loaded() -> None:
    bag = AssociationMany(ids=("a", "b"))
    with pytest.raises(RelationNotLoadedError, match="Cannot access '__iter__'"):
        iter(bag)
