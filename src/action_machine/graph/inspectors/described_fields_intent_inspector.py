# src/action_machine/graph/inspectors/described_fields_intent_inspector.py
"""
DescribedFieldsIntentInspector — graph inspector for ``DescribedFieldsIntent``.

The marker mixin lives in :mod:`action_machine.intents.described_fields.marker`.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Extract Pydantic field documentation metadata (description, examples,
constraints, required/default) and publish it as a dedicated
``described_fields`` facet node.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    DescribedFieldsIntent subclass
            │
            ▼
    _collect_pydantic_fields(model_cls)
            │
            ▼
    Snapshot(fields=...)
            │
            ▼
    FacetPayload(node_type="described_fields", node_meta=schema_fields)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Emits payloads only for classes that are valid Pydantic models with fields.
- Snapshot storage key is fixed: ``described_fields``.
- No graph edges are produced by this inspector.
- Field constraints are aggregated from direct ``FieldInfo`` attrs and metadata entries.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Non-Pydantic classes or models without fields are skipped.
- Type string rendering is best-effort and may be simplified for complex annotations.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Described-fields metadata inspector.
CONTRACT: Convert model field documentation metadata into ``described_fields`` facet payloads.
INVARIANTS: Storage key is ``described_fields``; classes without documentable fields are skipped.
FLOW: class discovery -> pydantic field extraction -> typed snapshot -> payload emission.
FAILURES: Absence of fields returns ``None`` payload (skip), not an error.
EXTENSION POINTS: Constraint extraction can be expanded via ``_CONSTRAINT_ATTRS``.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.intents.described_fields.marker import DescribedFieldsIntent


class DescribedFieldsIntentInspector(BaseIntentInspector):
    """
    Inspector for Pydantic field documentation metadata.

    AI-CORE-BEGIN
    ROLE: Concrete described-fields inspector.
    CONTRACT: Emit ``described_fields`` payloads from Pydantic model field metadata.
    INVARIANTS: Marker traversal via ``DescribedFieldsIntent`` and stable storage key.
    AI-CORE-END
    """

    _target_intent: type = DescribedFieldsIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        @dataclass(frozen=True)
        class FieldDescription:
            field_name: str
            field_type: str
            description: str
            examples: tuple[Any, ...] | None
            constraints: dict[str, Any]
            required: bool
            default: Any

        class_ref: type
        fields: tuple[FieldDescription, ...]

        def to_facet_payload(self) -> FacetPayload:
            def _to_row(fd: DescribedFieldsIntentInspector.Snapshot.FieldDescription) -> tuple[Any, ...]:
                return (
                    fd.field_name,
                    fd.field_type,
                    fd.description,
                    fd.examples,
                    tuple(fd.constraints.items()),
                    fd.required,
                    fd.default,
                )

            return FacetPayload(
                node_type="described_fields",
                node_name=DescribedFieldsIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=DescribedFieldsIntentInspector._make_meta(
                    schema_fields=tuple(_to_row(f) for f in self.fields),
                ),
                edges=(),
            )

    _CONSTRAINT_ATTRS: tuple[str, ...] = (
        "gt", "ge", "lt", "le",
        "min_length", "max_length",
        "pattern",
        "multiple_of",
        "strict",
    )

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def _extract_constraints(cls, field_info: FieldInfo) -> dict[str, Any]:
        constraints: dict[str, Any] = {}
        for attr in cls._CONSTRAINT_ATTRS:
            value = getattr(field_info, attr, None)
            if value is not None:
                constraints[attr] = value
        for meta_item in field_info.metadata or []:
            for attr in cls._CONSTRAINT_ATTRS:
                value = getattr(meta_item, attr, None)
                if value is not None and attr not in constraints:
                    constraints[attr] = value
        return constraints

    @classmethod
    def _collect_pydantic_fields(
        cls, model_cls: type | None,
    ) -> tuple[Snapshot.FieldDescription, ...]:
        if model_cls is None or not isinstance(model_cls, type) or not issubclass(model_cls, BaseModel):
            return ()
        model_fields = model_cls.model_fields
        if not model_fields:
            return ()
        result: list[DescribedFieldsIntentInspector.Snapshot.FieldDescription] = []
        for field_name, field_info in model_fields.items():
            annotation = field_info.annotation
            field_type_str = str(annotation) if annotation is not None else "Any"
            if annotation is not None and hasattr(annotation, "__name__"):
                field_type_str = annotation.__name__
            is_required = field_info.is_required()
            result.append(
                cls.Snapshot.FieldDescription(
                    field_name=field_name,
                    field_type=field_type_str,
                    description=field_info.description or "",
                    examples=tuple(field_info.examples) if field_info.examples is not None else None,
                    constraints=cls._extract_constraints(field_info),
                    required=is_required,
                    default=field_info.default if not is_required else PydanticUndefined,
                ),
            )
        return tuple(result)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        fields = cls._collect_pydantic_fields(target_cls)
        if not fields:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> Snapshot | None:
        fields = cls._collect_pydantic_fields(target_cls)
        if not fields:
            return None
        return cls.Snapshot(class_ref=target_cls, fields=fields)

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "described_fields"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        snap = cls.facet_snapshot_for_class(target_cls)
        assert snap is not None
        return snap.to_facet_payload()
