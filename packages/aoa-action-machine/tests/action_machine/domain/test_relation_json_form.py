# packages/aoa-action-machine/tests/action_machine/domain/test_relation_json_form.py
"""
A relation to an ordinary entity has one JSON form, read back on every path.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Cases 1.1 and 3.1–3.5 of issue #407. A One container writes ``{"id"}`` or
``{"id", "entity"}``, a Many container ``{"ids"}`` or ``{"ids", "entities"}``;
the same validator reads that form from JSON, from a dict and from a container,
types the ids by the target's ``id`` field, and reads a target with missing
fields as a partial entity.
"""

from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseDomain,
    CompositeMany,
    CompositeOne,
    Inverse,
    NoInverse,
)
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage

U1 = "00000000-0000-0000-0000-000000000001"
U2 = "00000000-0000-0000-0000-000000000002"


class _FormsDomain(BaseDomain):
    """Domain of the entities of this module."""

    name = "relation_json_forms"
    description = "Entities for the relation JSON form tests"


@meta(description="Stores the forms entities")
class _FormsStorage(BaseStorage):
    """Hold the forms entities."""


@entity(description="Customer", domain=_FormsDomain)
class FormCustomerCoreEntity(BaseCoreEntity):
    """A customer with a UUID id and the orders that point at it."""

    id: UUID = Field(description="Customer id")
    name: str = Field(description="Name")
    orders: Annotated[AssociationMany[FormOrderCoreEntity], Inverse(FormOrderCoreEntity, "customer")] = Field(
        description="Orders"
    )


@entity(description="Line", domain=_FormsDomain)
class FormLineDetailEntity(BaseDetailEntity):
    """An order line with a string id."""

    id: str = Field(description="Line id")


@entity(description="Note", domain=_FormsDomain)
class FormNoteDetailEntity(BaseDetailEntity):
    """A target that declares no id field."""

    text: str = Field(description="Text")


@entity(description="Order", domain=_FormsDomain)
class FormOrderCoreEntity(BaseCoreEntity):
    """An order with a customer, lines and notes."""

    id: str = Field(description="Order id")
    customer: Annotated[AssociationOne[FormCustomerCoreEntity], Inverse(FormCustomerCoreEntity, "orders")] = Field(
        description="Customer"
    )
    lines: Annotated[CompositeMany[FormLineDetailEntity], NoInverse()] = Field(description="Lines")
    note: Annotated[CompositeOne[FormNoteDetailEntity] | None, NoInverse()] = Field(default=None, description="Note")


# The customer names the order before the order exists; resolve its annotation now that both do.
FormCustomerCoreEntity.model_rebuild()


@entity(description="A target that names a class declared later", domain=_FormsDomain)
class FormBriefCoreEntity(BaseCoreEntity):
    """A target whose own annotation resolves only after another class exists."""

    id: str = Field(description="Brief id")
    stage: Annotated[AssociationOne[FormStageCoreEntity], NoInverse()] = Field(description="Stage")


@entity(description="Points at the brief before the brief is complete", domain=_FormsDomain)
class FormHintCoreEntity(BaseCoreEntity):
    """An entity rebuilt while its relation's target is still incomplete."""

    id: str = Field(description="Hint id")
    brief: Annotated[AssociationOne[FormBriefCoreEntity], NoInverse()] = Field(description="Brief")


# An import cycle closed by model_rebuild: the hint is rebuilt before its target can be.
FormHintCoreEntity.model_rebuild()


@entity(description="Declared after the brief", domain=_FormsDomain)
class FormStageCoreEntity(BaseCoreEntity):
    """The class the brief names."""

    id: str = Field(description="Stage id")


FormBriefCoreEntity.model_rebuild()


def _order(**fields: Any) -> FormOrderCoreEntity:
    data: dict[str, Any] = {
        "id": "o1",
        "customer": AssociationOne[FormCustomerCoreEntity](id=U1),
        "lines": CompositeMany[FormLineDetailEntity](ids=("l1", "l2")),
    }
    data.update(fields)
    return FormOrderCoreEntity(**data)


# ── 3.1 and 1.1: JSON out ──────────────────────────────────────────────────


def test_unloaded_relations_go_out_as_their_ids() -> None:
    """Case 3.1: an unloaded One writes {"id"}, an unloaded Many {"ids"}."""
    dumped = _order().model_dump(mode="json")
    assert dumped["customer"] == {"id": U1}
    assert dumped["lines"] == {"ids": ["l1", "l2"]}
    assert dumped["note"] is None


def test_a_loaded_relation_goes_out_with_its_entity() -> None:
    """Case 1.1: a loaded One writes the entity it holds, a partial one included."""
    customer = FormCustomerCoreEntity.partial(id=UUID(U1), name="Ann")
    order = _order(customer=AssociationOne[FormCustomerCoreEntity](id=U1, entity=customer))
    assert order.model_dump(mode="json")["customer"] == {"id": U1, "entity": {"id": U1, "name": "Ann"}}


def test_a_python_dump_keeps_the_container() -> None:
    """Python mode keeps the container, as #405 delivered."""
    assert isinstance(_order().model_dump()["customer"], AssociationOne)


# ── 3.2: JSON Schema ────────────────────────────────────────────────────────


def _definition(schema: dict[str, Any], name: str) -> dict[str, Any]:
    return schema["$defs"][name] if "$defs" in schema and name in schema["$defs"] else schema


def test_the_schema_builds_closed_and_names_the_target() -> None:
    """Case 3.2: the relation is a closed object with a required id and the target by reference."""
    schema = FormOrderCoreEntity.model_json_schema()
    customer = _definition(schema, "FormOrderCoreEntity")["properties"]["customer"]
    assert customer["type"] == "object"
    assert customer["required"] == ["id"]
    assert customer["additionalProperties"] is False
    assert customer["properties"]["id"]["format"] == "uuid"
    assert customer["properties"]["entity"]["$ref"] == "#/$defs/FormCustomerCoreEntity"
    lines = _definition(schema, "FormOrderCoreEntity")["properties"]["lines"]
    assert lines["required"] == ["ids"]
    assert lines["properties"]["entities"]["items"] == {"$ref": "#/$defs/FormLineDetailEntity"}


def test_a_recursive_pair_builds_a_finite_schema() -> None:
    """Customer.orders and Order.customer point at each other; both schemas build."""
    customer_schema = FormCustomerCoreEntity.model_json_schema()
    orders = _definition(customer_schema, "FormCustomerCoreEntity")["properties"]["orders"]
    assert orders["properties"]["entities"]["items"] == {"$ref": "#/$defs/FormOrderCoreEntity"}
    assert "FormOrderCoreEntity" in customer_schema["$defs"]


# ── 3.3 and 3.4: JSON in ────────────────────────────────────────────────────


def test_the_id_forms_are_read_back_from_json_and_from_a_dict() -> None:
    """Case 3.3: {"id"} and {"ids"} read back as unloaded containers, on every path."""
    data = {"id": "o1", "customer": {"id": U1}, "lines": {"ids": ["l1"]}}
    for order in (FormOrderCoreEntity.model_validate_json(json.dumps(data)), FormOrderCoreEntity.model_validate(data)):
        assert (order.customer.id, order.customer.is_loaded) == (UUID(U1), False)
        assert (order.lines.ids, order.lines.is_loaded) == (("l1",), False)
        assert type(order.customer) is AssociationOne


def test_loaded_with_zero_rows_survives_the_trip() -> None:
    """Case 3.4: {"ids": [], "entities": []} is loaded, {"ids": []} is not."""
    loaded = _order(lines=CompositeMany[FormLineDetailEntity](ids=(), entities=(), entities_loaded=True))
    assert loaded.model_dump(mode="json")["lines"] == {"ids": [], "entities": []}
    assert FormOrderCoreEntity.model_validate_json(loaded.model_dump_json()).lines.is_loaded
    unloaded = _order(lines=CompositeMany[FormLineDetailEntity](ids=()))
    assert unloaded.model_dump(mode="json")["lines"] == {"ids": []}
    assert not FormOrderCoreEntity.model_validate_json(unloaded.model_dump_json()).lines.is_loaded


def test_a_loaded_partial_target_reads_back_partial() -> None:
    """A missing field inside "entity" means not loaded."""
    customer = FormCustomerCoreEntity.partial(id=UUID(U1), name="Ann")
    order = _order(customer=AssociationOne[FormCustomerCoreEntity](id=U1, entity=customer))
    back = FormOrderCoreEntity.model_validate_json(order.model_dump_json())
    assert back.customer.name == "Ann"
    assert back.customer.entity is not None
    assert not back.customer.entity.is_field_loaded("orders")
    assert back == order


def test_loaded_entities_read_back() -> None:
    """A loaded Many reads back its entities, typed and loaded."""
    lines = CompositeMany[FormLineDetailEntity](ids=("l1",), entities=(FormLineDetailEntity(id="l1"),))
    back = FormOrderCoreEntity.model_validate_json(_order(lines=lines).model_dump_json())
    assert back.lines.is_loaded
    assert [type(line).__name__ for line in back.lines] == ["FormLineDetailEntity"]
    assert back.lines[0].id == "l1"


# ── 3.5: the type of the ids ───────────────────────────────────────────────


def test_ids_take_the_type_of_the_targets_id() -> None:
    """Case 3.5: a string UUID becomes a UUID, in code and after reading back, for One and Many."""
    order = _order()
    assert order.customer.id == UUID(U1)
    assert FormOrderCoreEntity.model_validate_json(order.model_dump_json()).customer.id == UUID(U1)
    customer = FormCustomerCoreEntity(id=U2, name="Ann", orders=AssociationMany[FormOrderCoreEntity](ids=("o1",)))
    assert customer.orders.ids == ("o1",)
    many = FormCustomerCoreEntity.model_validate({"id": U2, "name": "Ann", "orders": {"ids": ["o1", "o2"]}}).orders
    assert many.ids == ("o1", "o2")


def test_an_id_of_the_wrong_type_is_refused_at_the_id() -> None:
    """Case 3.5: "abc" is not a UUID; the error is located at customer.id."""
    with pytest.raises(ValidationError) as exc_info:
        _order(customer=AssociationOne[FormCustomerCoreEntity](id="abc"))
    error = exc_info.value.errors()[0]
    assert error["loc"] == ("customer", "id")
    assert error["type"] == "uuid_parsing"


def test_a_target_without_an_id_takes_str_or_int() -> None:
    """A target that declares no id takes ids JSON keeps exactly; anything else is refused."""
    assert _order(note=CompositeOne[FormNoteDetailEntity](id="n1")).note.id == "n1"
    assert _order(note=CompositeOne[FormNoteDetailEntity](id=7)).note.id == 7
    with pytest.raises(ValidationError):
        _order(note=CompositeOne[FormNoteDetailEntity](id=1.5))


# ── an import cycle ─────────────────────────────────────────────────────────


def test_an_entity_rebuilds_before_its_relations_target_is_complete() -> None:
    """A relation does not need its target's schema to build, as before #407; the forms still work."""
    hint = FormHintCoreEntity.model_validate({"id": "h1", "brief": {"id": "b1"}})
    assert hint.brief.id == "b1"
    assert hint.model_dump(mode="json") == {"id": "h1", "brief": {"id": "b1"}}
    schema = FormHintCoreEntity.model_json_schema()
    assert schema["properties"]["brief"]["properties"]["entity"]["$ref"] == "#/$defs/FormBriefCoreEntity"


# ── refusals ────────────────────────────────────────────────────────────────


def test_a_container_of_another_class_is_refused() -> None:
    """A CompositeOne in an AssociationOne field is refused, as today."""
    with pytest.raises(ValidationError):
        _order(customer=CompositeOne[FormCustomerCoreEntity](id=U1))


def test_an_unknown_key_is_refused() -> None:
    """The relation form is closed."""
    with pytest.raises(ValidationError):
        FormOrderCoreEntity.model_validate({"id": "o1", "customer": {"id": U1, "x": 1}, "lines": {"ids": []}})


def test_an_undeclared_field_inside_the_entity_is_refused() -> None:
    """A target read from a dict refuses a field it does not declare."""
    with pytest.raises(ValidationError):
        FormOrderCoreEntity.model_validate(
            {"id": "o1", "customer": {"id": U1, "entity": {"id": U1, "nick": "A"}}, "lines": {"ids": []}}
        )
