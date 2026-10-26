# tests/action_machine/domain/test_entity_kind.py
"""
Tests for the six kind base classes: what they declare, what they refuse.

Each kind is one file and one class. The class declares its kind word in its own
body, is abstract, is kept out of the model graph, and holds its descendants to
the kind's name suffix. The last test scans the source tree: exactly six classes
declare a kind, so a seventh cannot appear without an argument here.
"""

from __future__ import annotations

import ast
from abc import ABC
from pathlib import Path

import pytest

from aoa.action_machine.domain import (
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseDomain,
    BaseEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    BaseStateEntity,
    value,
)
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model, excluded_from_graph_model
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity

REPO_ROOT = Path(__file__).resolve().parents[5]


class ShopDomain(BaseDomain):
    """The domain the dictionary fixture belongs to."""

    name = "shop"
    description = "Shop model"

KINDS = (
    (BaseCoreEntity, "core", "CoreEntity"),
    (BaseAssocEntity, "assoc", "AssocEntity"),
    (BaseDetailEntity, "detail", "DetailEntity"),
    (BaseSpecEntity, "spec", "SpecEntity"),
    (BaseEnumEntity, "enum", "EnumEntity"),
    (BaseStateEntity, "state", "StateEntity"),
)


@pytest.mark.parametrize(("base", "word", "suffix"), KINDS)
def test_each_base_class_declares_its_kind_in_its_own_body(base: type, word: str, suffix: str) -> None:
    """The kind word, the suffix's class name and the word agree, and the class is a real subclass of the base."""
    assert base.__name__ == f"Base{suffix}"
    assert base.__name__.removeprefix("Base").removesuffix("Entity").lower() == word


@pytest.mark.parametrize(("base", "word", "suffix"), KINDS)
def test_each_base_class_is_abstract(base: type, word: str, suffix: str) -> None:
    """A base class states a role, not a row, so it cannot be constructed."""
    with pytest.raises(TypeError, match="is the base class of a kind and cannot be instantiated"):
        base()


@pytest.mark.parametrize(("base", "word", "suffix"), KINDS)
def test_each_base_class_is_out_of_the_model_graph(base: type, word: str, suffix: str) -> None:
    """A base class never becomes an entity node."""
    assert excluded_from_graph_model(base) is True


@pytest.mark.parametrize(("base", "word", "suffix"), KINDS)
def test_a_name_without_the_kind_suffix_is_refused(base: type, word: str, suffix: str) -> None:
    """A descendant is refused when its name does not carry the kind it inherits."""
    with pytest.raises(NamingSuffixError, match=f"must end with '{suffix}'"):
        type("NotTheKindEntity", (base,), {})


@pytest.mark.parametrize(("base", "word", "suffix"), KINDS)
def test_a_foreign_kind_suffix_is_refused(base: type, word: str, suffix: str) -> None:
    """A name carrying another kind's suffix is refused as the wrong kind."""
    foreign = "DetailEntity" if suffix != "DetailEntity" else "CoreEntity"
    with pytest.raises(NamingSuffixError, match=f"must end with '{suffix}'"):
        type(f"Order{foreign}", (base,), {})


def test_direct_inheritance_from_the_entity_base_is_refused() -> None:
    """An entity states its kind: a class that skips the six has nothing to state."""
    with pytest.raises(DeclarationStructureError, match="inherits BaseEntity directly"):
        type("StrayEntity", (BaseEntity,), {})


def test_a_direct_child_without_the_hook_is_not_a_kind_base_class() -> None:
    """A kind base class is a direct child that overrides the subclass hook; anything else is refused."""
    with pytest.raises(DeclarationStructureError, match="inherits BaseEntity directly"):
        type("NoHookEntity", (BaseEntity,), {"__doc__": "No hook, no kind."})


def test_two_kind_base_classes_are_refused() -> None:
    """One entity, one kind: two base classes cannot both describe it."""
    with pytest.raises(DeclarationStructureError, match="carries 2 kind base classes"):
        type("BothEntity", (BaseCoreEntity, BaseDetailEntity), {"__doc__": "Two kinds at once."})


def test_a_correctly_named_descendant_is_a_real_entity() -> None:
    """The rule accepts the name it asks for, and the descendant constructs."""

    @exclude_graph_model
    class AcceptedCoreEntity(BaseCoreEntity):
        """A lawful core entity, kept out of the graph so other suites see no extra node."""

    assert excluded_from_graph_model(AcceptedCoreEntity) is True
    assert isinstance(AcceptedCoreEntity(), AcceptedCoreEntity)


def test_an_intermediate_abstract_class_is_held_to_the_suffix() -> None:
    """An intermediate base carries its kind like any descendant, and its children carry it too."""

    @exclude_graph_model
    class BaseTransportCoreEntity(BaseCoreEntity, ABC):
        """An intermediate abstract descendant of the core kind."""

    assert excluded_from_graph_model(BaseTransportCoreEntity) is True
    with pytest.raises(NamingSuffixError, match="must end with 'CoreEntity'"):
        type("BaseTransportEntity", (BaseCoreEntity, ABC), {"__doc__": "An intermediate without the suffix."})
    with pytest.raises(NamingSuffixError, match="must end with 'CoreEntity'"):
        type("TruckEntity", (BaseTransportCoreEntity,), {})


def test_an_ordinary_mixin_does_not_count_as_a_kind() -> None:
    """One kind base plus one ordinary mixin is a lawful declaration."""

    class AuditMixin:
        """A mixin that states nothing about the kind."""

    @exclude_graph_model
    class AuditedCoreEntity(AuditMixin, BaseCoreEntity):
        """Audited, still a core entity."""

    assert isinstance(AuditedCoreEntity(), AuditedCoreEntity)


def test_a_decorated_dictionary_is_a_real_entity_in_the_graph() -> None:
    """The dictionary kind is an ordinary entity: only its marker is kept out of the model graph."""

    @entity(description="Currency reference value", domain=ShopDomain)
    class GraphCurrencyEnumEntity(BaseEnumEntity):
        """A decorated dictionary stays in the graph, like any other entity."""

        USD = value(code="usd", display_name="US dollar")

    assert excluded_from_graph_model(GraphCurrencyEnumEntity) is False
    assert EntityGraphNode(GraphCurrencyEnumEntity).to_dict()["properties"]["entity_kind"] == "enum"


def test_exactly_six_classes_inherit_the_entity_base_and_override_the_hook() -> None:
    """A seventh kind base class, anywhere under packages/, would be a second place a kind comes from."""
    declared: list[str] = []
    for path in sorted((REPO_ROOT / "packages").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {ast.unparse(base).split("[")[0].strip() for base in node.bases}
            overrides = {statement.name for statement in node.body if isinstance(statement, ast.FunctionDef)}
            if "BaseEntity" in bases and "__init_subclass__" in overrides:
                declared.append(node.name)

    assert sorted(declared) == [
        "BaseAssocEntity",
        "BaseCoreEntity",
        "BaseDetailEntity",
        "BaseEnumEntity",
        "BaseSpecEntity",
        "BaseStateEntity",
    ], sorted(declared)


KIND_LABELS = (
    (BaseCoreEntity, "Core"),
    (BaseAssocEntity, "Association"),
    (BaseDetailEntity, "Detail"),
    (BaseSpecEntity, "Specialization"),
    (BaseEnumEntity, "Enumeration"),
    (BaseStateEntity, "State"),
)


def _kind_base(body: dict, bases: tuple[type, ...] = (BaseEntity,)) -> type:
    """Declare a user kind base dynamically, so the source scan above never counts it as a seventh.

    Like the six, an accepted kind base is kept out of the model graph, so other suites never see it.
    """
    return exclude_graph_model(type(
        "BaseAggregateEntity",
        bases,
        {"__init_subclass__": classmethod(lambda cls, **kwargs: None), "__module__": __name__, **body},
    ))


@pytest.mark.parametrize(("base", "label"), KIND_LABELS)
def test_each_base_class_declares_its_display_name_in_its_own_body(base: type, label: str) -> None:
    """The name a reader sees for the kind lives on the class that declares the kind."""
    assert base.__dict__["KIND_LABEL"] == label


def test_a_kind_base_without_a_display_name_is_refused() -> None:
    """A kind the graph cannot name is refused when its class is created."""
    with pytest.raises(DeclarationStructureError, match=r"BaseAggregateEntity.*KIND_LABEL"):
        _kind_base({})


@pytest.mark.parametrize("label", ["", "  "])
def test_a_blank_display_name_is_refused(label: str) -> None:
    """An empty or whitespace-only name names nothing."""
    with pytest.raises(DeclarationStructureError, match=r"BaseAggregateEntity.*KIND_LABEL"):
        _kind_base({"KIND_LABEL": label})


def test_a_display_name_inherited_from_a_mixin_is_refused() -> None:
    """Each kind states its own name; borrowing one from a mixin does not count."""

    class NamedMixin:
        """A mixin that happens to carry a label."""

        KIND_LABEL = "Aggregate"

    with pytest.raises(DeclarationStructureError, match=r"BaseAggregateEntity.*KIND_LABEL"):
        _kind_base({}, (NamedMixin, BaseEntity))


def test_a_kind_base_with_a_display_name_is_accepted() -> None:
    """A user model may declare its own kind, as long as it names it."""
    aggregate = _kind_base({"KIND_LABEL": "Aggregate"})
    assert aggregate.__dict__["KIND_LABEL"] == "Aggregate"
