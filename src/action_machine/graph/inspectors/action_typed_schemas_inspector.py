# src/action_machine/graph/inspectors/action_typed_schemas_inspector.py
"""
Inspector: bind each action class to its ``BaseAction[P, R]`` schema types in the facet graph.

Walks ``BaseAction`` subclasses, resolves ``P`` and ``R`` via
:func:`extract_action_params_result_types`, and emits an ``action_schemas`` node with
informational edges to ``described_fields`` nodes for those types.

Described field metadata for ``P``/``R`` themselves is owned by
:class:`DescribedFieldsIntentInspector` (intent ``DescribedFieldsIntent``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a graph facet that explicitly links each action to its typed Params and
Result schemas. This makes schema dependencies visible to graph tooling without
duplicating field-level metadata extraction.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseAction subclass
         │
         ▼
    extract_action_params_result_types(target_cls)
         │
         ├─ no P/R -> skip
         └─ has P/R -> Snapshot(params_type, result_type)
                       │
                       ▼
                 FacetPayload(node_type="action_schemas")
                       │
                       ├─ edge "uses_params" -> described_fields<P>
                       └─ edge "uses_result" -> described_fields<R>

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Emits only informational edges (non-structural).
- Produces one ``action_schemas`` node per action with resolved generic types.
- Skips classes where generic schema types cannot be resolved.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Generic resolution quality depends on runtime binding helper behavior.
- This inspector does not validate described fields; that contract belongs to ``DescribedFieldsIntentInspector``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Action schema linkage inspector.
CONTRACT: Resolve ``BaseAction[P, R]`` types and expose them as graph node/edge metadata.
INVARIANTS: Node type is ``action_schemas``; schema links are informational edges to ``described_fields``.
FLOW: action class discovery -> generic extraction -> snapshot -> payload emission.
FAILURES: Missing/unresolved generic bindings result in skip (no payload).
EXTENSION POINTS: Edge labels/storage key can be specialized in derived inspectors.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import EdgeInfo, FacetPayload
from action_machine.model.base_action import BaseAction
from action_machine.runtime.binding.action_generic_params import extract_action_params_result_types


class ActionTypedSchemasInspector(BaseIntentInspector):
    """
    Links each action to its Params/Result schema types.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for action-to-schema graph mapping.
    CONTRACT: Emit ``action_schemas`` payloads for actions with resolved generics.
    INVARIANTS: Snapshot storage key is stable: ``action_schemas``.
    AI-CORE-END
    """

    _target_intent: type = BaseAction

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed view: which schema classes an action uses."""

        class_ref: type
        params_type: type | None
        result_type: type | None

        def to_facet_payload(self) -> FacetPayload:
            edges: list[EdgeInfo] = []
            if self.params_type is not None:
                edges.append(
                    ActionTypedSchemasInspector._make_edge(
                        target_node_type="described_fields",
                        target_cls=self.params_type,
                        edge_type="uses_params",
                        is_structural=False,
                    )
                )
            if self.result_type is not None:
                edges.append(
                    ActionTypedSchemasInspector._make_edge(
                        target_node_type="described_fields",
                        target_cls=self.result_type,
                        edge_type="uses_result",
                        is_structural=False,
                    )
                )
            return FacetPayload(
                node_type="action_schemas",
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
    def inspect(cls, target_cls: type) -> FacetPayload | None:
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
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "action_schemas"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        snap = cls.facet_snapshot_for_class(target_cls)
        assert snap is not None
        return snap.to_facet_payload()
