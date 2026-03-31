# src/action_machine/checkers/__init__.py
"""
Пакет чекеров ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит систему валидации полей результатов аспектов. Чекеры применяются
как декораторы к методам-аспектам и проверяют словарь, возвращённый аспектом,
на соответствие объявленным полям.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- CheckerGateHost — маркерный миксин, обозначающий поддержку декораторов
  чекеров на методах-аспектах. Наследуется BaseAction.

- ResultFieldChecker — базовый абстрактный чекер для полей результата аспекта.
  Определяет общий интерфейс: check(), _check_type_and_constraints(),
  _get_extra_params(). Поддерживает двойной режим: декоратор метода-аспекта
  и валидатор dict.

- ResultStringChecker — чекер для строковых полей (наличие, тип, длина,
  not_empty, min_length, max_length).

- ResultIntChecker — чекер для целочисленных полей (тип int, диапазон
  min_value/max_value).

- ResultFloatChecker — чекер для числовых полей int/float (тип, диапазон
  min_value/max_value).

- ResultBoolChecker — чекер для булевых полей (точное isinstance(value, bool),
  числа и строки не принимаются).

- ResultDateChecker — чекер для полей с датой (datetime или строка
  с указанным форматом, диапазон min_date/max_date).

- ResultInstanceChecker — чекер для проверки принадлежности значения
  указанному классу или кортежу классов.

═══════════════════════════════════════════════════════════════════════════════
ДВОЙНОЙ РЕЖИМ РАБОТЫ ЧЕКЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Все чекеры поддерживают два режима:

1. Как декоратор метода-аспекта (порядок с @regular_aspect не важен):

    @regular_aspect("Обработка платежа")
    @ResultStringChecker("txn_id", required=True)
    async def process_payment(self, params, state, box, connections):
        return {"txn_id": txn_id}

2. Как валидатор результата (вызывается машиной):

    checker = ResultStringChecker("txn_id", required=True)
    checker.check({"txn_id": txn_id})

═══════════════════════════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ С МЕТАДАННЫМИ
═══════════════════════════════════════════════════════════════════════════════

Каждый чекер записывает в метод атрибут _checker_meta:
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
"""

from .checker_gate_host import CheckerGateHost
from .result_bool_checker import ResultBoolChecker
from .result_date_checker import ResultDateChecker
from .result_field_checker import ResultFieldChecker
from .result_float_checker import ResultFloatChecker
from .result_instance_checker import ResultInstanceChecker
from .result_int_checker import ResultIntChecker
from .result_string_checker import ResultStringChecker

__all__ = [
    "CheckerGateHost",
    "ResultFieldChecker",
    "ResultStringChecker",
    "ResultIntChecker",
    "ResultFloatChecker",
    "ResultBoolChecker",
    "ResultDateChecker",
    "ResultInstanceChecker",
]
