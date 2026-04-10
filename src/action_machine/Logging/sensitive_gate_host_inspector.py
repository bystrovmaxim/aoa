# src/action_machine/logging/sensitive_gate_host_inspector.py
"""
SensitiveGateHostInspector — graph inspector for `@sensitive` declarations.

The inspector reads `_sensitive_config` from property getters and emits one
aggregated payload per class. Typed data lives on
``SensitiveGateHostInspector.Snapshot``; the graph stores serialisable tuples.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.core.base_action import BaseAction
from action_machine.core.base_schema import BaseSchema
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


class SensitiveGateHostInspector(BaseGateHostInspector):
    """
    Inspector that maps sensitive property configs into payload entries.

    Обходит схемы (``BaseSchema``), действия (``BaseAction``) и
    ``BaseResourceManager``: @sensitive на property, как в ``collect_sensitive_fields``.
    """

    _target_mixins: tuple[type, ...] = (BaseSchema, BaseAction, BaseResourceManager)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        result: list[type] = []
        seen: set[type] = set()
        for mixin in cls._target_mixins:
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
        fields: list[SensitiveGateHostInspector.Snapshot.Field] = []
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
                node_name=SensitiveGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=SensitiveGateHostInspector._make_meta(sensitive_fields=entries),
                edges=(),
            )

        @classmethod
        def from_target(
            cls, target_cls: type,
        ) -> SensitiveGateHostInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                fields=SensitiveGateHostInspector._collect_sensitive_fields(target_cls),
            )

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if not cls._has_sensitive_fields_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> SensitiveGateHostInspector.Snapshot | None:
        if not cls._has_sensitive_fields_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
