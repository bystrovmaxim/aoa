"""Check guarantees against isolated regressions without editing the checkout.
Run: .venv/bin/python -m pytest docs/reports/evidence/relationship_adversarial.py -q
"""

import importlib
import os
import runpy
from pathlib import Path

import pytest
from pydantic import ValidationError

from aoa.action_machine.domain import AssociationOne
from aoa.action_machine.domain.exceptions import EntityFieldDeclarationError
from aoa.action_machine.graph.validators.entity_field_validator import validate_entity_fields
from aoa.action_machine.graph.validators.entity_inverse_validator import validate_entity_inverses

root = Path(__file__).resolve().parents[3]
mode = os.environ.get("AOA_DOCS_MUTATION", "current")
if mode in ("bare", "embedded"):
    m = importlib.import_module("aoa.action_machine.graph.validators.entity_field_validator")
    old = m._check_field

    def reverted(host, name, field):
        """Verify reverted behavior."""
        if (
            host.__name__ == "HostCoreEntity"
            and name == "target"
            and (any(type(x).__name__ == "NoRelation" for x in field.metadata) == (mode == "embedded"))
        ):
            return None
        return old(host, name, field)

    m._check_field = reverted
if mode == "inverse":
    m = importlib.import_module("aoa.action_machine.graph.validators.entity_inverse_validator")
    m._check_reciprocal = lambda field: None
if mode == "dictionary":
    m = importlib.import_module("aoa.action_machine.domain.relation_containers")
    old = m._dictionary_association_schema

    def reverted(dictionary):
        """Verify reverted behavior."""
        schema = old(dictionary)
        return m.core_schema.no_info_before_validator_function(
            lambda value: AssociationOne(id=value.code, entity=value) if isinstance(value, dictionary) else value,
            schema,
        )

    m._dictionary_association_schema = reverted
if mode == "graph":
    m = importlib.import_module("aoa.action_machine.intents.entity.entity_relation_intent_resolver")
    old = m._from_descriptor
    from aoa.action_machine.domain import BaseEnumEntity

    m._from_descriptor = lambda field: (
        None if field.targets and issubclass(field.targets[0], BaseEnumEntity) else old(field)
    )

pair = runpy.run_path(str(root / "examples/step_21_relations/65_reciprocal_directions.py"))
selection = runpy.run_path(str(root / "examples/step_20_dictionaries/56_selection_transport.py"))


def test_valid_neighbor():
    """Verify test valid neighbor behavior."""
    pair["reciprocal_pair"]()
    pair["one_way_link"]()
    price = selection["PriceCoreEntity"](currency=AssociationOne(id="eur"))
    assert price.currency.entity is selection["CurrencyEnumEntity"].EUR


def test_bare_refused():
    """Verify test bare refused behavior."""
    model = runpy.run_path(str(root / "examples/step_21_relations/55_bare_entity_refused.py"))
    with pytest.raises(EntityFieldDeclarationError):
        validate_entity_fields([model["HostCoreEntity"]])


def test_embedded_refused():
    """Verify test embedded refused behavior."""
    model = runpy.run_path(str(root / "examples/step_21_relations/54_embedded_entity.py"))
    with pytest.raises(EntityFieldDeclarationError):
        validate_entity_fields([model["HostCoreEntity"]])


def test_one_sided_refused():
    """Verify test one sided refused behavior."""
    with pytest.raises(EntityFieldDeclarationError):
        validate_entity_inverses([pair["OldRegionCoreEntity"]])


def test_raw_dictionary_member_refused():
    """Verify test raw dictionary member refused behavior."""
    with pytest.raises(ValidationError):
        selection["PriceCoreEntity"](currency=selection["CurrencyEnumEntity"].EUR)


def test_dictionary_graph_relation():
    """Verify test dictionary graph relation behavior."""
    from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode

    node = EntityGraphNode(selection["PriceCoreEntity"])
    assert len(node.relations) == 1
    assert node.relations[0].properties["relation_type"] == "association"
    assert node.references == []
