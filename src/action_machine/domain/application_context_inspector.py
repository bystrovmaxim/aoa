# src/action_machine/domain/application_context_inspector.py
"""
``ApplicationContextInspector`` — emits the canonical ``Application`` vertex and
``Domain`` → ``Application`` informational edges.

Walks every ``BaseDomain`` subclass. For each concrete domain marker, returns
two facet payloads: the shared ``Application`` node (merged across domains) and
the ``Domain`` node with ``belongs_to`` → ``Application``.
"""

from __future__ import annotations

from action_machine.domain.application_context import ApplicationContext
from action_machine.domain.base_domain import BaseDomain
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.interchange_vertex_labels import APPLICATION_VERTEX_TYPE, DOMAIN_VERTEX_TYPE


class ApplicationContextInspector(BaseIntentInspector):
    """
    Inspector: one logical ``Application`` vertex; each ``BaseDomain`` belongs to it.

    Registration should run **before** inspectors that synthesize ``Domain`` stubs
    from ``belongs_to`` edges so domain rows are materialized with metadata; when
    stubs appear first, :meth:`GraphCoordinator._merge_facets_under_collect_key`
    merges ``Domain`` + ``Domain`` rows for the same class.
    """

    _target_intent = BaseDomain

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def inspect(cls, target_cls: type) -> list[FacetPayload] | None:
        domain_payload = cls._domain_payload_or_none(target_cls)
        if domain_payload is None:
            return None
        app_name = cls._make_node_name(ApplicationContext)
        application_payload = FacetPayload(
            node_type=APPLICATION_VERTEX_TYPE,
            node_name=app_name,
            node_class=ApplicationContext,
            node_meta=cls._make_meta(
                description="Logical application root; bounded-context domains belong here.",
            ),
            edges=(),
        )
        return [application_payload, domain_payload]

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        domain_payload = cls._domain_payload_or_none(target_cls)
        if domain_payload is None:
            msg = (
                f"{target_cls!r} is not a materializable BaseDomain subclass "
                "for ApplicationContextInspector"
            )
            raise TypeError(msg)
        return domain_payload

    @classmethod
    def _domain_payload_or_none(cls, target_cls: type) -> FacetPayload | None:
        if target_cls is BaseDomain or not issubclass(target_cls, BaseDomain):
            return None
        name = getattr(target_cls, "name", None)
        description = getattr(target_cls, "description", None)
        if not isinstance(name, str) or not isinstance(description, str):
            return None
        if not name.strip() or not description.strip():
            return None
        domain_name = cls._make_node_name(target_cls)
        domain_edge = cls._make_edge(
            target_node_type=APPLICATION_VERTEX_TYPE,
            target_cls=ApplicationContext,
            edge_type="belongs_to",
            is_structural=False,
        )
        return FacetPayload(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=target_cls,
            node_meta=cls._make_meta(name=name, description=description),
            edges=(domain_edge,),
        )
