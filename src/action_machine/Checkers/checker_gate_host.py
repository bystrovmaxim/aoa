# src/action_machine/Checkers/checker_gate_host.py
"""
Модуль: CheckerGateHost — маркерный миксин для декораторов чекеров.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

CheckerGateHost — миксин-маркер, обозначающий, что класс поддерживает
декораторы чекеров (например, @StringFieldChecker). Чекеры применяются
к методам-аспектам и проверяют возвращаемый ими словарь на соответствие
объявленным полям.

Наличие CheckerGateHost в MRO класса документирует контракт:
«этот класс может содержать методы с чекерами».

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleGateHost,
        DependencyGateHost[object],
        CheckerGateHost,                ← маркер: разрешает чекеры на методах
        AspectGateHost,
        ConnectionGateHost,
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Обработка платежа")
        @StringFieldChecker("txn_id", "ID транзакции", required=True)
        async def process_payment(self, params, state, box, connections):
            ...
            return {"txn_id": txn_id}

    # Декоратор @StringFieldChecker записывает в метод:
    #   method._checker_meta = [{"checker_class": StringFieldChecker,
    #                            "field_name": "txn_id", ...}]

    # MetadataBuilder._collect_checkers(cls) обходит MRO, находит методы
    # с _checker_meta и собирает их в ClassMetadata.checkers.

    # ActionProductMachine при выполнении аспекта:
    #   checkers = metadata.get_checkers_for_aspect("process_payment")
    #   → применяет каждый чекер к результату аспекта
"""

from typing import Any, ClassVar


class CheckerGateHost:
    """
    Маркерный миксин, обозначающий поддержку декораторов чекеров.

    Класс, наследующий CheckerGateHost, может содержать методы-аспекты
    с декораторами чекеров (@StringFieldChecker и др.). MetadataBuilder
    собирает чекеры в ClassMetadata.checkers, а ActionProductMachine
    применяет их к результатам аспектов.

    Миксин не содержит логики, полей или методов. Его функция —
    документировать контракт и обеспечивать единообразие с другими
    гейт-миксинами.
    """

    # Аннотация для mypy (хотя чекеры теперь висят на методах,
    # мы оставляем атрибут для обратной совместимости проверок)
    _field_checkers: ClassVar[list[Any]]