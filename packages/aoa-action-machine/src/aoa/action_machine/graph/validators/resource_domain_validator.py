# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/resource_domain_validator.py
"""
ResourceDomainValidator — an action depends only on resources of its own domain, and a domain reaches a data source through one resource.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource is the point that controls what leaves its store. An action that declared
``@depends`` on a resource of another domain would make that domain's control point
serve a caller it never chose; the work of another domain is reached through that
domain's actions instead. ``@connection`` is not judged: a connection is handed over by
the caller of the action — a transport's socket channel, for one — not chosen by the
action.

A domain reaches each data source through one resource: two resources of one domain that
name the same data source are refused, so a domain's entities in one store are kept by one
resource. Resources of different domains may share a data source, one each. The passes only
read: no node and no edge change.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Action node ──@depends──► Resource node
        │ domain                               │ domain
        └────────────── must be the same ──────┘
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aoa.action_machine.exceptions.data_source_declaration_error import DataSourceDeclarationError
from aoa.action_machine.exceptions.dependency_declaration_error import DependencyDeclarationError
from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.resources.base_resource import BaseResource

_USE_EDGES = ("@depends",)


def validate_resource_domains(nodes: Iterable[Any]) -> None:
    """
    Refuse an action that depends on a resource of another domain.

    Raises:
        DependencyDeclarationError: naming the action, the resource, the kind of use and both domains.
    """
    by_id = {node.node_id: node for node in nodes}
    for node in by_id.values():
        action = node.node_obj
        if not (isinstance(action, type) and issubclass(action, BaseAction)):
            continue
        action_domain = MetaIntentResolver.resolve_domain_type(action)
        for edge in node.get_all_edges():
            if edge.edge_name not in _USE_EDGES:
                continue
            resource = getattr(by_id.get(edge.target_node_id), "node_obj", None)
            if not (isinstance(resource, type) and issubclass(resource, BaseResource)):
                continue
            resource_domain = MetaIntentResolver.resolve_domain_type(resource)
            if resource_domain is not action_domain:
                raise DependencyDeclarationError(
                    f"{action.__name__} ({action_domain.__name__}) uses {resource.__name__} ({resource_domain.__name__}) "
                    f"through {edge.edge_name}: an action uses only resources of its own domain; reach another "
                    "domain through its actions."
                )


def validate_resource_data_sources(nodes: Iterable[Any]) -> None:
    """
    Refuse two resources of one domain that name the same data source.

    Raises:
        DataSourceDeclarationError: naming the domain, the data source and the two resources, by name.
    """
    seen: dict[tuple[type, type], type] = {}
    resources = [node.node_obj for node in nodes]
    for resource in sorted(
        (cls for cls in resources if isinstance(cls, type) and issubclass(cls, BaseResource)), key=lambda cls: cls.__name__
    ):
        domain = MetaIntentResolver.resolve_domain_type(resource)
        data_source = resource.data_source_type()
        if domain is None or data_source is None:
            continue
        first = seen.setdefault((domain, data_source), resource)
        if first is not resource:
            raise DataSourceDeclarationError(
                f"{domain.__name__} reaches {data_source.__name__} through {first.__name__} and {resource.__name__}: "
                "a domain reaches one data source through one resource."
            )
