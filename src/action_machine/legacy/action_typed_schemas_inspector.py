# src/action_machine/legacy/action_typed_schemas_inspector.py
"""
ActionTypedSchemasInspector — legacy facet inspector for action params/result schema usage.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maps each ``BaseAction`` subclass that binds params/result types into the
``action_schemas`` facet: ``FacetVertex`` rows with ``uses_params`` /
``uses_result`` edges to described-fields hosts.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseAction subclasses
              │
              v
    extract_action_params_result_types(cls)
              │
              v
    Snapshot ──► FacetVertex (:data:`ACTION_VERTEX_TYPE`)

Keeps extractor and facet wiring out of :mod:`action_machine.model.base_action`
so that module defines markers and ``BaseAction`` without tail imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.legacy.binding.extract_action_params_result_types import (
    extract_action_params_result_types,
)
from action_machine.legacy.described_fields.described_fields_intent_inspector import (
    DescribedFieldsIntentInspector,
)
from action_machine.legacy.interchange_vertex_labels import ACTION_VERTEX_TYPE
from action_machine.model.base_action import BaseAction
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex


class ActionTypedSchemasInspector(BaseIntentInspector):
    """
    AI-CORE-BEGIN
    ROLE: Concrete inspector for action-to-schema graph mapping.
    CONTRACT: Merged ``action`` payloads; snapshot storage key ``action_schemas``.
    AI-CORE-END
    """

    _target_intent: type = BaseAction

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed view: which schema classes an action uses."""

        class_ref: type
        params_type: type | None
        result_type: type | None

        def to_facet_vertex(self) -> FacetVertex:
            edges: list[FacetEdge] = []
            if self.params_type is not None:
                p_nt, p_name = DescribedFieldsIntentInspector.facet_host_for_schema_type(
                    self.params_type,
                )
                edges.append(
                    FacetEdge(
                        target_node_type=p_nt,
                        target_name=p_name,
                        edge_type="uses_params",
                        is_structural=False,
                        target_class_ref=self.params_type,
                    ),
                )
            if self.result_type is not None:
                r_nt, r_name = DescribedFieldsIntentInspector.facet_host_for_schema_type(
                    self.result_type,
                )
                edges.append(
                    FacetEdge(
                        target_node_type=r_nt,
                        target_name=r_name,
                        edge_type="uses_result",
                        is_structural=False,
                        target_class_ref=self.result_type,
                    ),
                )
            return FacetVertex(
                node_type=ACTION_VERTEX_TYPE,
                node_name=ActionTypedSchemasInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=ActionTypedSchemasInspector._make_meta(
                    params_type=self.params_type,
                    result_type=self.result_type,
                ),
                edges=tuple(edges),
            )

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
        p_type, r_type = extract_action_params_result_types(target_cls)
        if p_type is None and r_type is None:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> Snapshot | None:
        p_type, r_type = extract_action_params_result_types(target_cls)
        if p_type is None and r_type is None:
            return None
        return cls.Snapshot(
            class_ref=target_cls,
            params_type=p_type,
            result_type=r_type,
        )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "action_schemas"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        snap = cls.facet_snapshot_for_class(target_cls)
        assert snap is not None
        return snap.to_facet_vertex()
