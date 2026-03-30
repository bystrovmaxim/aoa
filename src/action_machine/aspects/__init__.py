# src/action_machine/aspects/__init__.py
"""
Пакет аспектов ActionMachine.

Содержит:
- AspectGateHost — маркерный миксин, обозначающий поддержку конвейера
  аспектов. Наследуется BaseAction.
- regular_aspect — декоратор для обычных шагов конвейера. Помечает
  async-метод с сигнатурой (self, params, state, box, connections) → dict.
  Результат объединяется с текущим state.
- summary_aspect — декоратор для финального шага конвейера. Помечает
  async-метод с той же сигнатурой, но возвращающий BaseResult.
  У действия может быть ровно один summary-аспект.

Оба декоратора записывают в метод атрибут _new_aspect_meta:
    {"type": "regular"|"summary", "description": "..."}

MetadataBuilder._collect_aspects(cls) обходит MRO класса, находит методы
с _new_aspect_meta и собирает их в ClassMetadata.aspects (tuple[AspectMeta]).
Порядок аспектов определяется порядком объявления в классе.

Структурные инварианты (проверяются MetadataBuilder):
- Не более одного summary-аспекта на класс.
- Если есть regular-аспекты, summary обязателен.
- Summary должен быть объявлен последним.
"""

from .aspect_gate_host import AspectGateHost
from .regular_aspect import regular_aspect
from .summary_aspect import summary_aspect

__all__ = [
    "AspectGateHost",
    "regular_aspect",
    "summary_aspect",
]
