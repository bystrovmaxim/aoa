# src/action_machine/checkers/checker_gate_host.py
"""
Module: CheckerGateHost — marker mixin for checker decorators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

CheckerGateHost is a marker mixin that indicates the class supports checker
decorators (for example, @result_string). Checkers are applied to aspect
methods and validate the dict returned by those methods against declared fields.

The presence of CheckerGateHost in the class MRO documents the contract:
"this class may contain methods with checkers."

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleGateHost,
        DependencyGateHost[object],
        CheckerGateHost,                ← marker: allows checkers on methods
        AspectGateHost,
        ConnectionGateHost,
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

    # MetadataBuilder._collect_checkers(cls) walks the MRO, finds methods
    # with _checker_meta, and collects them into ClassMetadata.checkers.

    # When ActionProductMachine executes the aspect:
    #   checkers = metadata.get_checkers_for_aspect("process_payment")
    #   → it applies each checker to the aspect result
"""

from typing import Any, ClassVar


class CheckerGateHost:
    """
    Marker mixin indicating support for checker decorators.

    A class inheriting CheckerGateHost may contain aspect methods with
    checker decorators (@result_string, etc.). MetadataBuilder collects the
    checkers into ClassMetadata.checkers, and ActionProductMachine applies them
    to aspect results.

    The mixin contains no logic, fields, or methods. Its purpose is to
    document the contract and provide consistency with other gate mixins.
    """

    # Аннотация для mypy (хотя чекеры теперь висят на методах,
    # мы оставляем атрибут для обратной совместимости проверок)
    _field_checkers: ClassVar[list[Any]]
