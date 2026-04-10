# src/action_machine/checkers/checker_gate_host_inspector.py
"""
CheckerGateHostInspector — graph inspector for checker declarations.

Typed data: ``Snapshot`` under cache key ``\"checker\"`` (``collect_checkers``).


AI-CORE-BEGIN
ROLE: module checker_gate_host_inspector
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload


class CheckerGateHostInspector(BaseGateHostInspector):
    """Inspector that maps `_checker_meta` into checker payload entries."""

    _target_mixin: type = CheckerGateHost

    @classmethod
    def _collect_checkers(cls, target_cls: type) -> tuple[Snapshot.Checker, ...]:
        from action_machine.core.base_action import BaseAction  # pylint: disable=import-outside-toplevel

        if issubclass(target_cls, BaseAction):
            action_out: list[CheckerGateHostInspector.Snapshot.Checker] = []
            for aspect in target_cls.scratch_aspects():
                action_out.extend(
                    target_cls.scratch_checkers_for_aspect(
                        aspect.method_name,
                        method_ref=aspect.method_ref,
                    ),
                )
            return tuple(action_out)
        out: list[CheckerGateHostInspector.Snapshot.Checker] = []
        for attr_name, attr_value in vars(target_cls).items():
            func: Any = attr_value.fget if isinstance(attr_value, property) and attr_value.fget else attr_value
            checker_list = getattr(func, "_checker_meta", None)
            if checker_list is None:
                continue
            for checker_dict in checker_list:
                out.append(
                    cls.Snapshot.Checker(
                        method_name=attr_name,
                        checker_class=checker_dict.get("checker_class", type(None)),
                        field_name=checker_dict.get("field_name", ""),
                        required=checker_dict.get("required", False),
                        extra_params={
                            k: v
                            for k, v in checker_dict.items()
                            if k not in ("checker_class", "field_name", "required")
                        },
                    ),
                )
        return tuple(out)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_mixin)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed checker facet."""

        @dataclass(frozen=True)
        class Checker:
            method_name: str
            checker_class: type
            field_name: str
            required: bool
            extra_params: dict[str, object]

        class_ref: type
        checkers: tuple[Checker, ...]

        def to_facet_payload(self) -> FacetPayload:
            entries = tuple(
                (
                    c.method_name,
                    c.checker_class,
                    c.field_name,
                    c.required,
                    tuple((k, v) for k, v in c.extra_params.items()),
                )
                for c in self.checkers
            )
            return FacetPayload(
                node_type="checker",
                node_name=CheckerGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=CheckerGateHostInspector._make_meta(checkers=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> CheckerGateHostInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                checkers=CheckerGateHostInspector._collect_checkers(target_cls),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "checker"

    @classmethod
    def _has_checker_methods_invariant(cls, target_cls: type) -> bool:
        return bool(cls._collect_checkers(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if not cls._has_checker_methods_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> CheckerGateHostInspector.Snapshot | None:
        if not cls._has_checker_methods_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
