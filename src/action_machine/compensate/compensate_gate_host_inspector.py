# src/action_machine/compensate/compensate_gate_host_inspector.py
"""
CompensateGateHostInspector — graph inspector for `@compensate` declarations.

The inspector reads method-level `_compensate_meta` and optional
`_required_context_keys`, then emits one aggregated payload per class.


AI-CORE-BEGIN
ROLE: module compensate_gate_host_inspector
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.compensate.compensate_gate_host import CompensateGateHost
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload


class CompensateGateHostInspector(BaseGateHostInspector):
    """Inspector that maps `_compensate_meta` into compensator payload entries."""

    _target_mixin: type = CompensateGateHost

    @classmethod
    def _collect_compensators(
        cls, target_cls: type,
    ) -> tuple[Snapshot.Compensator, ...]:
        from action_machine.core.base_action import BaseAction  # pylint: disable=import-outside-toplevel

        if issubclass(target_cls, BaseAction):
            return tuple(target_cls.scratch_compensators())
        out: list[CompensateGateHostInspector.Snapshot.Compensator] = []
        for attr_name, attr_value in vars(target_cls).items():
            func: Any = attr_value.fget if isinstance(attr_value, property) and attr_value.fget else attr_value
            meta = getattr(func, "_compensate_meta", None)
            if meta is None:
                continue
            out.append(
                cls.Snapshot.Compensator(
                    method_name=attr_name,
                    target_aspect_name=meta.get("target_aspect_name", ""),
                    description=meta.get("description", ""),
                    method_ref=func,
                    context_keys=frozenset(getattr(func, "_required_context_keys", ())),
                ),
            )
        return tuple(out)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_mixin)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed ``@compensate`` facet."""

        @dataclass(frozen=True)
        class Compensator:
            method_name: str
            target_aspect_name: str
            description: str
            method_ref: object
            context_keys: frozenset[str]

        class_ref: type
        compensators: tuple[Compensator, ...]

        def to_facet_payload(self) -> FacetPayload:
            entries = tuple(
                (
                    c.method_name,
                    c.target_aspect_name,
                    c.description,
                    c.method_ref,
                    c.context_keys,
                )
                for c in self.compensators
            )
            return FacetPayload(
                node_type="compensator",
                node_name=CompensateGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=CompensateGateHostInspector._make_meta(compensators=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> CompensateGateHostInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                compensators=CompensateGateHostInspector._collect_compensators(
                    target_cls,
                ),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "compensator"

    @classmethod
    def _has_compensators_invariant(cls, target_cls: type) -> bool:
        return bool(cls._collect_compensators(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if not cls._has_compensators_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> CompensateGateHostInspector.Snapshot | None:
        if not cls._has_compensators_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
