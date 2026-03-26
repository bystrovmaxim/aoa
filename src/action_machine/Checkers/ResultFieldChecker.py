"""
Базовый класс для всех чекеров полей результата аспекта.

Назначение:
    Проверяет, что результат аспекта (словарь, возвращаемый из regular_aspect
    или summary_aspect) содержит поля с правильными типами и значениями.

Изменения по сравнению со старым BaseFieldChecker:
    - Класс переименован в ResultFieldChecker, чтобы явно указать,
      что чекер применяется к результату аспекта, а не к входным параметрам.
    - Удалена ветка для классов: чекеры теперь можно применять только к методам.
      Для валидации входных параметров используются типизированные Params (dataclass).

Использование:
    Применяется как декоратор к методам-аспектам:
        @regular_aspect("Обработка платежа")
        @ResultStringChecker("txn_id", "ID транзакции", required=True)
        async def process_payment(self, ...):
            return {"txn_id": txn_id}
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from action_machine.Core.Exceptions import ValidationFieldError


class ResultFieldChecker(ABC):
    """
    Абстрактный базовый класс для всех чекеров полей результата.

    Чекер может использоваться только как декоратор метода (аспекта).
    При применении к методу добавляет себя в список _result_checkers метода.
    Этот список собирается и обрабатывается в CheckerGateHost.

    Атрибуты:
        field_name: имя поля, которое проверяет данный чекер.
        required: является ли поле обязательным.
        desc: описание чекера.
    """

    def __init__(self, field_name: str, required: bool, desc: str) -> None:
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля, которое будет проверяться.
            required: если True, поле считается обязательным; при отсутствии значения
                      будет выброшено исключение ValidationFieldError.
            desc: описание чекера.
        """
        self.field_name = field_name
        self.required = required
        self.desc = desc

    def __call__(self, target: Callable[..., Any]) -> Callable[..., Any]:
        """
        Позволяет использовать экземпляр чекера как декоратор для метода.

        Проверяет, что target — вызываемый объект (метод). Добавляет чекер
        в атрибут _result_checkers метода. Это временный атрибут, который
        собирается в CheckerGateHost.__init_subclass__.

        Аргументы:
            target: декорируемый метод (аспект).

        Возвращает:
            тот же объект target (без изменений).

        Исключения:
            TypeError: если target не является вызываемым объектом (не методом).
        """
        # Проверка, что target — callable (метод)
        if not callable(target):
            raise TypeError(
                f"Чекер результата можно применять только к методам, "
                f"получен {type(target).__name__}"
            )

        # Добавляем чекер во временный список метода
        if not hasattr(target, "_result_checkers"):
            target._result_checkers = []  # type: ignore[attr-defined]
        target._result_checkers.append(self)  # type: ignore[attr-defined]
        return target

    @abstractmethod
    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Абстрактный метод, обязательный к переопределению в наследниках.
        Должен проверять тип значения и дополнительные ограничения.

        Исключения:
            ValidationFieldError: если проверка не пройдена.
        """
        pass

    def _check_required(self, value: Any) -> bool:
        """
        Проверяет обязательность поля и наличие значения.

        Аргументы:
            value: значение поля.

        Возвращает:
            True, если проверка обязательности пройдена и значение присутствует (или поле необязательно).

        Исключения:
            ValidationFieldError: если поле обязательно, но значение отсутствует.
        """
        if self.required and value is None:
            raise ValidationFieldError(
                f"Отсутствует обязательный параметр: '{self.field_name}'", field=self.field_name
            )
        return not self.required or value is not None

    def check(self, params: dict[str, Any]) -> None:
        """
        Выполняет проверку значения поля в словаре результата.

        Последовательность действий:
        1. Извлекает значение по field_name из params.
        2. Проверяет обязательность.
        3. Если поле необязательное и отсутствует – завершает проверку.
        4. Иначе вызывает _check_type_and_constraints.
        5. Если вложенная проверка выбрасывает исключение без поля, добавляет имя поля.

        Аргументы:
            params: словарь с результатом аспекта.

        Исключения:
            ValidationFieldError: при нарушении любого условия проверки.
        """
        value = params.get(self.field_name)

        if not self._check_required(value):
            return

        try:
            self._check_type_and_constraints(value)
        except ValidationFieldError as e:
            if not e.field:
                e.field = self.field_name
            raise