# tests/action_machine/graph_model/test_graph_json_schema_generalization.py
"""PR-4: JSON Schema branches for ``parent_action`` / ``parent_role`` / ``parent_domain`` (plan §PR-4, §I.3)."""

from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from aoa.action_machine.graph_model.graph_json_schema import GRAPH_JSON_SCHEMA

_VALIDATOR = Draft202012Validator(GRAPH_JSON_SCHEMA)


def _base_doc(*, edges: list[dict]) -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": "fixture.actions.ChildAction",
                "type": "Action",
                "label": "ChildAction",
                "properties": {"description": "child"},
            },
            {
                "id": "fixture.actions.ParentAction",
                "type": "Action",
                "label": "ParentAction",
                "properties": {"description": "parent"},
            },
            {
                "id": "fixture.roles.ChildRole",
                "type": "Role",
                "label": "ChildRole",
                "properties": {"role_mode": "alive"},
            },
            {
                "id": "fixture.roles.ParentRole",
                "type": "Role",
                "label": "ParentRole",
                "properties": {"role_mode": "alive"},
            },
            {
                "id": "fixture.domains.ChildDomain",
                "type": "Domain",
                "label": "ChildDomain",
                "properties": {"name": "child", "description": "c"},
            },
            {
                "id": "fixture.domains.ParentDomain",
                "type": "Domain",
                "label": "ParentDomain",
                "properties": {"name": "parent", "description": "p"},
            },
        ],
        "edges": edges,
    }


def test_graph_json_schema_accepts_parent_action_edge() -> None:
    _VALIDATOR.validate(
        _base_doc(
            edges=[
                {
                    "source_id": "fixture.actions.ChildAction",
                    "target_id": "fixture.actions.ParentAction",
                    "type": "parent_action",
                    "relationship": "Generalization",
                    "is_dag": False,
                    "properties": {},
                },
            ],
        ),
    )


def test_graph_json_schema_accepts_parent_role_edge() -> None:
    _VALIDATOR.validate(
        _base_doc(
            edges=[
                {
                    "source_id": "fixture.roles.ChildRole",
                    "target_id": "fixture.roles.ParentRole",
                    "type": "parent_role",
                    "relationship": "Generalization",
                    "is_dag": False,
                    "properties": {},
                },
            ],
        ),
    )


def test_graph_json_schema_accepts_parent_domain_edge() -> None:
    _VALIDATOR.validate(
        _base_doc(
            edges=[
                {
                    "source_id": "fixture.domains.ChildDomain",
                    "target_id": "fixture.domains.ParentDomain",
                    "type": "parent_domain",
                    "relationship": "Generalization",
                    "is_dag": False,
                    "properties": {},
                },
            ],
        ),
    )


def test_graph_json_schema_rejects_parent_action_non_generalization_relationship() -> None:
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(
            _base_doc(
                edges=[
                    {
                        "source_id": "fixture.actions.ChildAction",
                        "target_id": "fixture.actions.ParentAction",
                        "type": "parent_action",
                        "relationship": "Association",
                        "is_dag": False,
                        "properties": {},
                    },
                ],
            ),
        )


def test_graph_json_schema_rejects_parent_action_non_empty_properties() -> None:
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(
            _base_doc(
                edges=[
                    {
                        "source_id": "fixture.actions.ChildAction",
                        "target_id": "fixture.actions.ParentAction",
                        "type": "parent_action",
                        "relationship": "Generalization",
                        "is_dag": False,
                        "properties": {"extra": "not-allowed"},
                    },
                ],
            ),
        )
