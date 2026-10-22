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
                                    "entity_kind": {
                                        "type": "string",
                                        "minLength": 1,
                                        "description": "Kind of the entity row; 'enum' marks a closed dictionary.",
                                    },
                                    "values": {
                                        "type": "array",
                                        "description": (
                                            "The values a closed dictionary declares, each one its reference "
                                            "object; empty for every other kind."
                                        ),
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "code": {"type": "string", "minLength": 1},
                                                "display_name": {"type": "string", "minLength": 1},
                                            },
                                            "required": ["code", "display_name"],
                                            "additionalProperties": False,
                                        },
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
                                                "reference_qualname": {
                                                    "type": ["string", "null"],
                                                    "description": (
                                                        "Interchange qualname of the closed dictionary this field "
                                                        "references; null for a scalar field."
                                                    ),
                                                },
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
                                "required": [
                                    "id",
                                    "label",
                                    "domain_qualname",
                                    "entity_kind",
                                    "values",
                                    "fields",
                                ],
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
                        "groups": {
                            "type": "array",
                            "description": (
                                "One entry per specialization axis, drawn as a container around its alternatives. "
                                "ERD-only: no other diagram reads this, and a member keeps its own node, columns and "
                                "outside relations."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "group_id": {
                                        "type": "string",
                                        "minLength": 1,
                                        "description": (
                                            "The axis's own identifier, `<head qualname>:<field name>`; the relation "
                                            "into the container points at it."
                                        ),
                                    },
                                    "label": {
                                        "type": "string",
                                        "minLength": 1,
                                        "description": "`<field> (by <classifier>)` — what the container's boundary says.",
                                    },
                                    "dictionary_label": {
                                        "type": "string",
                                        "description": (
                                            "The closed dictionary the axis borrows its codes from; "
                                            "absent when the axis is classified by a field."
                                        ),
                                    },
                                    "classifier_field": {
                                        "type": ["string", "null"],
                                        "description": (
                                            "The head's field whose value selects among the members; "
                                            "null when a closed dictionary classifies the axis."
                                        ),
                                    },
                                    "members": {
                                        "type": "array",
                                        "minItems": 2,
                                        "items": {"type": "string", "minLength": 1},
                                        "description": (
                                            "Qualified names of the alternative entities. At least two, because an axis "
                                            "with one alternative is a plain relation and is emitted as one."
                                        ),
                                    },
                                },
                                "required": ["group_id", "label", "classifier_field", "members"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["entities", "relations", "groups"],
                    "additionalProperties": False,
                },
            },
            "required": ["domain_label", "domain_qualname", "list_entities"],
            "additionalProperties": False,
        },
    },
)
