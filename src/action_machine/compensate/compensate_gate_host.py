# src/action_machine/compensate/compensate_gate_host.py
"""
CompensateGateHost — маркерный миксин для декоратора @compensate.

Инварианты привязки compensatorов к regular-аспектам задаются здесь же
и проверяются при ``GateCoordinator.build()`` (локальные ``validate_compensators``,
``require_compensate_gate_host_marker`` в этом модуле).


AI-CORE-BEGIN
ROLE: module compensate_gate_host
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any


class CompensateGateHost:
    """
    Marker mixin: класс может объявлять methodы с @compensate.

    Наследуется ``BaseAction``. Сборка метаданных проверяет наличие
    миксина в MRO, если у класса есть compensatorы.
    """

    pass


def require_compensate_gate_host_marker(
    cls: type,
    compensators: list[Any],
) -> None:
    """Есть @compensate → класс должен наследовать CompensateGateHost."""
    if compensators and not issubclass(cls, CompensateGateHost):
        names = ", ".join(c.method_name for c in compensators)
        raise TypeError(
            f"Class {cls.__name__} содержит compensatorы ({names}), "
            f"но не наследует CompensateGateHost. Декоратор @compensate "
            f"разрешён только на классах, наследующих CompensateGateHost. "
            f"Используйте BaseAction или добавьте CompensateGateHost "
            f"в цепочку наследования."
        )


def validate_compensators(
    cls: type,
    compensators: list[Any],
    aspects: list[Any],
) -> None:
    """Привязка compensatorов к существующим regular-аспектам и уникальность."""
    if not compensators:
        return

    aspect_map: dict[str, Any] = {a.method_name: a for a in aspects}
    seen_targets: dict[str, str] = {}

    for comp in compensators:
        target = comp.target_aspect_name

        if target not in aspect_map:
            available = ", ".join(sorted(aspect_map.keys())) if aspect_map else "(нет аспектов)"
            raise ValueError(
                f"Class {cls.__name__}: compensator '{comp.method_name}' "
                f"привязан к аспекту '{target}', который не существует. "
                f"Доступные аспекты: {available}. "
                f"Проверьте target_aspect_name в @compensate."
            )

        target_aspect = aspect_map[target]
        if target_aspect.aspect_type != "regular":
            raise ValueError(
                f"Class {cls.__name__}: compensator '{comp.method_name}' "
                f"привязан к аспекту '{target}', который имеет тип "
                f"'{target_aspect.aspect_type}'. Компенсаторы разрешены "
                f"только для regular-аспектов. Summary-аспект формирует "
                f"итоговый Result и не выполняет побочных эффектов, "
                f"требующих отката."
            )

        if target in seen_targets:
            existing_comp = seen_targets[target]
            raise ValueError(
                f"Class {cls.__name__}: аспект '{target}' имеет два "
                f"compensatorа: '{existing_comp}' и '{comp.method_name}'. "
                f"Для одного аспекта допускается не более одного compensatorа."
            )

        seen_targets[target] = comp.method_name
