# src/action_machine/aspects/aspect_gate_host.py
"""
Модуль: AspectGateHost — маркерный миксин для декораторов @regular_aspect и @summary_aspect.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

AspectGateHost — миксин-маркер, обозначающий, что класс поддерживает
конвейер аспектов. Декораторы @regular_aspect и @summary_aspect работают
на уровне методов (а не классов), поэтому они НЕ проверяют issubclass
напрямую. Однако миксин играет важную роль:

1. ДОКУМЕНТИРОВАНИЕ КОНТРАКТА: наличие AspectGateHost в MRO класса
   явно показывает, что класс участвует в конвейере аспектов.
   Это читается как контракт: «этот класс предоставляет методы-аспекты».

2. СТРУКТУРНАЯ ВАЛИДАЦИЯ: MetadataBuilder при сборке аспектов может
   проверить, что класс наследует AspectGateHost, прежде чем искать
   методы с _new_aspect_meta. Это защита от случайного использования
   декораторов аспектов в классах, не предназначенных для конвейера.

3. ЕДИНООБРАЗИЕ: все гейт-миксины (RoleGateHost, DependencyGateHost,
   CheckerGateHost, AspectGateHost, ConnectionGateHost, OnGateHost)
   следуют одному паттерну — маркерный класс без логики.

═══════════════════════════════════════════════════════════════════════════════
ЧТО ИЗМЕНИЛОСЬ (рефакторинг «координатор»)
═══════════════════════════════════════════════════════════════════════════════

РАНЬШЕ (до рефакторинга):
    - __init_subclass__ мог собирать аспекты в cls._aspects или
      cls._aspect_gate, создавать AspectGate и замораживать его.
    - Методы get_aspects(), get_regular_aspects(), get_summary_aspect()
      обращались к гейту.
    - ActionProductMachine вызывал cls.get_regular_aspects() и
      cls.get_summary_aspect().

ТЕПЕРЬ (после рефакторинга):
    - Миксин — пустой маркер. Никакой логики.
    - Декораторы @regular_aspect и @summary_aspect записывают
      _new_aspect_meta в сам метод (не в класс).
    - MetadataBuilder._collect_aspects(cls) обходит MRO, находит методы
      с _new_aspect_meta и собирает их в ClassMetadata.aspects.
    - ActionProductMachine читает metadata.get_regular_aspects() и
      metadata.get_summary_aspect() через координатор.
    - AspectGate, get_aspects() и другие методы — УДАЛЕНЫ.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction(
        ABC,
        Generic[P, R],
        RoleGateHost,
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,                 ← маркер: класс поддерживает аспекты
        ConnectionGateHost,
    ): ...

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация суммы")
        async def validate_amount(self, params, state, box, connections):
            ...                         # _new_aspect_meta = {"type": "regular", ...}
            return {}

        @regular_aspect("Обработка платежа")
        async def process_payment(self, params, state, box, connections):
            ...
            return {"txn_id": txn_id}

        @summary_aspect("Формирование результата")
        async def build_result(self, params, state, box, connections):
            ...                         # _new_aspect_meta = {"type": "summary", ...}
            return OrderResult(...)

    # MetadataBuilder.build(CreateOrderAction) обходит MRO, находит три метода
    # с _new_aspect_meta и собирает:
    #   ClassMetadata.aspects = (
    #       AspectMeta("validate_amount", "regular", "Валидация суммы", <ref>),
    #       AspectMeta("process_payment", "regular", "Обработка платежа", <ref>),
    #       AspectMeta("build_result", "summary", "Формирование результата", <ref>),
    #   )

    # ActionProductMachine:
    #   metadata = coordinator.get(CreateOrderAction)
    #   regulars = metadata.get_regular_aspects()   → 2 AspectMeta
    #   summary  = metadata.get_summary_aspect()    → 1 AspectMeta

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # BaseAction уже наследует AspectGateHost, поэтому любой Action
    # автоматически поддерживает @regular_aspect и @summary_aspect.

    # Минимальное действие (только summary):
    class PingAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Pong")
        async def pong(self, params, state, box, connections):
            result = BaseResult()
            result["message"] = "pong"
            return result

    # Действие с полным конвейером:
    class ComplexAction(BaseAction[P, R]):
        @regular_aspect("Шаг 1")
        async def step1(self, params, state, box, connections):
            return {"data": "value"}

        @regular_aspect("Шаг 2")
        async def step2(self, params, state, box, connections):
            return {"more_data": "value2"}

        @summary_aspect("Итог")
        async def finish(self, params, state, box, connections):
            return MyResult(...)
"""


class AspectGateHost:
    """
    Маркерный миксин, обозначающий поддержку конвейера аспектов.

    Класс, наследующий AspectGateHost, может содержать методы,
    декорированные @regular_aspect и @summary_aspect. MetadataBuilder
    собирает эти методы в ClassMetadata.aspects.

    Миксин не содержит логики, полей или методов. Его единственная функция —
    документировать контракт и обеспечивать единообразие с другими
    гейт-миксинами.

    Атрибуты уровня класса (создаются динамически декораторами на методах):
        method._new_aspect_meta : dict
            Словарь {"type": "regular"|"summary", "description": "..."},
            записываемый декоратором @regular_aspect или @summary_aspect
            в сам метод. Читается MetadataBuilder при сборке
            ClassMetadata.aspects (tuple[AspectMeta, ...]).
            НЕ используется напрямую — только через ClassMetadata.
    """

    pass
