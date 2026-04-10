# src/action_machine/on_error/on_error_gate_host_inspector.py
"""
OnErrorGateHostInspector — graph inspector for `@on_error` declarations.

The inspector reads method-level `_on_error_meta` and optional
`_required_context_keys`, then emits one aggregated payload per class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload
from action_machine.on_error.on_error_gate_host import OnErrorGateHost


class OnErrorGateHostInspector(BaseGateHostInspector):
    """Inspector that maps `_on_error_meta` into error handler payload entries."""

    _target_mixin: type = OnErrorGateHost

    @classmethod
    def _collect_error_handlers(
        cls, target_cls: type,
    ) -> tuple[Snapshot.ErrorHandler, ...]:
        from action_machine.core.base_action import BaseAction  # pylint: disable=import-outside-toplevel

        if issubclass(target_cls, BaseAction):
            return tuple(target_cls.scratch_error_handlers())
        out: list[OnErrorGateHostInspector.Snapshot.ErrorHandler] = []
        for attr_name, attr_value in vars(target_cls).items():
            func: Any = attr_value.fget if isinstance(attr_value, property) and attr_value.fget else attr_value
            meta = getattr(func, "_on_error_meta", None)
            if meta is None:
                continue
            exc_types = meta.get("exception_types", ())
            if isinstance(exc_types, type):
                exc_types = (exc_types,)
            else:
                exc_types = tuple(exc_types)
            out.append(
                cls.Snapshot.ErrorHandler(
                    method_name=attr_name,
                    exception_types=exc_types,
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
        """Typed ``@on_error`` facet."""

        @dataclass(frozen=True)
        class ErrorHandler:
            method_name: str
            exception_types: tuple[type[Exception], ...]
            description: str
            method_ref: object
            context_keys: frozenset[str]

        class_ref: type
        error_handlers: tuple[ErrorHandler, ...]

        def to_facet_payload(self) -> FacetPayload:
            entries = tuple(
                (
                    h.method_name,
                    h.exception_types,
                    h.description,
                    h.method_ref,
                    h.context_keys,
                )
                for h in self.error_handlers
            )
            return FacetPayload(
                node_type="error_handler",
                node_name=OnErrorGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=OnErrorGateHostInspector._make_meta(error_handlers=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> OnErrorGateHostInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                error_handlers=OnErrorGateHostInspector._collect_error_handlers(
                    target_cls,
                ),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "error_handler"

    @classmethod
    def _has_error_handlers_invariant(cls, target_cls: type) -> bool:
        return bool(cls._collect_error_handlers(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if not cls._has_error_handlers_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> OnErrorGateHostInspector.Snapshot | None:
        if not cls._has_error_handlers_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()
