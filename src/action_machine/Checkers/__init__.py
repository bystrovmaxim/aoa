# src/action_machine/Checkers/__init__.py
"""
Пакет чекеров ActionMachine.

Содержит:
- CheckerGateHost — маркерный миксин, обозначающий поддержку декораторов
  чекеров на методах-аспектах. Наследуется BaseAction.
- StringFieldChecker — чекер, проверяющий строковое поле в результате
  аспекта (наличие, тип, длина и т.д.).

Чекеры применяются к методам-аспектам и валидируют словарь, возвращённый
аспектом. Каждый чекер записывает в метод атрибут _checker_meta:
    [{"checker_class": StringFieldChecker, "field_name": "txn_id",
      "description": "...", "required": True, ...}]

Один метод может иметь несколько чекеров (для разных полей).

MetadataBuilder._collect_checkers(cls) обходит MRO класса, находит методы
с _checker_meta и собирает их в ClassMetadata.checkers (tuple[CheckerMeta]).

ActionProductMachine при выполнении regular-аспекта:
1. Получает checkers = metadata.get_checkers_for_aspect(aspect_name).
2. Если чекеров нет и аспект вернул непустой dict — ошибка.
3. Если чекеры есть — проверяет, что результат содержит только
   объявленные поля, и применяет каждый чекер.
"""

from .checker_gate_host import CheckerGateHost
from .StringFieldChecker import StringFieldChecker

__all__ = [
    "CheckerGateHost",
    "StringFieldChecker",
]# src/action_machine/Checkers/__init__.py
"""
Пакет чекеров ActionMachine.

Содержит:
- CheckerGateHost — маркерный миксин, обозначающий поддержку декораторов
  чекеров на методах-аспектах. Наследуется BaseAction.
- StringFieldChecker — чекер, проверяющий строковое поле в результате
  аспекта (наличие, тип, длина и т.д.).

Чекеры применяются к методам-аспектам и валидируют словарь, возвращённый
аспектом. Каждый чекер записывает в метод атрибут _checker_meta:
    [{"checker_class": StringFieldChecker, "field_name": "txn_id",
      "description": "...", "required": True, ...}]

Один метод может иметь несколько чекеров (для разных полей).

MetadataBuilder._collect_checkers(cls) обходит MRO класса, находит методы
с _checker_meta и собирает их в ClassMetadata.checkers (tuple[CheckerMeta]).

ActionProductMachine при выполнении regular-аспекта:
1. Получает checkers = metadata.get_checkers_for_aspect(aspect_name).
2. Если чекеров нет и аспект вернул непустой dict — ошибка.
3. Если чекеры есть — проверяет, что результат содержит только
   объявленные поля, и применяет каждый чекер.
"""


__all__ = [
    "CheckerGateHost",
    "StringFieldChecker",
]