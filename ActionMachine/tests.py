# ActionMachine/Logging/tests.py
"""
Тесты для системы логирования AOA.

Покрывают все компоненты: ReadableMixin.resolve, LogScope,
BaseLogger, ConsoleLogger, LogCoordinator.

Все тесты асинхронные, используют anyio.
Проверяют подстановку переменных, фильтрацию через регулярные
выражения, ANSI-раскраску, ленивое кеширование и рассылку
сообщений по цепочке координатор → логер.

Никакого подавления исключений — если логер сломан, тест падает.
Это сознательное решение в духе AOA [1].
"""

import sys
import os
from typing import Optional
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from ActionMachine.Core.ReadableMixin import ReadableMixin
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Context.UserInfo import UserInfo
from ActionMachine.Context.RequestInfo import RequestInfo
from ActionMachine.Context.EnvironmentInfo import EnvironmentInfo
from ActionMachine.Context.Context import Context
from ActionMachine.Logging.LogScope import LogScope
from ActionMachine.Logging.BaseLogger import BaseLogger
from ActionMachine.Logging.ConsoleLogger import ConsoleLogger
from ActionMachine.Logging.LogCoordinator import LogCoordinator


# =====================================================================
# Тестовые фикстуры и вспомогательные классы
# =====================================================================


@dataclass(frozen=True)
class TestParams(BaseParams):
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
        var: dict,
        context: Context,
        state: dict,
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
    """Тесты класса LogScope."""

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
        """Оператор in проверяет наличие ключа."""
        scope = LogScope(action="MyAction", aspect="load")
        assert "action" in scope
        assert "missing" not in scope

    def test_get_with_default(self) -> None:
        """get возвращает default для отсутствующего ключа."""
        scope = LogScope(action="MyAction")
        assert scope.get("action") == "MyAction"
        assert scope.get("missing", "fallback") == "fallback"

    def test_keys_values_items(self) -> None:
        """keys, values, items возвращают содержимое скоупа."""
        scope = LogScope(action="A", aspect="B")
        assert scope.keys() == ["action", "aspect"]
        assert scope.values() == ["A", "B"]
        assert scope.items() == [("action", "A"), ("aspect", "B")]

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
        params = TestParams()

        await logger.handle(scope, "Test message", {}, ctx, {}, params, 0)

        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "Test message"

    @pytest.mark.anyio
    async def test_handle_with_matching_filter(self) -> None:
        """Логер пропускает сообщение если фильтр совпал."""
        logger = RecordingLogger(filters=[r"TestAction"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await logger.handle(scope, "Hello", {}, ctx, {}, params, 0)

        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_with_non_matching_filter(self) -> None:
        """Логер отклоняет сообщение если ни один фильтр не совпал."""
        logger = RecordingLogger(filters=[r"PaymentAction"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await logger.handle(scope, "Hello", {}, ctx, {}, params, 0)

        assert len(logger.records) == 0

    @pytest.mark.anyio
    async def test_handle_filter_matches_on_first_hit(self) -> None:
        """Достаточно совпадения одного фильтра из нескольких."""
        logger = RecordingLogger(filters=[r"NoMatch", r"TestAction"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await logger.handle(scope, "Hello", {}, ctx, {}, params, 0)

        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_filter_checks_var(self) -> None:
        """Фильтр проверяется по var-переменным."""
        logger = RecordingLogger(filters=[r"amount=1500"])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

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
        params = TestParams()
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
        params = TestParams()

        await logger.write(scope, "Hello world", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "[MyAction.load] Hello world" in captured.out

    @pytest.mark.anyio
    async def test_write_with_indent(self, capsys: pytest.CaptureFixture[str]) -> None:
        """write добавляет отступ по уровню indent."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope(action="MyAction")
        ctx = make_context()
        params = TestParams()

        await logger.write(scope, "Indented", {}, ctx, {}, params, 3)

        captured = capsys.readouterr()
        assert captured.out.startswith("      ")  # 3 * "  " = 6 пробелов

    @pytest.mark.anyio
    async def test_write_without_scope(self, capsys: pytest.CaptureFixture[str]) -> None:
        """write без скоупа не выводит квадратные скобки."""
        logger = ConsoleLogger(use_colors=False)
        scope = LogScope()
        ctx = make_context()
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams()

        await logger.write(scope, "Clean text", {}, ctx, {}, params, 0)

        captured = capsys.readouterr()
        assert "\033[" not in captured.out


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
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams(amount=999.99)

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
        params = TestParams()

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
        params = TestParams()

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
    async def test_emit_missing_variable_shows_none(self) -> None:
        """emit подставляет <none> для несуществующей переменной."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await coordinator.emit(
            message="Missing: {%var.nonexistent}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Missing: <none>"

    @pytest.mark.anyio
    async def test_emit_missing_context_path_shows_none(self) -> None:
        """emit подставляет <none> для несуществующего пути в context."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await coordinator.emit(
            message="Deep: {%context.user.nonexistent.field}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Deep: <none>"

    @pytest.mark.anyio
    async def test_emit_unknown_namespace_shows_none(self) -> None:
        """emit подставляет <none> для неизвестного namespace."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await coordinator.emit(
            message="Unknown: {%unknown.field}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Unknown: <none>"

    @pytest.mark.anyio
    async def test_emit_no_variables_passes_message_as_is(self) -> None:
        """emit без переменных передаёт сообщение без изменений."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await coordinator.emit(
            message="Plain text without variables",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "Plain text without variables"

    @pytest.mark.anyio
    async def test_emit_multiple_variables(self) -> None:
        """emit подставляет несколько переменных из разных namespace."""
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context(user_id="user_42")
        params = TestParams(amount=100.0)

        await coordinator.emit(
            message="User {%context.user.user_id} paid {%params.amount} for {%var.item}",
            var={"item": "widget"},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert logger.records[0]["message"] == "User user_42 paid 100.0 for widget"

    @pytest.mark.anyio
    async def test_emit_broadcasts_to_all_loggers(self) -> None:
        """emit рассылает сообщение всем зарегистрированным логерам."""
        logger1 = RecordingLogger()
        logger2 = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger1, logger2])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams()

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
        params = TestParams(amount=1500.0)

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
    async def test_full_flow_with_none_substitution(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """
        Полный поток с <none> подстановкой.
        Координатор подставляет <none>, ConsoleLogger раскрашивает красным.
        """
        logger = ConsoleLogger(use_colors=True)
        coordinator = LogCoordinator(loggers=[logger])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

        await coordinator.emit(
            message="Missing value: {%var.missing}",
            var={},
            scope=scope,
            context=ctx,
            state={},
            params=params,
            indent=0,
        )

        captured = capsys.readouterr()
        assert "\033[31m<none>\033[0m" in captured.out

    @pytest.mark.anyio
    async def test_logger_exception_propagates(self) -> None:
        """
        Если логер падает, исключение летит наверх.
        Никакого подавления — сломанный логер = немедленное обнаружение.
        """

        class BrokenLogger(BaseLogger):
            async def write(self, scope, message, var, context, state, params, indent):
                raise RuntimeError("Logger is broken")

        coordinator = LogCoordinator(loggers=[BrokenLogger()])
        scope = LogScope(action="TestAction")
        ctx = make_context()
        params = TestParams()

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


if __name__ == "__main__": # type: ignore[no-untyped-def]
    pytest.main([__file__, "-v", "-s"])