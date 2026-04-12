# src/action_machine/logging/sensitive_intent_inspector.py
"""
SensitiveIntentInspector — inspector for ``@sensitive`` declarations on schemas and actions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walks concrete subclasses of ``BaseSchema``, ``BaseAction``, and
``BaseResourceManager``, collects ``_sensitive_config`` attached to property
getters (or callables), and emits one facet payload per class for log masking
configuration. Typed rows live on ``SensitiveIntentInspector.Snapshot``; graph
``node_meta`` uses serialisable tuples.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Candidate classes come from ``_target_intents`` union; subclasses are collected
  without duplicates (same pattern as other multi-mixin inspectors).
- Only declaring members on the class MRO are scanned; inherited names are skipped
  once seen on a subclass.
- Graph ``node_type`` / storage key stays ``sensitive`` (coordinator contract).
- Inspector does not execute user code beyond reading attributes on types.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @sensitive(...) @property def x: ...  →  getter._sensitive_config
    SensitiveIntentInspector.inspect(cls)  →  FacetPayload + Snapshot

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Validation of ``@sensitive`` arguments happens in the decorator at import time;
this module only aggregates declared configs for the built graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.core.base_action import BaseAction
from action_machine.core.base_schema import BaseSchema
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.payload import FacetPayload
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


class SensitiveIntentInspector(BaseIntentInspector):
    """
    Inspector that maps sensitive property configs into payload entries.

    Обходит схемы (``BaseSchema``), действия (``BaseAction``) и
    ``BaseResourceManager``: @sensitive на property, как в ``collect_sensitive_fields``.
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
    def _collect_sensitive_entries(cls, target_cls: type) -> tuple[tuple[Any, ...], ...]:
        entries: list[tuple[Any, ...]] = []
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
                entries.append((attr_name, tuple(dict(config).items())))
                seen_names.add(attr_name)
        return tuple(entries)

    @classmethod
    def _collect_sensitive_fields(
        cls, target_cls: type,
    ) -> tuple[Snapshot.Field, ...]:
        fields: list[SensitiveIntentInspector.Snapshot.Field] = []
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
                fields.append(
                    cls.Snapshot.Field(property_name=attr_name, config=dict(config)),
                )
                seen_names.add(attr_name)
        return tuple(fields)

    @classmethod
    def _has_sensitive_fields_invariant(cls, target_cls: type) -> bool:
        return bool(cls._collect_sensitive_entries(target_cls))

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed ``@sensitive`` facet per property."""

        @dataclass(frozen=True)
        class Field:
            property_name: str
            config: dict[str, Any]

        class_ref: type
        fields: tuple[Field, ...]

        def to_facet_payload(self) -> FacetPayload:
            entries = tuple(
                (f.property_name, tuple(f.config.items())) for f in self.fields
            )
            return FacetPayload(
                node_type="sensitive",
                node_name=SensitiveIntentInspector._make_node_name(self.class_ref),
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
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if not cls._has_sensitive_fields_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> SensitiveIntentInspector.Snapshot | None:
        if not cls._has_sensitive_fields_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
