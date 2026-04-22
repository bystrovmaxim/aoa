# src/action_machine/legacy/meta_intent_inspector.py
"""
MetaIntentInspector — graph inspector for ``@meta`` declarations.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Traverses classes under two marker mixins (``ActionMetaIntent`` and
``ResourceMetaIntent``) without duplicate candidates. **Actions** still emit a
dependent ``meta`` facet node (``…:meta``) folded into the structural ``action``
row where applicable. **Resource managers** emit a canonical
``resource_manager`` vertex (class path only), ``description`` from ``@meta`` on
that node, and an optional informational ``belongs_to`` edge to the domain when
``domain`` is a class.

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
                     FacetVertex — ``meta`` (actions) or ``resource_manager`` (managers)
                            └─ optional belongs_to -> domain
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.intents.meta.action_meta_intent import ActionMetaIntent
from action_machine.legacy.interchange_vertex_labels import ACTION_VERTEX_TYPE, DOMAIN_VERTEX_TYPE
from action_machine.legacy.resource_meta_intent import ResourceMetaIntent
from action_machine.resources.base_resource_manager import BaseResourceManager
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_vertex import FacetVertex


class MetaIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete meta inspector over action/resource marker trees.
    CONTRACT: Emit facet payloads when ``_meta_info`` exists.
    INVARIANTS: Traversal sources are ``ActionMetaIntent`` and ``ResourceMetaIntent``.
    AI-CORE-END
"""

    _target_intents: tuple[type, ...] = (ActionMetaIntent, ResourceMetaIntent)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """
        Typed ``meta`` facet snapshot from ``_meta_info``.

        ``to_facet_vertex()`` adds ``belongs_to`` only when ``domain`` is a type.
        Resource hosts use ``node_type=\"resource_manager\"`` and carry only
        ``description`` in ``node_meta`` (domain is the edge target, not a duplicate
        attribute on the vertex).
        """

        class_ref: type
        description: Any
        domain: Any

        def to_facet_vertex(self) -> FacetVertex:
            """Build facet payload: ``meta`` for actions, ``resource_manager`` for managers."""
            edges: tuple[Any, ...] = ()
            if self.domain is not None and isinstance(self.domain, type):
                edges = (
                    MetaIntentInspector._make_edge(
                        target_node_type=DOMAIN_VERTEX_TYPE,
                        target_cls=self.domain,
                        edge_type="belongs_to",
                        is_structural=False,
                    ),
                )
            if issubclass(self.class_ref, BaseResourceManager):
                return FacetVertex(
                    node_type="resource_manager",
                    node_name=MetaIntentInspector._make_node_name(self.class_ref),
                    node_class=self.class_ref,
                    node_meta=MetaIntentInspector._make_meta(
                        description=self.description,
                    ),
                    edges=edges,
                )
            canonical = MetaIntentInspector._make_node_name(self.class_ref)
            merge_key = f"{ACTION_VERTEX_TYPE}:{canonical}"
            return FacetVertex(
                node_type="meta",
                node_name=MetaIntentInspector._make_host_dependent_node_name(
                    self.class_ref, "meta",
                ),
                node_class=self.class_ref,
                node_meta=MetaIntentInspector._make_meta(
                    description=self.description,
                    domain=self.domain,
                ),
                edges=edges,
                merge_group_key=merge_key,
                merge_node_type=ACTION_VERTEX_TYPE,
                merge_node_name=canonical,
                skip_node_type_snapshot_fallback=True,
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
    def inspect(cls, target_cls: type) -> FacetVertex | None:
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
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        """Build payload through ``Snapshot`` projection for consistency."""
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        """Always ``\"meta\"`` so :meth:`GraphCoordinator.get_snapshot` stays ``(..., \"meta\")``."""
        return "meta"
