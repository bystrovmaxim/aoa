"""Verify endpoint guarantees against isolated behavioral regressions.
Run: .venv/bin/python -m pytest docs/reports/evidence/endpoint_role_adversarial.py -q
"""

import importlib
import os
import runpy
from pathlib import Path

import pytest
from pydantic import ValidationError

from aoa.action_machine.domain import AssociationOne, RoleCompatibilityError
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode

_MODE = os.environ.get("AOA_ROLE_MUTATION", "current")
_ROLE = importlib.import_module("aoa.action_machine.graph.validators.entity_role_compatibility_validator")
_FIELD = importlib.import_module("aoa.action_machine.graph.validators.entity_field_validator")
_CONTAINER = importlib.import_module("aoa.action_machine.domain.relation_containers")
_COMPATIBLE = _ROLE.roles_compatible
_CHECK_TARGET = _FIELD._check_relation_target
_MEMBER = _CONTAINER._dictionary_member_of


def _mutated_roles(first: str, second: str) -> bool:
    """Reintroduce exactly one matrix regression in this process."""
    if (
        _MODE == "ownership"
        and first.startswith(("Aggregate", "Composite"))
        and second.startswith(("Aggregate", "Composite"))
    ):
        return True
    if _MODE == "specialized" and first == second == "Generalization":
        return True
    if _MODE == "many" and {first, second} == {"AggregateMany", "AssociationOne"}:
        return False
    return _COMPATIBLE(first, second)


def _single_dictionary_only(host, name, field) -> None:
    """Restore the former dictionary-container prohibition."""
    if field.targets and _FIELD._kind_of(field.targets[0]) == "Enum" and field.container is not AssociationOne:
        _FIELD._refuse(host, name, "Restored AssociationOne-only dictionary restriction")
    _CHECK_TARGET(host, name, field)


def _unchecked_member(dictionary, code, *, item_prefix=""):
    """Accept an unknown identifier as though it selected the first member."""
    if _MODE == "member" and code == "unknown":
        return dictionary.members[0]
    return _MEMBER(dictionary, code, item_prefix=item_prefix)


if _MODE in {"ownership", "specialized", "many"}:
    _ROLE.roles_compatible = _mutated_roles
if _MODE == "dictionary":
    _FIELD._check_relation_target = _single_dictionary_only
if _MODE == "member":
    _CONTAINER._dictionary_member_of = _unchecked_member

_ROOT = Path(__file__).resolve().parents[3]
_EXAMPLES = _ROOT / "examples/step_21_relations"
_PLAIN = runpy.run_path(str(_EXAMPLES / "68_role_plain_associations.py"))
_AGGREGATION = runpy.run_path(str(_EXAMPLES / "69_role_aggregation.py"))
_COMPOSITION = runpy.run_path(str(_EXAMPLES / "70_role_composition.py"))
_SPECIALIZATION = runpy.run_path(str(_EXAMPLES / "71_role_specialization.py"))
_DICTIONARY = runpy.run_path(str(_EXAMPLES / "72_role_dictionary.py"))
_DIRECTIONS = runpy.run_path(str(_EXAMPLES / "73_role_directions.py"))


def test_valid_neighbor() -> None:
    """Keep a valid One pair and independent direction controls usable."""
    assert EntityGraphNode(_PLAIN["CustomerCoreEntity"]).relations[0].properties["cardinality"] == "one"
    _DIRECTIONS["independent_links"]()
    _DIRECTIONS["reciprocal_links"]()
    _DIRECTIONS["conflicting_directions"]()


def test_ownership_pair_refused() -> None:
    """Catch an accidental allowance for ownership at both endpoints."""
    with pytest.raises(RoleCompatibilityError):
        EntityGraphNode(_COMPOSITION["CompositeACoreEntity"])


def test_specialized_pair_refused() -> None:
    """Catch a same-role generalization allowance."""
    with pytest.raises(RoleCompatibilityError):
        EntityGraphNode(_SPECIALIZATION["GeneralizationACoreEntity"])
    EntityGraphNode(_SPECIALIZATION["RecordCoreEntity"])


def test_permitted_many_pair() -> None:
    """Catch a new prohibition based on Many cardinality."""
    node = EntityGraphNode(_AGGREGATION["DepartmentCoreEntity"])
    assert node.relations[0].properties["cardinality"] == "many"


def test_all_dictionary_containers() -> None:
    """Catch restoration of dictionary-specific container restrictions."""
    assert len(EntityGraphNode(_DICTIONARY["PriceListCoreEntity"]).relations) == 6
    _DICTIONARY["python_selection"]()


def test_dictionary_membership() -> None:
    """Catch an unknown code bypassing catalogue membership validation."""
    with pytest.raises(ValidationError, match="not a declared value"):
        _DICTIONARY["PriceListCoreEntity"].model_validate_json(
            '{"primary":{"id":"eur"},"quoted":{"id":"usd"},"snapshot":{"id":"eur"},'
            '"alternatives":[{"id":"unknown"}],"bundled":[]}'
        )
