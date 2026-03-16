################################################################################
# Файл: ActionMachine/tests.py
################################################################################

# ActionMachine/tests.py
"""
Тесты для системы логирования AOA.

Покрывают все компоненты: ReadableMixin.resolve, LogScope,
BaseLogger, ConsoleLogger, LogCoordinator, ExpressionEvaluator.

Все тесты асинхронные, используют anyio.
Проверяют подстановку переменных, фильтрацию через регулярные
выражения, ANSI-раскраску, ленивое кеширование, рассылку
сообщений по цепочке координатор → логер, а также условную
логику iif в шаблонах.

Строгая политика ошибок: любая ошибка в шаблоне (несуществующая
переменная, невалидный iif, неизвестный namespace) выбрасывает
LogTemplateError. Тесты проверяют как успешные сценарии,
так и корректный выброс исключений при ошибках.

Никакого подавления исключений — если логер сломан, тест падает.
Это сознательное решение в духе AOA.
"""

import sys
import os
from typing import Optional, Any, Dict
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.Exceptions import LogTemplateError
from ActionMachine.Context.UserInfo import UserInfo
from ActionMachine.Context.RequestInfo import RequestInfo
from ActionMachine.Context.EnvironmentInfo import EnvironmentInfo
from ActionMachine.Context.Context import Context
from ActionMachine.Logging.LogScope import LogScope
from ActionMachine.Logging.BaseLogger import BaseLogger
from ActionMachine.Logging.ConsoleLogger import ConsoleLogger
from ActionMachine.Logging.LogCoordinator import LogCoordinator
from ActionMachine.Logging.ExpressionEvaluator import ExpressionEvaluator


# =====================================================================
# Тестовые фикстуры и вспомогательные классы
# =====================================================================

@dataclass(frozen=True)
class Params_Test(BaseParams):
    """Тестовые параметры для проверки подстановки переменных."""
    user_id: int = 42
    card_token: str = "tok_test_abc"
    amount: float = 1500.0


class RecordingLogger(BaseLogger):
    """
    Логер, записывающий все полученные сообщения в список.

    Используется в тестах для проверки того, что координатор
    корректно рассылает сообщения и что фильтрация работает.
    Не выводит ничего в консоль — только накапливает записи.
    """

    def __init__(self, filters: Optional[list[str]] = None) -> None:
        """
        Создаёт записывающий логер.

        Аргументы:
            filters: список регулярных выражений для фильтрации.
        """
        super().__init__(filters=filters)
        self.records: list[dict[str, Any]] = []

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: Dict[str, Any],
        context: Context,
        state: Dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Записывает сообщение в список records.

        Аргументы:
            scope: скоуп вызова.
            message: текст сообщения с подстановками.
            var: словарь переменных.
            context: контекст выполнения.
            state: состояние конвейера.
            params: входные параметры.
            indent: уровень отступа.
        """
        self.records.append({
            "scope": scope,
            "message": message,
            "var": var,
            "context": context,
            "state": state,
            "params": params,
            "indent": indent,
        })


def make_context(
    user_id: str = "agent_1",
    roles: Optional[list[str]] = None,
    trace_id: str = "trace-abc-123",
) -> Context:
    """
    Создаёт тестовый контекст с пользователем и запросом.

    Аргументы:
        user_id: идентификатор пользователя.
        roles: список ролей.
        trace_id: идентификатор трассировки.

    Возвращает:
        Готовый Context для использования в тестах.
    """
    user = UserInfo(
        user_id=user_id,
        roles=roles or ["user", "admin"],
        extra={"org": "acme"},
    )
    request = RequestInfo(
        trace_id=trace_id,
        request_path="/api/v1/orders",
        request_method="POST",
    )
    environment = EnvironmentInfo(
        hostname="pod-xyz-42",
        service_name="order-service",
        environment="production",
    )
    return Context(user=user, request=request, environment=environment)


# =====================================================================
# Тесты ReadableMixin.resolve
# =====================================================================

class TestReadableMixinResolve:
    """Тесты метода resolve в ReadableMixin."""

    def test_resolve_flat_field(self) -> None:
        """resolve возвращает значение плоского поля."""
        user = UserInfo(user_id="42", roles=["admin"])
        assert user.resolve("user_id") == "42"

    def test_resolve_nested_readable_mixin(self) -> None:
        """resolve обходит вложенные объекты с ReadableMixin."""
        ctx = make_context(user_id="agent_007")
        assert ctx.resolve("user.user_id") == "agent_007"

    def test_resolve_deep_nested(self) -> None:
        """resolve проходит по цепочке Context → UserInfo → extra (dict)."""
        ctx = make_context()
        assert ctx.resolve("user.extra.org") == "acme"

    def test_resolve_missing_returns_default(self) -> None:
        """resolve возвращает default если путь не найден."""
        user = UserInfo(user_id="42")
        assert user.resolve("nonexistent", default="<none>") == "<none>"

    def test_resolve_missing_nested_returns_default(self) -> None:
        """resolve возвращает default если промежуточный ключ не найден."""
        ctx = make_context()
        assert ctx.resolve("user.nonexistent.deep", default="N/A") == "N/A"

    def test_resolve_none_default_is_none(self) -> None:
        """resolve по умолчанию возвращает None для несуществующего пути."""
        user = UserInfo(user_id="42")
        assert user.resolve("missing") is None

    def test_resolve_caches_result(self) -> None:
        """resolve кеширует результат при повторном вызове."""
        user = UserInfo(user_id="42")
        result1 = user.resolve("user_id")
        result2 = user.resolve("user_id")
        assert result1 == result2 == "42"
        # Проверяем что кеш существует и содержит ключ
        assert "user_id" in user._resolve_cache

    def test_resolve_caches_default_for_missing(self) -> None:
        """resolve кеширует default для несуществующего пути."""
        user = UserInfo(user_id="42")
        user.resolve("missing", default="fallback")
        assert user._resolve_cache["missing"] == "fallback"

    def test_resolve_dict_inside_readable(self) -> None:
        """resolve проходит через dict внутри ReadableMixin."""
        user = UserInfo(extra={"nested": {"key": "value"}})
        assert user.resolve("extra.nested.key") == "value"

    def test_resolve_list_field(self) -> None:
        """resolve возвращает список как значение."""
        user = UserInfo(roles=["admin", "user"])
        result = user.resolve("roles")
        assert result == ["admin", "user"]


# =====================================================================
# Тесты LogScope
# =====================================================================

class TestLogScope:
    """
    Тесты класса LogScope.

    LogScope наследует collections.abc.Mapping, поэтому методы
    keys(), values(), items() возвращают view-объекты, а не списки.
    В тестах используем list() для приведения к спискам перед
    сравнением — это работает единообразно.
    """

    def test_as_dotpath_single_key(self) -> None:
        """as_dotpath для одного ключа возвращает его значение."""
        scope = LogScope(action="ProcessOrderAction")
        assert scope.as_dotpath() == "ProcessOrderAction"

    def test_as_dotpath_multiple_keys(self) -> None:
        """as_dotpath склеивает значения через точку в порядке вставки."""
        scope = LogScope(
            action="ProcessOrderAction",
            aspect="validate_user",
            event="before",
        )
        assert scope.as_dotpath() == "ProcessOrderAction.validate_user.before"

    def test_as_dotpath_empty_scope(self) -> None:
        """as_dotpath возвращает пустую строку для пустого скоупа."""
        scope = LogScope()
        assert scope.as_dotpath() == ""

    def test_as_dotpath_skips_empty_values(self) -> None:
        """as_dotpath пропускает пустые значения при склейке."""
        scope = LogScope(action="MyAction", aspect="", event="start")
        assert scope.as_dotpath() == "MyAction.start"

    def test_as_dotpath_cached(self) -> None:
        """as_dotpath кеширует результат при повторном вызове."""
        scope = LogScope(action="MyAction", aspect="load")
        result1 = scope.as_dotpath()
        result2 = scope.as_dotpath()
        assert result1 == result2 == "MyAction.load"
        assert scope._cached_path is not None

    def test_getitem(self) -> None:
        """Доступ по ключу через __getitem__."""
        scope = LogScope(action="MyAction")
        assert scope["action"] == "MyAction"

    def test_getitem_missing_raises_keyerror(self) -> None:
        """__getitem__ бросает KeyError для отсутствующего ключа."""
        scope = LogScope(action="MyAction")
        with pytest.raises(KeyError):
            _ = scope["missing"]

    def test_contains(self) -> None:
        """
        Оператор in проверяет наличие ключа.

        __contains__ автоматически предоставлен Mapping
        на основе __getitem__ и __iter__.
        """
        scope = LogScope(action="MyAction", aspect="load")
        assert "action" in scope
        assert "missing" not in scope

    def test_get_with_default(self) -> None:
        """
        get возвращает default для отсутствующего ключа.

        get() автоматически предоставлен Mapping
        на основе __getitem__.
        """
        scope = LogScope(action="MyAction")
        assert scope.get("action") == "MyAction"
        assert scope.get("missing", "fallback") == "fallback"

    def test_keys_values_items(self) -> None:
        """
        keys, values, items возвращают содержимое скоупа.

        Mapping возвращает view-объекты (KeysView, ValuesView,
        ItemsView), поэтому используем list() для приведения
        к спискам перед сравнением.
        """
        scope = LogScope(action="A", aspect="B")
        assert list(scope.keys()) == ["action", "aspect"]
        assert list(scope.values()) == ["A", "B"]
        assert list(scope.items()) == [("action", "A"), ("aspect", "B")]

    def test_to_dict_returns_copy(self) -> None:
        """to_dict возвращает копию, изменение не влияет на скоуп."""
        scope = LogScope(action="MyAction")
        d = scope.to_dict()
        d["action"] = "Modified"
        assert scope["action"] == "MyAction"

    def test_repr(self) -> None:
        """repr возвращает читаемое строковое представление."""
        scope = LogScope(action="MyAction")
        assert repr(scope) == "LogScope(action='MyAction')"

    def test_different_scope_lengths(self) -> None:
        """Скоупы могут иметь разную длину."""
        scope1 = LogScope(action="A")
        scope2 = LogScope(action="A", aspect="B", event="C")
        scope3 = LogScope(action="A", plugin="MetricsPlugin")
        assert scope1.as_dotpath() == "A"
        assert scope2.as_dotpath() == "A.B.C"
        assert scope3.as_dotpath() == "A.MetricsPlugin"

    def test_len(self) -> None:
        """
        len() возвращает количество ключей.

        __len__ — один из трёх обязательных методов Mapping,
        реализованный явно в LogScope.
        """
        scope = LogScope(action="A", aspect="B")
        assert len(scope) == 2
        assert len(LogScope()) == 0

    def test_iter(self) -> None:
        """
        iter() возвращает итератор по ключам в порядке добавления.

        __iter__ — один из трёх обязательных методов Mapping,
        реализованный явно в LogScope.
        """
        scope = LogScope(action="A", aspect="B", event="C")
        assert list(scope) == ["action", "aspect", "event"]


# =====================================================================
# Тесты BaseLogger (через RecordingLogger)
# =====================================================================

class TestBaseLogger:
    """Тесты абстрактного BaseLogger через RecordingLogger."""

    @pytest.mark.anyio
    async def test_handle_without_filters_passes_all(self) -> None:
        """Без фильтров логер принимает все сообщения."""
        logger = RecordingLogger()
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await logger.handle(scope, "Test message", {}, ctx, {}, params, 0)

        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "Test message"

    @pytest.mark.anyio
    async def test_handle_with_matching_filter(self) -> None:
        """Логер пропускает сообщение если фильтр совпал."""
        logger = RecordingLogger(filters=[r"TestAction"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await logger.handle(scope, "Hello", {}, ctx, {}, params, 0)

        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_with_non_matching_filter(self) -> None:
        """Логер отклоняет сообщение если ни один фильтр не совпал."""
        logger = RecordingLogger(filters=[r"PaymentAction"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await logger.handle(scope, "Hello", {}, ctx, {}, params, 0)

        assert len(logger.records) == 0

    @pytest.mark.anyio
    async def test_handle_filter_matches_on_first_hit(self) -> None:
        """Достаточно совпадения одного фильтра из нескольких."""
        logger = RecordingLogger(filters=[r"NoMatch", r"TestAction"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await logger.handle(scope, "Hello", {}, ctx, {}, params, 0)

        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_filter_checks_var(self) -> None:
        """Фильтр проверяется по var-переменным."""
        logger = RecordingLogger(filters=[r"amount=1500"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await logger.handle(
            scope, "Payment", {"amount": 1500}, ctx, {}, params, 0
        )

        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_passes_all_params_to_write(self) -> None:
        """write получает все параметры от handle."""
        logger = RecordingLogger()
        scope = LogScope(action="A", aspect="B")
        ctx = make_context()
        params = Params_Test()
        state = {"total": 100}
        var = {"key": "value"}

        await logger.handle(scope, "msg", var, ctx, state, params, 3)

        record = logger.records[0]
        assert record["scope"] is scope
        assert record["message"] == "msg"
        assert record["var"] == {"key": "value"}
        assert record["context"] is ctx
        assert record["state"] == {"total": 100}
        assert record["params"] is params
        assert record["indent"] == 3


# =====================================================================
# Тесты ConsoleLogger
# =====================================================================

class TestConsoleLogger:
    """Тесты ConsoleLogger."""

    @pytest.mark.anyio
    async def test_write_outputs_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """write выводит сообщение через print."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction", aspect="load")
        ctx = make_context()
        params = Params_Test()

        await logger.write(scope, "Hello world", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "[MyAction.load] Hello world" in captured.out

    @pytest.mark.anyio
    async def test_write_with_indent(self, capsys: pytest.CaptureFixture[str]) -> None:
        """write добавляет отступ по уровню indent."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = Params_Test()

        await logger.write(scope, "Indented", {}, ctx, {}, params, 3)

        captured = capsys.readouterr()
        assert captured.out.startswith("      ")  # 3 * "  " = 6 пробелов

    @pytest.mark.anyio
    async def test_write_without_scope(self, capsys: pytest.CaptureFixture[str]) -> None:
        """write без скоупа не выводит квадратные скобки."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope()
        ctx = make_context()
        params = Params_Test()

        await logger.write(scope, "No scope", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "No scope" in captured.out
        assert "[" not in captured.out

    @pytest.mark.anyio
    async def test_write_colorizes_none_marker(self, capsys: pytest.CaptureFixture[str]) -> None:
        """write раскрашивает <none> красным при use_colors=True."""
        logger = ConsoleLogger(use_colors=True)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = Params_Test()

        await logger.write(scope, "value=<none>", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        # Проверяем наличие ANSI-кода красного цвета вокруг <none>
        assert "\033[31m<none>\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_write_no_colors(self, capsys: pytest.CaptureFixture[str]) -> None:
        """write без цветов не содержит ANSI-кодов."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = Params_Test()

        await logger.write(scope, "Clean text", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[" not in captured.out


# =====================================================================
# Тесты ExpressionEvaluator
# =====================================================================

class TestExpressionEvaluator:
    """Тесты вычислителя выражений для iif."""

    # Указываем тип атрибута для pylint
    evaluator: ExpressionEvaluator

    def setup_method(self) -> None:
        self.evaluator = ExpressionEvaluator()

    def test_evaluate_simple_condition(self) -> None:
        """Проверка простого условия с числами."""
        names: Dict[str, Any] = {"amount": 1500}
        result = self.evaluator.evaluate("amount > 1000", names)
        assert result is True

        result = self.evaluator.evaluate("amount <= 1000", names)
        assert result is False

    def test_evaluate_string_comparison(self) -> None:
        """Проверка сравнения строк."""
        names: Dict[str, Any] = {"status": "active"}
        result = self.evaluator.evaluate("status == 'active'", names)
        assert result is True

        result = self.evaluator.evaluate("status != 'active'", names)
        assert result is False

    def test_evaluate_logical_operators(self) -> None:
        """Проверка логических операторов."""
        names = {"x": 5, "y": 10}
        result = self.evaluator.evaluate("x > 3 and y < 20", names)
        assert result is True

        result = self.evaluator.evaluate("x > 10 or y < 5", names)
        assert result is False

    def test_evaluate_builtin_functions(self) -> None:
        """Проверка встроенных функций len, upper, lower."""
        names = {"text": "Hello", "items": [1, 2, 3]}
        result = self.evaluator.evaluate("len(items)", names)
        assert result == 3

        result = self.evaluator.evaluate("upper(text)", names)
        assert result == "HELLO"

        result = self.evaluator.evaluate("lower(text)", names)
        assert result == "hello"

    def test_evaluate_format_number(self) -> None:
        """Проверка функции format_number."""
        names = {"value": 1234567.89}
        result = self.evaluator.evaluate("format_number(value, 0)", names)
        # Ожидаем "1,234,568" (округление)
        assert result == "1,234,568"

        result = self.evaluator.evaluate("format_number(value, 2)", names)
        assert result == "1,234,567.89"

    def test_iif_basic(self) -> None:
        """Проверка базовой конструкции iif."""
        names = {"amount": 1500}
        result = self.evaluator.evaluate_iif(
            "amount > 1000; 'HIGH'; 'LOW'", names
        )
        assert result == "HIGH"

        names2 = {"amount": 500}
        result = self.evaluator.evaluate_iif(
            "amount > 1000; 'HIGH'; 'LOW'", names2
        )
        assert result == "LOW"

    def test_iif_with_expressions_in_branches(self) -> None:
        """Проверка iif с выражениями в ветках."""
        names = {"value": 10}
        result = self.evaluator.evaluate_iif(
            "value > 5; value * 2; value / 2", names
        )
        assert result == "20"

        names2 = {"value": 2}
        result = self.evaluator.evaluate_iif(
            "value > 5; value * 2; value / 2", names2
        )
        assert result == "1.0"

    def test_iif_with_boolean_literals(self) -> None:
        """Проверка iif с булевыми литералами True/False."""
        names = {"success": True}
        result = self.evaluator.evaluate_iif(
            "success == True; 'OK'; 'FAIL'", names
        )
        assert result == "OK"

        names2 = {"success": False}
        result = self.evaluator.evaluate_iif(
            "success == True; 'OK'; 'FAIL'", names2
        )
        assert result == "FAIL"

    def test_iif_nested(self) -> None:
        """Проверка вложенных iif."""
        names = {"amount": 1500000}
        expr = "amount > 1000000; 'CRITICAL'; iif(amount > 100000; 'HIGH'; 'NORMAL')"
        result = self.evaluator.evaluate_iif(expr, names)
        assert result == "CRITICAL"

        names2 = {"amount": 500000}
        result = self.evaluator.evaluate_iif(expr, names2)
        assert result == "HIGH"

        names3 = {"amount": 50000}
        result = self.evaluator.evaluate_iif(expr, names3)
        assert result == "NORMAL"

    def test_iif_syntax_error_raises(self) -> None:
        """
        iif с неверным количеством аргументов выбрасывает LogTemplateError.

        Строгая политика: ошибка в шаблоне — это баг разработчика,
        который должен обнаруживаться немедленно.
        """
        names: Dict[str, Any] = {}
        with pytest.raises(LogTemplateError, match="iif ожидает 3 аргумента"):
            self.evaluator.evaluate_iif("amount > 1000; 'HIGH'", names)

    def test_iif_undefined_variable_raises(self) -> None:
        """
        Обращение к неопределённой переменной в iif выбрасывает LogTemplateError.

        Строгая политика: неопределённая переменная — это баг,
        а не ситуация для молчаливого маркера.
        """
        names: Dict[str, Any] = {}
        with pytest.raises(LogTemplateError, match="Ошибка вычисления выражения"):
            self.evaluator.evaluate_iif("missing > 10; 'yes'; 'no'", names)

    def test_evaluate_invalid_expression_raises(self) -> None:
        """
        Невалидное выражение в evaluate выбрасывает LogTemplateError.

        Синтаксическая ошибка в выражении — это баг в шаблоне,
        который должен падать громко.
        """
        with pytest.raises(LogTemplateError, match="Ошибка вычисления выражения"):
            self.evaluator.evaluate(">>>invalid<<<", {})

    def test_process_template_no_iif(self) -> None:
        """Шаблон без iif возвращается без изменений."""
        template = "Простое сообщение"
        result = self.evaluator.process_template(template, {})
        assert result == template

    def test_process_template_single_iif(self) -> None:
        """Шаблон с одним iif."""
        names = {"success": True}
        template = "Статус: {iif(success == True; 'OK'; 'FAIL')}"
        result = self.evaluator.process_template(template, names)
        assert result == "Статус: OK"

    def test_process_template_multiple_iif(self) -> None:
        """Шаблон с несколькими iif."""
        names = {"x": 5, "y": 10}
        template = "{iif(x > 3; 'A'; 'B')} и {iif(y < 5; 'C'; 'D')}"
        result = self.evaluator.process_template(template, names)
        assert result == "A и D"

    def test_process_template_invalid_iif_raises(self) -> None:
        """
        Невалидный iif внутри шаблона выбрасывает LogTemplateError.

        process_template не подавляет ошибки из evaluate_iif —
        исключение пробрасывается наверх.
        """
        with pytest.raises(LogTemplateError):
            self.evaluator.process_template(
                "Result: {iif(missing > 10; 'yes'; 'no')}", {}
            )

    def test_iif_with_literal_values(self) -> None:
        """
        Проверка iif с уже подставленными литеральными значениями.
        Это основной сценарий после перехода на стратегию
        подстановки значений ДО вычисления iif.
        simpleeval получает числа/строки как литералы, names={}.
        """
        # Числовое сравнение — значения уже подставлены как литералы
        result = self.evaluator.evaluate_iif(
            "1500.0 > 1000; 'HIGH'; 'LOW'", {}
        )
        assert result == "HIGH"

        result = self.evaluator.evaluate_iif(
            "500.0 > 1000; 'HIGH'; 'LOW'", {}
        )
        assert result == "LOW"

    def test_iif_with_literal_string_comparison(self) -> None:
        """
        Проверка iif со строковым сравнением через литералы.
        Строки подставляются в кавычках координатором.
        """
        result = self.evaluator.evaluate_iif(
            "'admin' == 'admin'; 'ROOT'; 'USER'", {}
        )
        assert result == "ROOT"

        result = self.evaluator.evaluate_iif(
            "'agent_1' == 'admin'; 'ROOT'; 'USER'", {}
        )
        assert result == "USER"

    def test_iif_with_literal_bool(self) -> None:
        """
        Проверка iif с булевыми литералами.
        Bool подставляется как True/False.
        """
        result = self.evaluator.evaluate_iif(
            "True == True; 'OK'; 'FAIL'", {}
        )
        assert result == "OK"

        result = self.evaluator.evaluate_iif(
            "False == True; 'OK'; 'FAIL'", {}
        )
        assert result == "FAIL"


# =====================================================================
# Тесты LogCoordinator
# =====================================================================

class TestLogCoordinator:
    """Тесты координатора логирования."""

    @pytest.mark.anyio
    async def test_emit_substitutes_var(self) -> None:
        """emit подставляет переменные из var."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Count is {%var.count}",
            var={"count": 42},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Count is 42"

    @pytest.mark.anyio
    async def test_emit_substitutes_context(self) -> None:
        """emit подставляет переменные из context через resolve."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context(user_id="agent_007")
        params = Params_Test()

        await coordinator.emit(
            message="User: {%context.user.user_id}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "User: agent_007"

    @pytest.mark.anyio
    async def test_emit_substitutes_params(self) -> None:
        """emit подставляет переменные из params через resolve."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test(amount=999.99)

        await coordinator.emit(
            message="Amount: {%params.amount}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Amount: 999.99"

    @pytest.mark.anyio
    async def test_emit_substitutes_state(self) -> None:
        """emit подставляет переменные из state (dict)."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Total: {%state.total}",
            var={},
            scope=scope,
            context=ctx,
            state={"total": 1500.0},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Total: 1500.0"

    @pytest.mark.anyio
    async def test_emit_substitutes_scope(self) -> None:
        """emit подставляет переменные из scope."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="ProcessOrder", aspect="validate")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Action: {%scope.action}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Action: ProcessOrder"

    @pytest.mark.anyio
    async def test_emit_with_iif_simple(self) -> None:
        """emit обрабатывает простой iif с единым синтаксисом {%...}."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test(amount=1500.0)

        await coordinator.emit(
            message="Risk: {iif({%params.amount} > 1000; 'HIGH'; 'LOW')}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Risk: HIGH"

        params2 = Params_Test(amount=500.0)
        await coordinator.emit(
            message="Risk: {iif({%params.amount} > 1000; 'HIGH'; 'LOW')}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params2,
            indent=0,
        )

        assert logger.records[1]["message"] == "Risk: LOW"

    @pytest.mark.anyio
    async def test_emit_with_iif_using_var(self) -> None:
        """iif использует переменные из var (с булевыми значениями)."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Result: {iif({%var.success} == True; 'OK'; 'FAIL')}",
            var={"success": True},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Result: OK"

    @pytest.mark.anyio
    async def test_emit_with_iif_nested(self) -> None:
        """emit обрабатывает вложенные iif с единым синтаксисом."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test(amount=1500000.0)

        await coordinator.emit(
            message="Level: {iif({%params.amount} > 1000000; 'CRITICAL'; iif({%params.amount} > 100000; 'HIGH'; 'LOW'))}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Level: CRITICAL"

        params2 = Params_Test(amount=500000.0)
        await coordinator.emit(
            message="Level: {iif({%params.amount} > 1000000; 'CRITICAL'; iif({%params.amount} > 100000; 'HIGH'; 'LOW'))}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params2,
            indent=0,
        )

        assert logger.records[1]["message"] == "Level: HIGH"

    @pytest.mark.anyio
    async def test_emit_with_iif_combined_with_variables(self) -> None:
        """Смешанное использование {%...} и iif — единый синтаксис."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test(amount=1500.0)

        await coordinator.emit(
            message="{iif({%params.amount} > 1000; 'КРУПНАЯ'; 'Обычная')} операция на сумму {%params.amount}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "КРУПНАЯ операция на сумму 1500.0"

    @pytest.mark.anyio
    async def test_emit_missing_variable_raises(self) -> None:
        """
        Обращение к несуществующей переменной выбрасывает LogTemplateError.

        Строгая политика: ошибка в шаблоне — это баг разработчика.
        Никаких молчаливых <none> маркеров. Система падает громко,
        чтобы баг обнаруживался на первом же запуске.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Missing: {%var.nonexistent}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_missing_variable_in_iif_raises(self) -> None:
        """
        Обращение к несуществующей переменной внутри iif
        выбрасывает LogTemplateError.

        Единый синтаксис {%...} внутри iif — те же правила:
        переменная не найдена → LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Result: {iif({%var.missing} > 10; 'yes'; 'no')}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_unknown_namespace_raises(self) -> None:
        """
        Неизвестный namespace в шаблоне выбрасывает LogTemplateError.

        Допустимые namespace: var, state, scope, context, params.
        Любой другой — немедленная ошибка.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="Неизвестный namespace"):
            await coordinator.emit(
                message="Value: {%unknown.field}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_invalid_iif_syntax_raises(self) -> None:
        """
        Невалидный синтаксис iif (не 3 аргумента) выбрасывает LogTemplateError.

        Ошибка в iif — баг в шаблоне. Система падает громко.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="iif ожидает 3 аргумента"):
            await coordinator.emit(
                message="Bad: {iif(1 > 0; 'only_two_args')}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_with_iif_using_state(self) -> None:
        """iif использует переменные из state с единым синтаксисом."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Status: {iif({%state.processed} == True; 'DONE'; 'PENDING')}",
            var={},
            scope=scope,
            context=ctx,
            state={"processed": True},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Status: DONE"

    @pytest.mark.anyio
    async def test_emit_with_iif_using_scope(self) -> None:
        """iif использует переменные из scope с единым синтаксисом."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="ProcessOrder", aspect="validate")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Scope: {iif({%scope.aspect} == 'validate'; 'VALIDATION'; {%scope.aspect})}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Scope: VALIDATION"

    @pytest.mark.anyio
    async def test_emit_multiple_iif(self) -> None:
        """Шаблон с несколькими iif."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test(amount=1500.0)  # 1500 % 2 == 0 → even

        await coordinator.emit(
            message="{iif({%params.amount} > 1000; 'BIG'; 'small')} and {iif({%params.amount} % 2 == 0; 'even'; 'odd')}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "BIG and even"

    @pytest.mark.anyio
    async def test_emit_no_iif_passes_through(self) -> None:
        """Шаблон без iif передаётся без изменений (после подстановки переменных)."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Plain text without iif",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Plain text without iif"

    @pytest.mark.anyio
    async def test_emit_broadcasts_to_all_loggers(self) -> None:
        """emit рассылает сообщение всем зарегистрированным логерам."""
        logger1 = RecordingLogger()
        logger2 = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger1, logger2])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Broadcast",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert len(logger1.records) == 1
        assert len(logger2.records) == 1
        assert logger1.records[0]["message"] == "Broadcast"
        assert logger2.records[0]["message"] == "Broadcast"

    @pytest.mark.anyio
    async def test_emit_respects_logger_filters(self) -> None:
        """emit вызывает все логеры, но каждый фильтрует самостоятельно."""
        logger_all = RecordingLogger()  # без фильтров — принимает всё
        logger_payment = RecordingLogger(filters=[r"PaymentAction"])  # только Payment
        coordinator = LogCoordinator(loggers=[logger_all, logger_payment])
        scope = LogScope(action="OrderAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Order created",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert len(logger_all.records) == 1  # принял
        assert len(logger_payment.records) == 0  # отклонил

    @pytest.mark.anyio
    async def test_add_logger(self) -> None:
        """add_logger добавляет логер в координатор."""
        coordinator = LogCoordinator()
        logger = RecordingLogger()
        coordinator.add_logger(logger)

        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="After add",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_emit_without_loggers_does_nothing(self) -> None:
        """emit без логеров не падает."""
        coordinator = LogCoordinator()
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        # Не должно выбросить исключение
        await coordinator.emit(
            message="No loggers",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

    @pytest.mark.anyio
    async def test_emit_passes_indent_to_loggers(self) -> None:
        """emit передаёт indent в каждый логер."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Indented",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=5,
        )

        assert logger.records[0]["indent"] == 5

    @pytest.mark.anyio
    async def test_emit_nested_state_dict(self) -> None:
        """emit подставляет вложенные значения из state."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Nested: {%state.order.id}",
            var={},
            scope=scope,
            context=ctx,
            state={"order": {"id": 42}},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Nested: 42"

    @pytest.mark.anyio
    async def test_emit_nested_var_dict(self) -> None:
        """emit подставляет вложенные значения из var."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Var nested: {%var.data.value}",
            var={"data": {"value": "deep"}},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Var nested: deep"

    @pytest.mark.anyio
    async def test_emit_with_iif_string_comparison(self) -> None:
        """iif корректно сравнивает строковые значения из context."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context(user_id="admin")
        params = Params_Test()

        await coordinator.emit(
            message="Role: {iif({%context.user.user_id} == 'admin'; 'ROOT'; 'USER')}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Role: ROOT"

    @pytest.mark.anyio
    async def test_emit_with_iif_string_comparison_no_match(self) -> None:
        """iif корректно обрабатывает несовпадение строк."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context(user_id="agent_1")
        params = Params_Test()

        await coordinator.emit(
            message="Role: {iif({%context.user.user_id} == 'admin'; 'ROOT'; 'USER')}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Role: USER"

    @pytest.mark.anyio
    async def test_emit_with_iif_var_number(self) -> None:
        """iif корректно работает с числовыми переменными из var."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        await coordinator.emit(
            message="Size: {iif({%var.count} > 100; 'LARGE'; 'SMALL')}",
            var={"count": 200},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Size: LARGE"

    @pytest.mark.anyio
    async def test_emit_missing_nested_variable_raises(self) -> None:
        """
        Обращение к несуществующему вложенному пути выбрасывает LogTemplateError.

        Например, {%state.order.id} когда state={} — переменная
        не найдена, LogTemplateError немедленно.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Value: {%state.order.id}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_missing_params_field_raises(self) -> None:
        """
        Обращение к несуществующему полю params выбрасывает LogTemplateError.

        Params_Test не имеет поля 'nonexistent', resolve вернёт None,
        координатор выбросит LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Value: {%params.nonexistent}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_missing_context_path_raises(self) -> None:
        """
        Обращение к несуществующему пути в context выбрасывает LogTemplateError.

        context.resolve("user.nonexistent") вернёт None,
        координатор выбросит LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Value: {%context.user.nonexistent}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_missing_scope_key_raises(self) -> None:
        """
        Обращение к несуществующему ключу scope выбрасывает LogTemplateError.

        scope.get("missing") вернёт None, координатор выбросит LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Value: {%scope.missing}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )


# =====================================================================
# Тесты интеграции: координатор + консольный логер
# =====================================================================

class TestIntegration:
    """Интеграционные тесты: координатор + ConsoleLogger."""

    @pytest.mark.anyio
    async def test_full_flow_console_no_colors(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """
        Полный поток: координатор подставляет переменные,
        ConsoleLogger выводит в консоль без цветов.
        """
        logger = ConsoleLogger(use_colors=False)
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="ProcessOrder", aspect="charge")
        ctx = make_context(user_id="user_42")
        params = Params_Test(amount=1500.0)

        await coordinator.emit(
            message="Charged {%params.amount} for user {%context.user.user_id}",
            var={"receipt": "R-001"},
            scope=scope,
            context=ctx,
            state={"total": 1500.0},
            params=params,
            indent=1,
        )

        captured = capsys.readouterr()
        assert "Charged 1500.0 for user user_42" in captured.out
        assert "[ProcessOrder.charge]" in captured.out
        # Проверяем отступ (indent=1 → "  ")
        assert captured.out.startswith("  ")

    @pytest.mark.anyio
    async def test_full_flow_with_iif(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """
        Полный поток с iif в шаблоне — единый синтаксис {%...}.
        """
        logger = ConsoleLogger(use_colors=False)
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="ProcessOrder", aspect="charge")
        ctx = make_context(user_id="user_42")
        params = Params_Test(amount=1500000.0)

        await coordinator.emit(
            message="{iif({%params.amount} > 1000000; '🚨 КРИТИЧЕСКАЯ'; 'Обычная')} транзакция на сумму {%params.amount}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=1,
        )

        captured = capsys.readouterr()
        assert "🚨 КРИТИЧЕСКАЯ транзакция на сумму 1500000.0" in captured.out

    @pytest.mark.anyio
    async def test_full_flow_missing_variable_raises(
        self,
    ) -> None:
        """
        Полный поток с отсутствующей переменной.
        Координатор выбрасывает LogTemplateError, до логера
        сообщение не доходит. Строгая политика.
        """
        logger = ConsoleLogger(use_colors=True)
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Missing value: {%var.missing}",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_logger_exception_propagates(self) -> None:
        """
        Если логер падает, исключение летит наверх.
        Никакого подавления — сломанный логер = немедленное обнаружение.
        """

        class BrokenLogger(BaseLogger):
            async def write(self, scope: LogScope, message: str, var: Dict[str, Any],
                            context: Context, state: Dict[str, Any],
                            params: BaseParams, indent: int) -> None:
                raise RuntimeError("Logger is broken")

        coordinator = LogCoordinator(loggers=[BrokenLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = Params_Test()

        with pytest.raises(RuntimeError, match="Logger is broken"):
            await coordinator.emit(
                message="This should fail",
                var={},
                scope=scope,
                context=ctx,
                state={},
                params=params,
                indent=0,
            )


# =====================================================================
# Запуск
# =====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])