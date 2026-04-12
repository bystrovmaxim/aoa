# src/action_machine/checkers/checker_intent.py
"""
Module: CheckerIntent — marker mixin for checker decorators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

CheckerIntent is a marker mixin that indicates the class supports checker
decorators (for example, @result_string). Checkers are applied to aspect
methods and validate the dict returned by those methods against declared fields.

The presence of CheckerIntent in the class MRO documents the contract:
"this class may contain methods with checkers."

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleIntent,
        DependencyIntent[object],
        CheckerIntent,                ← marker: allows checkers on methods
        AspectIntent,
        ConnectionIntent,
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Payment processing")
        @result_string("txn_id", "Transaction ID", required=True)
        async def process_payment(self, params, state, box, connections):
            ...
            return {"txn_id": txn_id}

    # @result_string writes to the method:
    #   method._checker_meta = [{"checker_class": StringFieldChecker,
    #                            "field_name": "txn_id", ...}]

    # CheckerIntentInspector._collect_checkers(cls) scans class methods
    # with _checker_meta, and collects them into checker snapshot (GateCoordinator.get_checkers).

    # When ActionProductMachine executes the aspect:
    #   checkers = coordinator.get_checkers_for_aspect(Action, "process_payment")
    #   → it applies each checker to the aspect result


AI-CORE-BEGIN
ROLE: module checker_intent
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any, ClassVar


class CheckerIntent:
    """
    Marker mixin indicating support for checker decorators.

    A class inheriting CheckerIntent may contain aspect methods with
    checker decorators (@result_string, etc.). MetadataBuilder collects the
    checkers into checker snapshot (GateCoordinator.get_checkers), and ActionProductMachine applies them
    to aspect results.

    The mixin contains no logic, fields, or methods. Its purpose is to
    document the contract and provide consistency with other gate mixins.
    """

    # Аннотация для mypy (хотя checkerы теперь висят на methodах,
    # мы оставляем атрибут для обратной совместимости проверок)
    _field_checkers: ClassVar[list[Any]]


def require_checker_intent_marker(cls: type, checkers: list[Any]) -> None:
    """Есть checkerы → класс должен наследовать CheckerIntent."""
    if checkers and not issubclass(cls, CheckerIntent):
        checker_fields = ", ".join(c.field_name for c in checkers)
        raise TypeError(
            f"Class {cls.__name__} содержит checkerы для полей ({checker_fields}), "
            f"но не наследует CheckerIntent. Декораторы checkerов "
            f"(@result_string, @result_int и др.) разрешены "
            f"только на классах, наследующих CheckerIntent. "
            f"Используйте BaseAction или добавьте CheckerIntent "
            f"в цепочку наследования."
        )


def validate_checkers_belong_to_aspects(
    cls: type,
    checkers: list[Any],
    aspects: list[Any],
) -> None:
    """Каждый checker привязан к существующему аспекту."""
    aspect_names = {a.method_name for a in aspects}
    for checker in checkers:
        if checker.method_name not in aspect_names:
            raise ValueError(
                f"Class {cls.__name__}: checker '{checker.checker_class.__name__}' "
                f"для поля '{checker.field_name}' привязан к methodу "
                f"'{checker.method_name}', который не является аспектом. "
                f"Чекеры можно применять только к methodам с @regular_aspect "
                f"или @summary_aspect."
            )
