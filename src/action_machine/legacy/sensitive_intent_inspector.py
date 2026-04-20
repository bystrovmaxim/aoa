# src/action_machine/legacy/sensitive_intent_inspector.py
"""
SensitiveIntentInspector — inspector for ``@sensitive`` declarations on schemas and actions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks concrete subclasses of ``BaseSchema``, ``BaseAction``, and
``BaseResourceManager``, collects ``_sensitive_config`` on declaring members, and
emits:

* one interchange vertex per sensitive property — ``node_type`` ``sensitive_field``,
  ``id`` = ``{declaring_class dotted name}:{property_name}``;
* ownership edges ``HAS_SENSITIVE_FIELD`` from the canonical host vertex
  (``described_fields`` / ``Action`` / ``resource_manager``) to each field vertex.

The aggregate ``…:sensitive`` modifier node is **not** emitted. A typed
:class:`Snapshot` is still stored under storage key ``"sensitive"`` for
``get_snapshot``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.legacy.interchange_vertex_labels import ACTION_VERTEX_TYPE, ENTITY_VERTEX_TYPE
from action_machine.model.base_action import BaseAction
from action_machine.model.base_schema import BaseSchema
from action_machine.resources.base_resource_manager import BaseResourceManager
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex


class SensitiveIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete inspector for sensitive field masking metadata on the graph.
    CONTRACT: ``inspect`` returns multiple ``FacetVertex`` rows; snapshot key ``sensitive``.
    INVARIANTS: Uses union traversal roots and deduplicates classes by identity.
    AI-CORE-END
"""

    _target_intents: tuple[type, ...] = (BaseSchema, BaseAction, BaseResourceManager)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        result: list[type] = []
        seen: set[type] = set()
        for mixin in cls._target_intents:
            for sub in cls._collect_subclasses(mixin):
                if sub in seen:
                    continue
                seen.add(sub)
                result.append(sub)
        return result

    @classmethod
    def _iter_sensitive_declarations(
        cls, target_cls: type,
    ) -> tuple[tuple[type, str, dict[str, Any]], ...]:
        rows: list[tuple[type, str, dict[str, Any]]] = []
        seen_names: set[str] = set()
        for klass in target_cls.__mro__:
            if klass is object:
                continue
            for attr_name, attr_value in vars(klass).items():
                if attr_name in seen_names:
                    continue
                getter = None
                if isinstance(attr_value, property) and attr_value.fget is not None:
                    getter = attr_value.fget
                elif callable(attr_value):
                    getter = attr_value
                if getter is None:
                    continue
                config = getattr(getter, "_sensitive_config", None)
                if config is None:
                    continue
                rows.append((klass, attr_name, dict(config)))
                seen_names.add(attr_name)
        return tuple(rows)

    @classmethod
    def _collect_sensitive_entries(
        cls, target_cls: type,
    ) -> tuple[tuple[tuple[str, Any], ...], ...]:
        entries: list[tuple[tuple[str, Any], ...]] = []
        for _declaring, attr_name, config in cls._iter_sensitive_declarations(target_cls):
            entries.append(
                cls._make_meta(
                    property_name=attr_name,
                    config=tuple(config.items()),
                ),
            )
        return tuple(entries)

    @classmethod
    def _collect_sensitive_fields(
        cls, target_cls: type,
    ) -> tuple[Snapshot.Field, ...]:
        fields: list[SensitiveIntentInspector.Snapshot.Field] = []
        for declaring_klass, attr_name, config in cls._iter_sensitive_declarations(target_cls):
            fields.append(
                cls.Snapshot.Field(
                    declaring_class=declaring_klass,
                    property_name=attr_name,
                    config=config,
                ),
            )
        return tuple(fields)

    @classmethod
    def _has_sensitive_fields_invariant(cls, target_cls: type) -> bool:
        return bool(cls._iter_sensitive_declarations(target_cls))

    @classmethod
    def _sensitive_field_vertex_name(cls, declaring_klass: type, property_name: str) -> str:
        return f"{cls._make_node_name(declaring_klass)}:{property_name}"

    @classmethod
    def _sensitive_host_vertex(cls, declaring_klass: type) -> tuple[str, str]:
        """Return ``(node_type, node_name)`` for the canonical host of ``@sensitive`` rows."""
        # pylint: disable=import-outside-toplevel
        from action_machine.legacy.described_fields.described_fields_intent_inspector import (
            DescribedFieldsIntentInspector,
        )
        from action_machine.legacy.described_fields.marker import DescribedFieldsIntent
        from action_machine.legacy.entity_intent import EntityIntent

        if issubclass(declaring_klass, BaseAction):
            return ACTION_VERTEX_TYPE, cls._make_node_name(declaring_klass)
        if issubclass(declaring_klass, BaseResourceManager):
            return "resource_manager", cls._make_node_name(declaring_klass)
        if issubclass(declaring_klass, EntityIntent):
            return ENTITY_VERTEX_TYPE, cls._make_node_name(declaring_klass)
        if issubclass(declaring_klass, DescribedFieldsIntent):
            return (
                DescribedFieldsIntentInspector.interchange_node_type_for_schema_model(declaring_klass),
                DescribedFieldsIntentInspector.described_fields_vertex_name(declaring_klass),
            )
        return "described_fields", cls._make_node_name(declaring_klass)

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "sensitive"

    @classmethod
    def should_register_facet_snapshot_for_vertex(
        cls,
        _target_cls: type,
        _payload: FacetVertex,
    ) -> bool:
        """Per-field facet nodes carry ``committed_facet_rows`` only; snapshot is for ``get_snapshot``."""
        return False

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed ``@sensitive`` facet (aggregate for ``get_snapshot``)."""

        @dataclass(frozen=True)
        class Field:
            declaring_class: type
            property_name: str
            config: dict[str, Any]

        class_ref: type
        fields: tuple[Field, ...]

        def to_facet_vertex(self) -> FacetVertex:
            entries = tuple(
                SensitiveIntentInspector._make_meta(
                    property_name=f.property_name,
                    config=tuple(f.config.items()),
                )
                for f in self.fields
            )
            return FacetVertex(
                node_type="sensitive",
                node_name=SensitiveIntentInspector._make_host_dependent_node_name(
                    self.class_ref, "sensitive",
                ),
                node_class=self.class_ref,
                node_meta=SensitiveIntentInspector._make_meta(sensitive_fields=entries),
                edges=(),
            )

        @classmethod
        def from_target(
            cls, target_cls: type,
        ) -> SensitiveIntentInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                fields=SensitiveIntentInspector._collect_sensitive_fields(target_cls),
            )

    @classmethod
    def inspect(cls, target_cls: type) -> list[FacetVertex] | None:
        decls = cls._iter_sensitive_declarations(target_cls)
        if not decls:
            return None

        out: list[FacetVertex] = []
        host_edges: dict[type, list[FacetEdge]] = {}

        for declaring_klass, prop_name, config in decls:
            sf_name = cls._sensitive_field_vertex_name(declaring_klass, prop_name)
            out.append(
                FacetVertex(
                    node_type="sensitive_field",
                    node_name=sf_name,
                    node_class=declaring_klass,
                    node_meta=cls._make_meta(
                        property_name=prop_name,
                        config=tuple(config.items()),
                    ),
                    edges=(),
                ),
            )
            host_edges.setdefault(declaring_klass, []).append(
                FacetEdge(
                    target_node_type="sensitive_field",
                    target_name=sf_name,
                    edge_type="has_sensitive_field",
                    is_structural=False,
                    target_class_ref=declaring_klass,
                ),
            )

        for declaring_klass, edges in host_edges.items():
            host_type, host_name = cls._sensitive_host_vertex(declaring_klass)
            out.append(
                FacetVertex(
                    node_type=host_type,
                    node_name=host_name,
                    node_class=declaring_klass,
                    node_meta=(),
                    edges=tuple(edges),
                ),
            )

        return out

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> SensitiveIntentInspector.Snapshot | None:
        if not cls._has_sensitive_fields_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()
