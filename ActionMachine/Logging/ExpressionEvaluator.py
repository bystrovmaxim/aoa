# ActionMachine/Logging/ExpressionEvaluator.py
"""
Вычислитель выражений для шаблонов логирования AOA.

Использует библиотеку simpleeval для безопасного вычисления
выражений внутри конструкции {iif(условие; истина; ложь)}.

simpleeval не поддерживает import, exec, eval, __builtins__
и любой доступ к файловой системе или сети. Это гарантирует
что шаблон логера не может выполнить произвольный код.

Вычислитель предоставляет:
- Операторы сравнения: ==, !=, >, <, >=, <=
- Логические операторы: and, or, not
- Арифметику: +, -, *, /
- Встроенные функции: len, upper, lower, format_number
- Строковые литералы, числа, bool (True/False)

Все переменные из контекста выполнения (var, state, params,
context, scope) доступны внутри выражений через литеральные
значения, подставленные координатором ДО вычисления iif.

Никакого подавления ошибок. Если выражение невалидно —
выбрасывается LogTemplateError. Ошибка в шаблоне лога —
это баг разработчика, который должен обнаруживаться
немедленно на первом же запуске.
"""

import re
from typing import Any, Dict, List

from simpleeval import EvalWithCompoundTypes  # type: ignore[import-untyped]

from ActionMachine.Core.Exceptions import LogTemplateError


# Регулярное выражение для поиска {iif(...)} в шаблоне.
# Используем нежадный захват с последующей проверкой баланса скобок.
_IIF_PATTERN: re.Pattern[str] = re.compile(
    r"\{iif\((.+?)\)\}"
)


# Набор безопасных функций, доступных внутри выражений.
# Каждая функция имеет явную сигнатуру и не выполняет IO.
_SAFE_FUNCTIONS: Dict[str, Any] = {
    "len": len,
    "upper": lambda s: str(s).upper(),
    "lower": lambda s: str(s).lower(),
    "str": str,
    "int": int,
    "float": float,
    "abs": abs,
    "format_number": lambda n, decimals=2: f"{float(n):,.{int(decimals)}f}",
}


class ExpressionEvaluator:
    """
    Безопасный вычислитель выражений для шаблонов логирования.

    Оборачивает simpleeval, предоставляя:
    - Набор безопасных функций (len, upper, lower, format_number).
    - Защиту от выполнения произвольного кода.
    - Метод evaluate для вычисления одного выражения.
    - Метод evaluate_iif для вычисления конструкции iif.
    - Метод process_template для обработки всех {iif(...)}
      в строке шаблона.

    НЕ подавляет исключения. Если выражение невалидно —
    выбрасывается LogTemplateError. Ошибка в шаблоне лога —
    это баг разработчика, который должен быть обнаружен
    немедленно. Это консистентно с философией AOA:
    логеры падают громко, и шаблоны тоже.
    """

    def evaluate(self, expression: str, names: Dict[str, Any]) -> Any:
        """
        Вычисляет одно выражение в контексте переменных.

        Аргументы:
            expression: строка выражения Python-подобного синтаксиса.
            names: словарь переменных, доступных в выражении.

        Возвращает:
            Результат вычисления (любой тип).

        Исключения:
            LogTemplateError: если выражение невалидно или содержит
                неопределённые переменные.

        Пример:
            >>> evaluator.evaluate("amount > 1000", {"amount": 1500})
            True
        """
        evaluator = EvalWithCompoundTypes(
            names=names,
            functions=_SAFE_FUNCTIONS,
        )
        try:
            return evaluator.eval(expression)
        except Exception as e:
            raise LogTemplateError(
                f"Ошибка вычисления выражения '{expression}': {e}"
            ) from e

    def evaluate_iif(
        self,
        raw_args: str,
        names: Dict[str, Any],
    ) -> str:
        """
        Вычисляет конструкцию iif(условие; истина; ложь).

        Разбирает строку аргументов по разделителю ';',
        вычисляет условие, и возвращает соответствующую
        ветку как строку.

        Поддерживает вложенные iif — если выбранная ветка
        начинается с "iif(", она обрабатывается рекурсивно
        через повторный вызов evaluate_iif. Также вложенные
        iif в формате {iif(...)} обрабатываются через
        process_template перед разбором аргументов.

        Аргументы:
            raw_args: строка вида "условие; значение_true; значение_false".
            names: словарь переменных для подстановки.

        Возвращает:
            Строковый результат выбранной ветки.

        Исключения:
            LogTemplateError: если:
                - количество аргументов iif не равно 3.
                - ошибка вычисления условия.
                - ошибка вычисления выбранной ветки.

        Пример:
            >>> evaluator.evaluate_iif(
            ...     "amount > 1000; 'КРУПНАЯ'; 'обычная'",
            ...     {"amount": 1500}
            ... )
            'КРУПНАЯ'
        """
        # Сначала обработаем вложенные iif в формате {iif(...)} в аргументах
        processed_args = self.process_template(raw_args, names)
        parts = self._split_iif_args(processed_args)

        if len(parts) != 3:
            raise LogTemplateError(
                f"iif ожидает 3 аргумента, разделённых ';', "
                f"получено {len(parts)}. "
                f"Выражение: iif({raw_args})"
            )

        condition_str = parts[0].strip()
        true_expr = parts[1].strip()
        false_expr = parts[2].strip()

        # Вычисляем условие — ошибка вычисления полетит как LogTemplateError
        # из метода evaluate.
        condition_result = self.evaluate(condition_str, names)

        chosen_expr = true_expr if condition_result else false_expr

        # Проверяем, является ли выбранная ветка вложенным вызовом iif
        # без фигурных скобок, например: iif(amount > 100000; 'HIGH'; 'LOW')
        # В этом случае рекурсивно вызываем evaluate_iif.
        stripped = chosen_expr.strip()
        if stripped.startswith("iif(") and stripped.endswith(")"):
            # Извлекаем аргументы вложенного iif — убираем "iif(" и ")"
            inner_args = stripped[4:-1]
            return self.evaluate_iif(inner_args, names)

        # Выбранная ветка может быть строковым литералом
        # в одинарных кавычках или выражением.
        # Ошибка вычисления полетит как LogTemplateError из метода evaluate.
        result = self.evaluate(chosen_expr, names)
        return str(result)

    def process_template(
        self,
        template: str,
        names: Dict[str, Any],
    ) -> str:
        """
        Обрабатывает все {iif(...)} в строке шаблона.

        Находит каждое вхождение {iif(...)}, вычисляет его
        через evaluate_iif и подставляет результат.

        Аргументы:
            template: строка шаблона с {iif(...)} конструкциями.
            names: словарь переменных для подстановки.

        Возвращает:
            Строка с вычисленными значениями вместо {iif(...)}.

        Исключения:
            LogTemplateError: если любое iif-выражение невалидно.

        Пример:
            >>> evaluator.process_template(
            ...     "Status: {iif(success == True; 'OK'; 'FAIL')}",
            ...     {"success": True}
            ... )
            'Status: OK'
        """
        def replacer(match: re.Match[str]) -> str:
            raw_args = match.group(1)
            return self.evaluate_iif(raw_args, names)

        return _IIF_PATTERN.sub(replacer, template)

    def _split_iif_args(self, raw: str) -> List[str]:
        """
        Разбивает аргументы iif по ';' с учётом вложенных
        скобок и строковых литералов.

        Простое split(';') не работает, потому что внутри
        может быть вложенный iif или строка с ';'.

        Аргументы:
            raw: строка аргументов без внешних скобок iif().

        Возвращает:
            Список из частей (в идеале 3 для корректного iif).
        """
        parts: List[str] = []
        current: List[str] = []
        depth = 0
        in_string = False
        string_char = ""

        for char in raw:
            if in_string:
                current.append(char)
                if char == string_char:
                    in_string = False
                continue

            if char in ("'", '"'):
                in_string = True
                string_char = char
                current.append(char)
                continue

            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == ";" and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(char)

        if current:
            parts.append("".join(current))

        return parts