# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/list_entities_action_schema.py
"""
list_entities_action_schema — JSON Schema for ``ListEntitiesAction.Result.domain_slices``.
"""

from __future__ import annotations

from aoa.action_machine.model import JsonSchemaValue

# One slice per requested domain: label, qualname, and ``list_entities`` (entities + relations).
ListEntitiesDomainSlicesJson = JsonSchemaValue.define(
    name="ListEntitiesDomainSlicesJson",
    schema={
        "type": "array",
        "minItems": 0,
        "items": {
            "type": "object",
            "properties": {
                "domain_label": {"type": "string", "minLength": 1},
                "domain_qualname": {"type": "string", "minLength": 1},
                "list_entities": {
                    "type": "object",
                    "properties": {
                        "entities": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "label": {"type": "string"},
                                    "domain_qualname": {
                                        "type": "string",
                                        "description": (
                                            "Interchange qualname of the BaseDomain owning this entity "
                                            "(for accent coloring)."
                                        ),
                                    },
                                    "fields": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                        "properties": {
                                            "field_id": {
                                                "type": ["string", "null"],
                                                "description": (
                                                    "Interchange node id of the EntityField vertex when the row is a "
                                                    "scalar field (null for synthetic relation/FK rows)."
                                                ),
                                            },
                                            "name": {"type": "string"},
                                                "type": {"type": "string"},
                                                "primary_key": {"type": "boolean"},
                                                "foreign_key": {"type": "boolean"},
                                            },
                                            "required": [
                                                "name",
                                                "type",
                                                "primary_key",
                                                "foreign_key",
                                            ],
                                            "additionalProperties": False,
                                        },
                                    },
                                },
                                "required": ["id", "label", "domain_qualname", "fields"],
                                "additionalProperties": False,
                            },
                        },
                        "relations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source": {"type": "string"},
                                    "target": {"type": "string"},
                                    "label": {"type": "string"},
                                    "relationship_kind": {"type": "string"},
                                    "source_cardinality": {
                                        "type": "string",
                                        "enum": ["one", "zero_one", "one_many", "zero_many"],
                                    },
                                    "target_cardinality": {
                                        "type": "string",
                                        "enum": ["one", "zero_one", "one_many", "zero_many"],
                                    },
                                },
                                "required": [
                                    "source",
                                    "target",
                                    "label",
                                    "relationship_kind",
                                    "source_cardinality",
                                    "target_cardinality",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["entities", "relations"],
                    "additionalProperties": False,
                },
            },
            "required": ["domain_label", "domain_qualname", "list_entities"],
            "additionalProperties": False,
        },
    },
)
