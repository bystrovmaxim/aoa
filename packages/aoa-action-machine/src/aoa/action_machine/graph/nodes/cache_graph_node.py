# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/cache_graph_node.py
"""
CacheGraphNode — interchange node for one cache declaration of an operation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each ``@cache_key``, ``@cache_read``, ``@cache_write`` and ``@cache_invalidate`` an
operation declares is a vertex of the assembled graph, as its object check is:
``node_id`` is the operation's dotted id, ``:`` and the method name; interchange
``node_type`` is ``Cache``; ``properties`` carry its ``kind`` and ``description``. A write with
``layout=CacheLayout.ENTITIES`` is checked here too: its Result needs a field typed by
an entity, and each such entity an ``id``.
The operation reaches it by a composition edge named after the declaration
(``@cache_key``, …). Building it checks the declaration's annotation types.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode ──@cache_<kind>──▶ CacheGraphNode
                                          │ node_obj: the declared method
                                          └ required_context edges (``@context_requires``)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.required_context_graph_edge import RequiredContextGraphEdge
from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver
from aoa.action_machine.intents.cache.cache_entity_fields import entity_fields
from aoa.action_machine.intents.cache.cache_intent_resolver import description_of, kind_of, layout_of
from aoa.action_machine.intents.cache.cache_layout import CacheLayout
from aoa.action_machine.intents.cache.cache_signature_types import validate_types
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


def _validate_entity_layout(action_cls: type[Any]) -> None:
    """``layout=CacheLayout.ENTITIES`` needs a Result field typed by an entity, and an ``id`` on each such entity."""
    result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
    fields = entity_fields(result_type)
    if not fields:
        raise DeclarationStructureError(
            f"{action_cls.__name__} writes with layout=CacheLayout.ENTITIES, but {result_type.__qualname__} has no "
            "field typed by an entity (bare, | None or list[...]); the layout would store nothing entity by entity."
        )
    for name, (entity_cls, _many) in fields.items():
        if "id" not in getattr(entity_cls, "model_fields", {}):
            raise DeclarationStructureError(
                f"{action_cls.__name__} writes with layout=CacheLayout.ENTITIES, but {entity_cls.__name__} of field "
                f"'{name}' declares no id; an entity entry is tagged with its type and id."
            )


@dataclass(init=False, frozen=True)
class CacheGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
        ROLE: Interchange node for one cache declaration of one operation.
        CONTRACT: ``node_id`` = ``full_qualname(action) + ':' + method``; :attr:`NODE_TYPE` is ``Cache``; ``properties`` are ``kind`` (``key``, ``read``, ``write``, ``invalidate``) and ``description``; :attr:`required_context` holds the edges ``@context_requires`` asked for.
        INVARIANTS: Built only for a declared method; its annotation types are validated here, at assembly.
        FAILURES: :exc:`~aoa.action_machine.exceptions.AspectSignatureError` from ``validate_types``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Cache"
    required_context: list[RequiredContextGraphEdge]

    def __init__(self, method: Callable[..., Any], _action_cls: type[Any]) -> None:
        kind = kind_of(method)
        validate_types(kind, _action_cls, method)
        if kind == "write" and layout_of(method) is CacheLayout.ENTITIES:
            _validate_entity_layout(_action_cls)
        method_name = TypeIntrospection.unwrapped_callable_name(method)
        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(_action_cls)}:{method_name}",
            node_type=CacheGraphNode.NODE_TYPE,
            label=method_name,
            properties={"kind": kind, "description": description_of(method)},
            node_obj=method,
        )
        object.__setattr__(
            self,
            "required_context",
            RequiredContextGraphEdge.get_required_context_edges(method, _action_cls, self),
        )

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the required-context composition edges."""
        return [*self.required_context]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return the required-context companion nodes this declaration pulled in."""
        return [edge.target_node for edge in self.required_context if edge.target_node is not None]

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-safe vertex (``id``, ``type``, ``label``, properties)."""
        return {"id": self.node_id, "type": self.node_type, "label": self.label, "properties": dict(self.properties)}
