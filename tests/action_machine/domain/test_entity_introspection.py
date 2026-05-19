# tests/action_machine/domain/test_entity_introspection.py
"""BaseEntity introspection contract (plan §5.21)."""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseEntity,
    FieldNotLoadedError,
    NoInverse,
    Rel,
)
from aoa.action_machine.intents.entity import entity
from tests.action_machine.scenarios.domain_model.entities import (
    DraftLifecycle,
    LifecycleEntity,
    RelatedEntity,
    SampleEntity,
    TestDomain,
)


@entity(description="Order", domain=TestDomain)
class OrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    number: str = Field(description="Order number")
    customer_id: str = Field(description="Customer reference")
    lifecycle: DraftLifecycle | None = Field(default=None, description="Lifecycle")


class TestIsFieldContract:
    def test_declared_and_loaded(self) -> None:
        inst = SampleEntity(id="1", name="A", value=1)
        assert inst.is_field("id") is True

    def test_not_declared(self) -> None:
        inst = SampleEntity(id="1", name="A", value=1)
        assert inst.is_field("missing") is False

    def test_not_loaded(self) -> None:
        inst = SampleEntity.partial(id="1")
        assert inst.is_field("name") is False

    def test_is_fields_one_unavailable(self) -> None:
        inst = SampleEntity.partial(id="1")
        assert inst.is_fields(["id", "name"]) is False

    def test_is_fields_empty(self) -> None:
        inst = SampleEntity(id="1", name="A", value=1)
        assert inst.is_fields([]) is True


class TestGetterContract:
    def test_getters_disjoint_union(self) -> None:
        order = OrderEntity(
            id="o1",
            number="N-1",
            customer_id="c42",
            lifecycle=DraftLifecycle("draft"),
        )
        pk = order.get_primary_key()
        fk = order.get_foreign_keys()
        scalar = order.get_scalar_fields()
        lifecycle = order.get_lifecycle_fields()
        assert pk == {"id": "o1"}
        assert fk == {}
        assert scalar == {"number": "N-1", "customer_id": "c42"}  # scalar id column, not relation
        assert lifecycle == {"lifecycle": order.lifecycle}
        assert not (set(pk) & set(fk) | set(pk) & set(scalar) | set(pk) & set(lifecycle))
        assert order.get_all_fields() == {**pk, **fk, **scalar, **lifecycle}

    def test_relation_excluded_from_getters(self) -> None:
        related = RelatedEntity(id="r1", title="T", parent=None, children=None)
        combined = related.get_all_fields()
        assert combined == {"id": "r1", "title": "T"}
        assert "parent" not in combined
        assert "children" not in combined

    def test_lifecycle_entity(self) -> None:
        inst = LifecycleEntity(id="1", lifecycle=DraftLifecycle("draft"))
        assert set(inst.get_lifecycle_fields()) == {"lifecycle"}


class TestGetFieldValue:
    def test_unloaded_raises(self) -> None:
        inst = SampleEntity.partial(id="1")
        with pytest.raises(FieldNotLoadedError):
            inst.get_field_value("name")

    def test_loaded(self) -> None:
        inst = SampleEntity.partial(id="1", name="A")
        assert inst.get_field_value("name") == "A"


class TestRelationForeignKeys:
    def test_association_one_container_in_get_foreign_keys(self) -> None:
        @entity(description="Child", domain=TestDomain)
        class ChildEntity(BaseEntity):
            id: str = Field(description="id")
            policy: Annotated[
                AssociationOne[OrderEntity] | None,
                NoInverse(),
            ] = Rel(description="Policy")  # type: ignore[assignment]

        policy_ref = AssociationOne(id="pol-9")
        child = ChildEntity(id="1", policy=policy_ref)
        fks = child.get_foreign_keys()
        assert fks == {"policy": policy_ref}
        assert fks["policy"].id == "pol-9"
        assert "policy" not in child.get_scalar_fields()
        assert child.get_all_fields()["policy"] is policy_ref

    def test_none_relation_omitted(self) -> None:
        @entity(description="Child", domain=TestDomain)
        class ChildEntity(BaseEntity):
            id: str = Field(description="id")
            policy: Annotated[
                AssociationOne[OrderEntity] | None,
                NoInverse(),
            ] = Rel(description="Policy")  # type: ignore[assignment]

        child = ChildEntity(id="1", policy=None)
        assert child.get_foreign_keys() == {}
