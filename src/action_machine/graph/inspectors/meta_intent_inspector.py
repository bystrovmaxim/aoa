# src/action_machine/graph/inspectors/meta_intent_inspector.py
"""
MetaIntentInspector — graph inspector for ``@meta`` declarations.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Traverses classes under two marker mixins (``ActionMetaIntent`` and
``ResourceMetaIntent``) without duplicate candidates. For each class with
``@meta`` scratch in ``_meta_info``, emits a ``meta`` node and an optional
informational ``belongs_to`` edge to a domain node when ``domain`` is a class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionMetaIntent / ResourceMetaIntent subclasses
                   │
                   ▼
            MetaIntentInspector.inspect()
                   │
                   ├─ no _meta_info -> None
                   └─ Snapshot.from_target(...)
                            │
                            ▼
                     FacetPayload(node_type="meta")
                            └─ optional belongs_to -> domain

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Candidate traversal deduplicates classes from both marker trees.
- Payload is emitted only when ``_meta_info`` exists.
- Domain edge is emitted only when ``domain`` is a class object.
- Snapshot projection is the single source for payload construction.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``@meta`` argument validation is owned by decorator layer.
- Graph-wide integrity validation is owned by ``GateCoordinator`` build phases.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Meta facet inspector for action/resource classes.
CONTRACT: Read ``_meta_info`` and emit ``meta`` node payloads with optional domain linkage.
INVARIANTS: Dual-marker traversal with deduplication; no payload without decorator scratch.
FLOW: marker subclass discovery -> scratch check -> typed snapshot -> facet payload.
FAILURES: Missing scratch returns ``None`` payload (skip), invalid scratch shape raises ``TypeError``.
EXTENSION POINTS: Marker sources can be extended via ``_target_intents``.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.intents.meta.meta_intents import ActionMetaIntent, ResourceMetaIntent


class MetaIntentInspector(BaseIntentInspector):
    """
    Inspector: ``@meta`` declarations -> ``meta`` node + optional domain edge.

    AI-CORE-BEGIN
    ROLE: Concrete meta inspector over action/resource marker trees.
    CONTRACT: Emit ``meta`` payloads when ``_meta_info`` exists.
    INVARIANTS: Traversal sources are ``ActionMetaIntent`` and ``ResourceMetaIntent``.
    AI-CORE-END
    """

    _target_intents: tuple[type, ...] = (ActionMetaIntent, ResourceMetaIntent)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """
        Typed ``meta`` facet snapshot from ``_meta_info``.

        ``to_facet_payload()`` adds ``belongs_to`` only when ``domain`` is a type.
        """

        class_ref: type
        description: Any
        domain: Any

        def to_facet_payload(self) -> FacetPayload:
            """Build ``FacetPayload`` for ``meta`` node and optional domain edge."""
            edges: tuple[Any, ...] = ()
            if self.domain is not None and isinstance(self.domain, type):
                edges = (
                    MetaIntentInspector._make_edge(
                        target_node_type="domain",
                        target_cls=self.domain,
                        edge_type="belongs_to",
                        is_structural=False,
                    ),
                )
            return FacetPayload(
                node_type="meta",
                node_name=MetaIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=MetaIntentInspector._make_meta(
                    description=self.description,
                    domain=self.domain,
                ),
                edges=edges,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> MetaIntentInspector.Snapshot:
            """Build snapshot from ``target_cls._meta_info``."""
            meta_info = getattr(target_cls, "_meta_info", None)
            if not isinstance(meta_info, dict):
                raise TypeError(
                    f"{target_cls.__name__} does not contain valid _meta_info.",
                )
            return cls(
                class_ref=target_cls,
                description=meta_info.get("description"),
                domain=meta_info.get("domain"),
            )

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """Union marker-subclass traversals from all targets without duplicates."""
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
    def _has_meta_info_invariant(cls, target_cls: type) -> bool:
        """True when ``_meta_info`` is present on the class."""
        return getattr(target_cls, "_meta_info", None) is not None

    @classmethod
    def _has_domain_invariant(cls, target_cls: type) -> bool:
        """True when ``_meta_info.domain`` exists and is not ``None``."""
        meta_info = getattr(target_cls, "_meta_info", None)
        if not isinstance(meta_info, dict):
            return False
        return meta_info.get("domain") is not None

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """Return ``meta`` payload when declaration exists; otherwise ``None``."""
        if not cls._has_meta_info_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> MetaIntentInspector.Snapshot | None:
        """Return typed snapshot for coordinator cache, or ``None`` when absent."""
        if not cls._has_meta_info_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Build payload through ``Snapshot`` projection for consistency."""
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
