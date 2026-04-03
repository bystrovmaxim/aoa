# src/action_machine/aspects/__init__.py
"""
Пакет аспектов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит декораторы для объявления шагов конвейера бизнес-логики действия
и маркерный миксин, обозначающий поддержку конвейера.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- AspectGateHost — маркерный миксин, обозначающий поддержку конвейера
  аспектов. Наследуется BaseAction. Класс без AspectGateHost в MRO
  не может содержать методы с @regular_aspect или @summary_aspect —
  MetadataBuilder выбросит TypeError при сборке метаданных.

- regular_aspect — декоратор для обычных шагов конвейера. Помечает
  async-метод с сигнатурой (self, params, state, box, connections) → dict.
  Результат объединяется с текущим state. Имя метода обязано заканчиваться
  на "_aspect". Description обязателен (непустая строка).

- summary_aspect — декоратор для финального шага конвейера. Помечает
  async-метод с той же сигнатурой, но возвращающий BaseResult.
  У действия может быть ровно один summary-аспект. Имя метода обязано
  заканчиваться на "_summary". Description обязателен (непустая строка).

═══════════════════════════════════════════════════════════════════════════════
МЕХАНИЗМ РАБОТЫ
═══════════════════════════════════════════════════════════════════════════════

Оба декоратора записывают в метод атрибут _new_aspect_meta:
    {"type": "regular"|"summary", "description": "..."}

MetadataBuilder.collect_aspects(cls) обходит vars(cls), находит методы
с _new_aspect_meta и собирает их в ClassMetadata.aspects (tuple[AspectMeta]).
Порядок аспектов определяется порядком объявления в классе.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРНЫЕ ИНВАРИАНТЫ (проверяются MetadataBuilder)
═══════════════════════════════════════════════════════════════════════════════

- Не более одного summary-аспекта на класс.
- Если есть regular-аспекты, summary обязателен.
- Summary должен быть объявлен последним.
- Имя метода @regular_aspect заканчивается на "_aspect".
- Имя метода @summary_aspect заканчивается на "_summary".
- Description обязателен для обоих декораторов.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.aspects import regular_aspect, summary_aspect

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация данных")
        async def validate_aspect(self, params, state, box, connections):
            return {"validated_user": params.user_id}

        @regular_aspect("Обработка платежа")
        @result_string("txn_id", required=True)
        async def process_payment_aspect(self, params, state, box, connections):
            return {"txn_id": "TXN-001"}

        @summary_aspect("Формирование результата")
        async def build_result_summary(self, params, state, box, connections):
            return OrderResult(...)
"""

from .aspect_gate_host import AspectGateHost
from .regular_aspect import regular_aspect
from .summary_aspect import summary_aspect

__all__ = [
    "AspectGateHost",
    "regular_aspect",
    "summary_aspect",
]
