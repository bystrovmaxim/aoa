# ActionMachine/Logging/ExpressionEvaluator.py
"""
Вычислитель выражений для шаблонов логирования AOA.

Использует библиотеку simpleeval для безопасного вычисления
выражений внутри конструкции {iif(условие; истина; ложь)}.

simpleeval не поддерживает import, exec, eval, __builtins__
и любой доступ к файловой системе или сети. Это гарантирует,
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

Парсинг аргументов iif выполняется отдельным классом _IifArgSplitter,
который корректно обрабатывает вложенные скобки и строковые литералы.
"""

import re
from typing import Any

from simpleeval import EvalWithCompoundTypes  # type: ignore[import-untyped]

from action_machine.Core.Exceptions import LogTemplateError

# Регулярное выражение для поиска {iif(...)} в шаблоне.
# Используем нежадный захват с последующей проверкой баланса скобок.
_IIF_PATTERN: re.Pattern[str] = re.compile(r"\{iif\((.+?)\)\}")


# Набор безопасных функций, доступных внутри выражений.
# Каждая функция имеет явную сигнатуру и не выполняет IO.
_SAFE_FUNCTIONS: dict[str, Any] = {
    "len": len,
    "upper": lambda s: str(s).upper(),
    "lower": lambda s: str(s).lower(),
    "str": str,
    "int": int,
    "float": float,
    "abs": abs,
    "format_number": lambda n, decimals=2: f"{float(n):,.{int(decimals)}f}",
}


class _IifArgSplitter:
    """
    Разбивает аргументы iif по ';' с учётом вложенных скобок
    и строковых литералов.

    Простое split(';') не работает, потому что внутри
    может быть вложенный iif или строка с ';'.

    Принцип работы:
    1. Итерируемся по символам входной строки.
    2. Если мы внутри строкового литерала — накапливаем символы
       до закрывающей кавычки (_handle_string_char).
    3. Если встретили открывающую кавычку — входим в режим
       строкового литерала (_handle_quote).
    4. Иначе обрабатываем структурные символы: скобки
       изменяют глубину, ';' на нулевой глубине разделяет
       аргументы (_handle_structural_char).
    """

    def __init__(self, raw: str) -> None:
        """
        Инициализирует парсер.

        Аргументы:
            raw: строка аргументов iif без внешних скобок.
                 Например: "amount > 1000; 'HIGH'; 'LOW'".
        """
        self._raw = raw
        self._parts: list[str] = []
        self._current: list[str] = []
        self._depth: int = 0
        self._in_string: bool = False
        self._string_char: str = ""

    def _handle_string_char(self, char: str) -> bool:
        """
        Обрабатывает символ, если мы находимся внутри строкового литерала.

        Внутри строкового литерала все символы накапливаются без
        интерпретации. Единственный особый символ — закрывающая
        кавычка (совпадающая с открывающей), которая завершает
        строковый режим.

        Аргументы:
            char: текущий символ для обработки.

        Возвращает:
            True если символ был обработан (мы внутри строки),
            False если мы не в строковом режиме и символ
            должен быть обработан другим методом.
        """
        if not self._in_string:
            return False
        self._current.append(char)
        if char == self._string_char:
            self._in_string = False
        return True

    def _handle_quote(self, char: str) -> bool:
        """
        Обрабатывает открывающую кавычку (одинарную или двойную).

        Если символ является кавычкой, включает режим строкового
        литерала. Все последующие символы будут накапливаться
        без интерпретации до закрывающей кавычки.

        Аргументы:
            char: текущий символ для проверки.

        Возвращает:
            True если символ был кавычкой и обработан,
            False если символ не является кавычкой.
        """
        if char not in ("'", '"'):
            return False
        self._in_string = True
        self._string_char = char
        self._current.append(char)
        return True

    def _handle_structural_char(self, char: str) -> None:
        """
        Обрабатывает структурные символы: скобки и разделитель ';'.

        Открывающая скобка '(' увеличивает глубину вложенности.
        Закрывающая скобка ')' уменьшает глубину вложенности.
        Точка с запятой ';' на нулевой глубине завершает текущий
        аргумент и начинает новый. На ненулевой глубине ';'
        является частью вложенного выражения и просто накапливается.
        Все остальные символы накапливаются в текущий аргумент.

        Аргументы:
            char: текущий символ для обработки.
        """
        if char == "(":
            self._depth += 1
            self._current.append(char)
        elif char == ")":
            self._depth -= 1
            self._current.append(char)
        elif char == ";" and self._depth == 0:
            # Разделитель аргументов на верхнем уровне —
            # завершаем текущий аргумент и начинаем новый.
            self._parts.append("".join(self._current))
            self._current = []
        else:
            self._current.append(char)

    def split(self) -> list[str]:
        """
        Выполняет разбиение строки аргументов и возвращает список частей.

        Итерируется по каждому символу входной строки, применяя
        обработчики в порядке приоритета:
        1. _handle_string_char — если мы внутри строкового литерала.
        2. _handle_quote — если символ является открывающей кавычкой.
        3. _handle_structural_char — для скобок, ';' и обычных символов.

        После обхода всех символов добавляет последний накопленный
        аргумент (если он не пуст) в список результатов.

        Возвращает:
            Список строк — аргументы iif (в идеале 3 для корректного iif).

        Пример:
            >>> _IifArgSplitter("amount > 1000; 'HIGH'; 'LOW'").split()
            ["amount > 1000", " 'HIGH'", " 'LOW'"]
        """
        for char in self._raw:
            # Приоритет 1: символ внутри строкового литерала.
            if self._handle_string_char(char):
                continue
            # Приоритет 2: открывающая кавычка.
            if self._handle_quote(char):
                continue
            # Приоритет 3: структурные символы (скобки, ';', остальное).
            self._handle_structural_char(char)

        # Добавляем последний накопленный аргумент.
        if self._current:
            self._parts.append("".join(self._current))

        return self._parts


class expression_evaluator:
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
    немедленно.
    """

    def evaluate(self, expression: str, names: dict[str, Any]) -> Any:
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
            raise LogTemplateError(f"Ошибка вычисления выражения '{expression}': {e}") from e

    def evaluate_iif(
        self,
        raw_args: str,
        names: dict[str, Any],
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
                f"iif ожидает 3 аргумента, разделённых ';', получено {len(parts)}. Выражение: iif({raw_args})"
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
        names: dict[str, Any],
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

    def _split_iif_args(self, raw: str) -> list[str]:
        """
        Разбивает аргументы iif через выделенный парсер _IifArgSplitter.

        Делегирует всю логику парсинга классу _IifArgSplitter,
        который отслеживает глубину скобок и строковые литералы.

        Аргументы:
            raw: строка аргументов без внешних скобок iif().

        Возвращает:
            Список из частей (в идеале 3 для корректного iif).
        """
        return _IifArgSplitter(raw).split()
