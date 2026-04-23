# src/action_machine/introspection_tools/intent_introspection.py
"""
Intent-scratch introspection: recognize ActionMachine pipeline callables from class ``vars``,
read normalized ``description`` strings from decorator metadata by ``CallableKind``,
read class-level ``@meta`` scratch (``_meta_info``) as a plain mapping, read ``@depends``
scratch on ``_depends_info`` (declared types, ``DependencyInfo`` tuples, interchange target kinds),
and read ``@connection`` scratch on ``_connection_info`` (declared resource types per declaration).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Any

from action_machine.legacy.interchange_vertex_labels import (
    ACTION_VERTEX_TYPE,
    SERVICE_VERTEX_TYPE,
)
from action_machine.runtime.dependency_info import DependencyInfo
from graph.base_intent_inspector import BaseIntentInspector

_RESOURCE_MANAGER_VERTEX_TYPE: str = "resource_manager"


class CallableKind(StrEnum):
    """Own-class intent callables: ``@regular_aspect``, ``@summary_aspect``, ``@compensate``, ``@on_error``."""

    REGULAR_ASPECT = "regular_aspect"
    SUMMARY_ASPECT = "summary_aspect"
    COMPENSATE = "compensate"
    ON_ERROR = "on_error"


class IntentIntrospection:
    """Inspect class namespaces using intent decorator scratch (``_new_aspect_meta``, etc.)."""

    @staticmethod
    def meta_info_dict(host_cls: type) -> dict[str, Any]:
        """
        Return ``_meta_info`` written by ``@meta`` on ``host_cls``, or ``{}`` when absent or not a mapping.
        """
        raw = getattr(host_cls, "_meta_info", None)
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def description_for_callable(call_like: Any, callable_kind: CallableKind | str) -> str | None:
        """
        Return strip-trimmed user ``description`` from intent scratch for ``callable_kind``, or ``None``.

        Unwraps ``property`` getters like :meth:`~graph.base_intent_inspector.BaseIntentInspector._unwrap_declaring_class_member`.
        """
        resolved_kind = CallableKind(callable_kind)
        func = BaseIntentInspector._unwrap_declaring_class_member(call_like)
        meta: Any
        match resolved_kind:
            case CallableKind.REGULAR_ASPECT:
                meta = getattr(func, "_new_aspect_meta", None)
                if not isinstance(meta, Mapping) or meta.get("type") != "regular":
                    return None
            case CallableKind.SUMMARY_ASPECT:
                meta = getattr(func, "_new_aspect_meta", None)
                if not isinstance(meta, Mapping) or meta.get("type") != "summary":
                    return None
            case CallableKind.COMPENSATE:
                meta = getattr(func, "_compensate_meta", None)
            case CallableKind.ON_ERROR:
                meta = getattr(func, "_on_error_meta", None)
        if not isinstance(meta, Mapping):
            return None
        raw = meta.get("description")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    @staticmethod
    def collect_own_class_callables_by_callable_kind(
        owner_class: type,
        callable_kind: CallableKind | str,
    ) -> list[Callable[..., Any]]:
        """Own-class callables in ``vars(owner_class)`` order whose scratch matches ``callable_kind`` (enum or string)."""
        resolved_kind = CallableKind(callable_kind)
        matching_callables: list[Callable[..., Any]] = []
        for _attr_name, namespace_entry in vars(owner_class).items():
            candidate = (
                namespace_entry.fget
                if isinstance(namespace_entry, property) and namespace_entry.fget is not None
                else namespace_entry
            )
            if not callable(candidate):
                continue
            match resolved_kind:
                case CallableKind.REGULAR_ASPECT:
                    aspect_meta = getattr(candidate, "_new_aspect_meta", None)
                    if not isinstance(aspect_meta, dict) or aspect_meta.get("type") != "regular":
                        continue
                case CallableKind.SUMMARY_ASPECT:
                    aspect_meta = getattr(candidate, "_new_aspect_meta", None)
                    if not isinstance(aspect_meta, dict) or aspect_meta.get("type") != "summary":
                        continue
                case CallableKind.COMPENSATE:
                    if getattr(candidate, "_compensate_meta", None) is None:
                        continue
                case CallableKind.ON_ERROR:
                    if getattr(candidate, "_on_error_meta", None) is None:
                        continue
            matching_callables.append(candidate)
        return matching_callables

    @staticmethod
    def _declared_types_from_scratch_entries(host_cls: type, scratch_attr: str) -> list[type]:
        """
        Walk ``getattr(host_cls, scratch_attr)`` (sequence of records with a ``cls`` field);
        return each ``cls`` that is a ``type``, in iteration order.
        """
        raw = getattr(host_cls, scratch_attr, None)
        if not raw:
            return []
        out: list[type] = []
        for entry in raw:
            entry_cls = getattr(entry, "cls", None)
            if isinstance(entry_cls, type):
                out.append(entry_cls)
        return out

    @staticmethod
    def depends_declared_types(host_cls: type) -> list[type]:
        """``cls`` values from ``_depends_info`` (``@depends``), declaration order."""
        return IntentIntrospection._declared_types_from_scratch_entries(host_cls, "_depends_info")

    @staticmethod
    def connection_declared_types(host_cls: type) -> list[type]:
        """``cls`` values from ``_connection_info`` (``@connection``), declaration order."""
        return IntentIntrospection._declared_types_from_scratch_entries(host_cls, "_connection_info")

    @staticmethod
    def depends_infos(host_cls: type) -> tuple[DependencyInfo, ...]:
        """
        Return ``DependencyInfo`` entries from ``_depends_info`` written by ``@depends``,
        or an empty tuple when the attribute is missing or empty.
        """
        raw = getattr(host_cls, "_depends_info", None)
        if not raw:
            return ()
        return tuple(raw)

    @staticmethod
    def depends_target_interchange_node_type(dep_cls: type) -> str:
        """
        Interchange ``target_node_type`` string for a ``@depends`` dependency class.

        Matches :class:`~action_machine.legacy.dependency_intent_inspector.DependencyIntentInspector`
        facet edges: ``BaseAction`` → ``Action``, ``BaseResource`` → ``resource_manager``,
        otherwise ``Service``.

        Imports ``BaseAction`` / ``BaseResource`` lazily to avoid import cycles with
        :mod:`action_machine.model.base_action` during package initialization.
        """
        from action_machine.model.base_action import BaseAction  # pylint: disable=import-outside-toplevel
        from action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel

        if issubclass(dep_cls, BaseAction):
            return ACTION_VERTEX_TYPE
        if issubclass(dep_cls, BaseResource):
            return _RESOURCE_MANAGER_VERTEX_TYPE
        return SERVICE_VERTEX_TYPE
