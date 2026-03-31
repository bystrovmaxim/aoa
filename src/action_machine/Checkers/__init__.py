# src/action_machine/checkers/__init__.py
"""
Пакет чекеров ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит систему валидации полей результатов аспектов. Каждый чекер
представлен двумя компонентами:

1. **Класс чекера** (ResultStringChecker, ResultIntChecker и т.д.) —
   используется машиной для проверки словаря, возвращённого аспектом.
   Машина создаёт экземпляр из CheckerMeta и вызывает checker.check().

2. **Функция-декоратор** (result_string, result_int и т.д.) — применяется
   к методу-аспекту и записывает метаданные чекера в ``_checker_meta``.
   MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

Маркерный миксин:

- **CheckerGateHost** — маркерный миксин, обозначающий поддержку декораторов
  чекеров на методах-аспектах. Наследуется BaseAction.

Базовый класс:

- **ResultFieldChecker** — базовый абстрактный чекер для полей результата
  аспекта. Определяет общий интерфейс: check(), _check_type_and_constraints(),
  _get_extra_params().

Классы чекеров (используются машиной):

- **ResultStringChecker** — строковые поля (тип, длина, not_empty).
- **ResultIntChecker** — целочисленные поля (тип int, диапазон).
- **ResultFloatChecker** — числовые поля int/float (тип, диапазон).
- **ResultBoolChecker** — булевые поля (точное isinstance(value, bool)).
- **ResultDateChecker** — поля с датой (datetime или строка с форматом, диапазон).
- **ResultInstanceChecker** — проверка принадлежности значения указанному классу.

Функции-декораторы (применяются к методам-аспектам):

- **result_string** — объявляет строковое поле в результате аспекта.
- **result_int** — объявляет целочисленное поле.
- **result_float** — объявляет числовое поле (int/float).
- **result_bool** — объявляет булево поле.
- **result_date** — объявляет поле с датой.
- **result_instance** — объявляет поле-экземпляр класса.

═══════════════════════════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ С МЕТАДАННЫМИ
═══════════════════════════════════════════════════════════════════════════════

Функции-декораторы записывают в метод атрибут _checker_meta — список словарей:
    [{"checker_class": ResultStringChecker, "field_name": "txn_id",
      "required": True, ...}]

Один метод может иметь несколько чекеров (для разных полей).

MetadataBuilder._collect_checkers(cls) обходит MRO класса, находит методы
с _checker_meta и собирает их в ClassMetadata.checkers (tuple[CheckerMeta]).

ActionProductMachine при выполнении regular-аспекта:
1. Получает checkers = metadata.get_checkers_for_aspect(aspect_name).
2. Если чекеров нет и аспект вернул непустой dict — ошибка.
3. Если чекеры есть — проверяет, что результат содержит только
   объявленные поля, и применяет каждый чекер.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.checkers import result_string, result_int, result_float

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Обработка платежа")
        @result_string("txn_id", required=True, min_length=1)
        @result_float("charged_amount", required=True, min_value=0.0)
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id, "charged_amount": params.amount}

        @regular_aspect("Подсчёт бонусов")
        @result_int("bonus_points", required=True, min_value=0)
        async def calc_bonus(self, params, state, box, connections):
            return {"bonus_points": int(params.amount * 0.1)}
"""

from .checker_gate_host import CheckerGateHost
from .result_bool_checker import ResultBoolChecker, result_bool
from .result_date_checker import ResultDateChecker, result_date
from .result_field_checker import ResultFieldChecker
from .result_float_checker import ResultFloatChecker, result_float
from .result_instance_checker import ResultInstanceChecker, result_instance
from .result_int_checker import ResultIntChecker, result_int
from .result_string_checker import ResultStringChecker, result_string

__all__ = [
    # Маркерный миксин
    "CheckerGateHost",
    # Базовый класс
    "ResultFieldChecker",
    # Классы чекеров (используются машиной)
    "ResultStringChecker",
    "ResultIntChecker",
    "ResultFloatChecker",
    "ResultBoolChecker",
    "ResultDateChecker",
    "ResultInstanceChecker",
    # Функции-декораторы (применяются к методам-аспектам)
    "result_string",
    "result_int",
    "result_float",
    "result_bool",
    "result_date",
    "result_instance",
]
