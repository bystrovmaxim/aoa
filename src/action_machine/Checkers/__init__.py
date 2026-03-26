# src/action_machine/Checkers/__init__.py
"""
Пакет чекеров ActionMachine.

Содержит:
- CheckerGateHost — маркерный миксин, обозначающий поддержку декораторов
  чекеров на методах-аспектах. Наследуется BaseAction.
- ResultStringChecker — чекер, проверяющий строковое поле в результате
  аспекта (наличие, тип, длина и т.д.).
- ResultIntChecker — чекер для целочисленных полей результата аспекта.
- ResultFloatChecker — чекер для числовых полей (int/float) результата аспекта.
- ResultBoolChecker — чекер для булевых полей результата аспекта.
- ResultDateChecker — чекер для полей с датой результата аспекта.
- ResultInstanceChecker — чекер для проверки принадлежности значения классу.
- ResultFieldChecker — базовый абстрактный чекер для полей результата аспекта.

Чекеры применяются как декораторы к методам-аспектам и валидируют словарь,
возвращённый аспектом. Каждый чекер записывает в метод атрибут _checker_meta:
    [{"checker_class": ResultStringChecker, "field_name": "txn_id",
      "description": "...", "required": True, ...}]

Один метод может иметь несколько чекеров (для разных полей).

MetadataBuilder._collect_checkers(cls) обходит MRO класса, находит методы
с _checker_meta и собирает их в ClassMetadata.checkers (tuple[CheckerMeta]).

ActionProductMachine при выполнении regular-аспекта:
1. Получает checkers = metadata.get_checkers_for_aspect(aspect_name).
2. Если чекеров нет и аспект вернул непустой dict — ошибка.
3. Если чекеры есть — проверяет, что результат содержит только
   объявленные поля, и применяет каждый чекер.

Важно: чекеры уровня класса (старый StringFieldChecker и подобные) —
запрещены. Допускаются только Result*Checker, применяемые как декораторы
к методам-аспектам.
"""

from .checker_gate_host import CheckerGateHost
from .result_string_checker import ResultStringChecker

__all__ = [
    "CheckerGateHost",
    "ResultStringChecker",
]
