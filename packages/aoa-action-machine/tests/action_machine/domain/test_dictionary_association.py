# tests/action_machine/domain/test_dictionary_association.py
"""
Tests for the explicit single dictionary association's runtime contract.

A host field typed ``AssociationOne[D]`` accepts an explicit wrapper and normalizes it to a
new frozen wrapper holding the canonical member; it refuses unknown codes, foreign or
mismatched members and raw member/code/reference inputs. Structural wrappers keep their
existing behavior.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseDomain,
    BaseEnumEntity,
    NoInverse,
    value,
)
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity import entity


class AssociationDomain(BaseDomain):
    """Domain for dictionary-association fixtures."""

    name = "association"
    description = "Association"


@entity(description="Currency", domain=AssociationDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """A closed dictionary of currencies."""

    symbol: str = Field(description="Currency symbol")

    EUR = value(code="eur", display_name="Euro", symbol="€")
    USD = value(code="usd", display_name="US dollar", symbol="$")


@exclude_graph_model
@entity(description="Structural target", domain=AssociationDomain)
class StructuralCoreEntity(BaseCoreEntity):
    """A structural target for the unchanged-wrapper control."""

    id: str = Field(description="Identifier")


@exclude_graph_model
@entity(description="Host", domain=AssociationDomain)
class HostCoreEntity(BaseCoreEntity):
    """A host selecting a currency and an optional one, plus a structural relation."""

    id: str = Field(description="Identifier")
    currency: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Currency")
    optional: Annotated[AssociationOne[CurrencyEnumEntity] | None, NoInverse()] = Field(
        default=None, description="Optional currency"
    )
    structural: Annotated[AssociationOne[StructuralCoreEntity], NoInverse()] = Field(description="Structural relation")


def test_an_id_only_wrapper_resolves_the_canonical_member() -> None:
    """An id-only wrapper is normalized to the declared member; id == entity.code."""
    host = HostCoreEntity(id="h1", currency=AssociationOne(id="eur"), structural=AssociationOne(id="s1"))

    assert host.currency.entity is CurrencyEnumEntity.EUR
    assert host.currency.id == host.currency.entity.code


def test_an_identity_matching_member_is_accepted() -> None:
    """A supplied entity that is the identical declared member is accepted."""
    host = HostCoreEntity(
        id="h2",
        currency=AssociationOne(id="eur", entity=CurrencyEnumEntity.EUR),
        structural=AssociationOne(id="s1"),
    )

    assert host.currency.entity is CurrencyEnumEntity.EUR


def test_an_unknown_code_is_refused() -> None:
    """An id naming no declared value is refused."""
    with pytest.raises(ValidationError, match="not a declared value"):
        HostCoreEntity(id="h3", currency=AssociationOne(id="xxx"), structural=AssociationOne(id="s1"))


def test_a_wrong_type_id_is_refused() -> None:
    """A non-string id is not a code shortcut."""
    with pytest.raises(ValidationError, match="non-empty string code"):
        HostCoreEntity(id="h4", currency=AssociationOne(id=7), structural=AssociationOne(id="s1"))


def test_a_mismatched_member_is_refused() -> None:
    """A member whose code disagrees with the supplied id is refused."""
    with pytest.raises(ValidationError, match="not the declared value"):
        HostCoreEntity(
            id="h5",
            currency=AssociationOne(id="eur", entity=CurrencyEnumEntity.USD),
            structural=AssociationOne(id="s1"),
        )


def test_a_copy_of_a_member_is_refused() -> None:
    """A constructed copy is not the declared value."""
    copy = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")

    with pytest.raises(ValidationError, match="not the declared value"):
        HostCoreEntity(id="h6", currency=AssociationOne(id="eur", entity=copy), structural=AssociationOne(id="s1"))


def test_a_raw_member_is_refused() -> None:
    """A bare declared member is not silently wrapped into a container."""
    with pytest.raises(ValidationError):
        HostCoreEntity(id="h7", currency=CurrencyEnumEntity.EUR, structural=AssociationOne(id="s1"))


def test_a_bare_code_is_refused() -> None:
    """A bare code is not silently wrapped into a container."""
    with pytest.raises(ValidationError):
        HostCoreEntity(id="h8", currency="eur", structural=AssociationOne(id="s1"))


def test_a_python_mapping_is_refused() -> None:
    """A Python mapping is not an implicit conversion path."""
    with pytest.raises(ValidationError):
        HostCoreEntity(id="h9", currency={"id": "eur"}, structural=AssociationOne(id="s1"))


def test_the_input_wrapper_is_not_mutated() -> None:
    """The input wrapper stays id-only; the validated field receives a new wrapper."""
    wrapper = AssociationOne(id="eur")

    host = HostCoreEntity(id="h10", currency=wrapper, structural=AssociationOne(id="s1"))

    assert wrapper.entity is None
    assert host.currency is not wrapper
    assert host.currency.entity is CurrencyEnumEntity.EUR


def test_a_nullable_field_accepts_none() -> None:
    """The nullable selection may hold None."""
    host = HostCoreEntity(id="h11", currency=AssociationOne(id="eur"), structural=AssociationOne(id="s1"))

    assert host.optional is None


def test_an_unchanged_structural_wrapper_keeps_its_behavior() -> None:
    """An ordinary structural AssociationOne target is not affected by the dictionary path."""
    wrapper = AssociationOne(id="s1")

    host = HostCoreEntity(id="h12", currency=AssociationOne(id="eur"), structural=wrapper)

    assert host.structural.id == "s1"
    assert host.structural.entity is None
