# src/action_machine/intents/entity/lifecycle_intent_resolver.py
"""Life-cycle field discovery and template FSM snapshots for ``@entity`` host classes."""

from __future__ import annotations

import types
import typing
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Annotated, Any, get_args, get_origin

from action_machine.domain.lifecycle import Lifecycle, StateInfo


@dataclass(frozen=True)
class LifeCycleFieldResolution:
    """One model field typed as a concrete ``Lifecycle`` subclass with ``_template``."""

    field_name: str
    lifecycle_class: type[Lifecycle]


@dataclass(frozen=True)
class LifeCycleFiniteAutomaton:
    """
    Frozen read-only snapshot of one lifecycle template (states + ``StateInfo`` edges).

    Use :attr:`states`: each :class:`~action_machine.domain.lifecycle.StateInfo`
    exposes ``transitions``, ``state_type``, ``display_name``.
    """

    lifecycle_class: type[Lifecycle]
    states: Mapping[str, StateInfo]

    def __post_init__(self) -> None:
        if not isinstance(self.states, MappingProxyType):  # enforce read-only mapping
            object.__setattr__(self, "states", MappingProxyType(dict(self.states)))


def _lifecycle_annotation_denotes_subclass(annotation: Any) -> bool:
    """True when ``annotation`` refers to any ``Lifecycle`` subclass (Annotated / unions)."""
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _lifecycle_annotation_denotes_subclass(base)

    if isinstance(annotation, type) and issubclass(annotation, Lifecycle) and annotation is not Lifecycle:
        return True

    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        return any(
            arg is not types.NoneType and _lifecycle_annotation_denotes_subclass(arg)
            for arg in get_args(annotation)
        )

    return False


def _extract_concrete_lifecycle_class(annotation: Any) -> type[Lifecycle] | None:
    """First concrete ``Lifecycle`` subclass found in annotation (Annotated / unions)."""
    if get_origin(annotation) is Annotated:
        base = get_args(annotation)[0]
        return _extract_concrete_lifecycle_class(base)

    if isinstance(annotation, type) and issubclass(annotation, Lifecycle) and annotation is not Lifecycle:
        return annotation

    origin = get_origin(annotation)
    if origin is types.UnionType or origin is typing.Union:
        for arg in get_args(annotation):
            if arg is types.NoneType:
                continue
            found = _extract_concrete_lifecycle_class(arg)
            if found is not None:
                return found

    return None


class LifeCycleIntentResolver:
    """
    AI-CORE-BEGIN
    ROLE: Map entity ``model_fields`` to lifecycle columns and expose template graphs.
    CONTRACT: Resolver-only; skips fields without usable ``Lifecycle._get_template()`` (parity with collectors).
    INVARIANTS: Read-only snapshots; no graph coordinator or inspectors.
    FAILURES: :exc:`ValueError` when the field is absent or does not expose a lifecycle template for method (2).
    AI-CORE-END
    """

    @staticmethod
    def resolve_lifecycle_fields(entity_cls: type) -> list[LifeCycleFieldResolution]:
        """
        Lifecycle-typed entries on ``entity_cls``, in ``model_fields`` iteration order.

        Only fields backed by a specialized ``Lifecycle`` subclass with a resolved template
        (:meth:`Lifecycle._get_template`) appear.
        """
        model_fields = getattr(entity_cls, "model_fields", None)
        if not model_fields:
            return []

        try:
            from typing_extensions import get_type_hints  # pylint: disable=import-outside-toplevel

            hints = get_type_hints(entity_cls, include_extras=True)
        except Exception:
            hints = {}

        out: list[LifeCycleFieldResolution] = []
        for field_name, field_info in model_fields.items():
            annotation = hints.get(field_name, field_info.annotation)
            if not _lifecycle_annotation_denotes_subclass(annotation):
                continue
            lifecycle_class = _extract_concrete_lifecycle_class(annotation)
            if lifecycle_class is None:
                continue
            template = lifecycle_class._get_template()
            if template is None:
                continue
            out.append(
                LifeCycleFieldResolution(
                    field_name=field_name,
                    lifecycle_class=lifecycle_class,
                ),
            )

        return out

    @staticmethod
    def resolve_finite_state_machine(
        entity_cls: type,
        field_name: str,
    ) -> LifeCycleFiniteAutomaton:
        """Return immutable template snapshot for ``field_name``, or raise ``ValueError``."""
        needle = field_name.strip()
        for row in LifeCycleIntentResolver.resolve_lifecycle_fields(entity_cls):
            if row.field_name != needle:
                continue
            template = row.lifecycle_class._get_template()
            if template is None:
                break
            return LifeCycleFiniteAutomaton(
                lifecycle_class=row.lifecycle_class,
                states=MappingProxyType(template.get_states()),
            )

        msg = f"{entity_cls!r} has no resolved lifecycle template for field {field_name!r}"
        raise ValueError(msg)
