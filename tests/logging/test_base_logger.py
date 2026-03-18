"""
Тесты абстрактного BaseLogger через RecordingLogger.
Проверяем:
- Фильтрацию сообщений по регулярным выражениям
- Передачу параметров в метод write
- Поведение без фильтров (принимает всё)
- Отклонение сообщений при несовпадении фильтров
"""
import pytest
from action_machine.Core.BaseState import BaseState
from tests.conftest import RecordingLogger


class TestBaseLogger:
    """Тесты абстрактного BaseLogger через RecordingLogger."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Без фильтров
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_handle_without_filters_passes_all(self, recording_logger, scope, context_fixture, params):
        """Без фильтров логер принимает все сообщения."""
        logger = recording_logger
        await logger.handle(scope, "Test message", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "Test message"
        assert logger.records[0]["scope"] is scope
        assert logger.records[0]["ctx"] is context_fixture
        assert logger.records[0]["params"] is params
        assert logger.records[0]["indent"] == 0

    @pytest.mark.anyio
    async def test_handle_multiple_calls_without_filters(self, recording_logger, scope, context_fixture, params):
        """Логер без фильтров обрабатывает несколько сообщений подряд."""
        logger = recording_logger
        await logger.handle(scope, "First", {}, context_fixture, BaseState(), params, 0)
        await logger.handle(scope, "Second", {}, context_fixture, BaseState(), params, 1)
        await logger.handle(scope, "Third", {}, context_fixture, BaseState(), params, 2)
        assert len(logger.records) == 3
        assert [r["message"] for r in logger.records] == ["First", "Second", "Third"]
        assert [r["indent"] for r in logger.records] == [0, 1, 2]

    # ------------------------------------------------------------------
    # ТЕСТЫ: С фильтрами
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_handle_with_matching_filter(self, scope, context_fixture, params):
        """Логер пропускает сообщение если фильтр совпал."""
        logger = RecordingLogger(filters=[r"TestAction"])
        # scope.action = "TestAction" (из фикстуры)
        await logger.handle(scope, "Hello", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "Hello"

    @pytest.mark.anyio
    async def test_handle_with_non_matching_filter(self, scope, context_fixture, params):
        """Логер отклоняет сообщение если ни один фильтр не совпал."""
        logger = RecordingLogger(filters=[r"PaymentAction"])
        # scope.action = "TestAction" — не совпадает
        await logger.handle(scope, "Hello", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 0

    @pytest.mark.anyio
    async def test_handle_filter_matches_on_first_hit(self, scope, context_fixture, params):
        """Достаточно совпадения одного фильтра из нескольких."""
        logger = RecordingLogger(
            filters=[
                r"NoMatch",
                r"TestAction",  # этот должен сработать
                r"AnotherNoMatch",
            ]
        )
        await logger.handle(scope, "Hello", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_filter_checks_var(self, scope, context_fixture, params):
        """Фильтр проверяется по var-переменным."""
        logger = RecordingLogger(filters=[r"amount=1500"])
        await logger.handle(scope, "Payment", {"amount": 1500, "user": "john"}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_filter_checks_message_text(self, scope, context_fixture, params):
        """Фильтр проверяется по тексту сообщения."""
        logger = RecordingLogger(filters=[r"ERROR|CRITICAL"])
        await logger.handle(scope, "INFO: всё хорошо", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 0
        await logger.handle(scope, "ERROR: что-то сломалось", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1
        await logger.handle(scope, "CRITICAL: система падает", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 2

    @pytest.mark.anyio
    async def test_handle_filter_checks_combined_string(self, scope, context_fixture, params):
        """Фильтр проверяется по комбинации scope + message + var."""
        logger = RecordingLogger(filters=[r"TestAction.*amount=1500"])
        await logger.handle(scope, "Processing payment", {"amount": 1500}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1
        await logger.handle(scope, "Processing payment", {"amount": 500}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1  # не добавилось

    # ------------------------------------------------------------------
    # ТЕСТЫ: Регулярные выражения в фильтрах
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_filter_with_regex_meta_characters(self, scope, context_fixture, params):
        """
        Фильтр поддерживает метасимволы регулярных выражений.
        BaseLogger использует re.search, который ищет совпадение
        в любом месте filter_string. Строка filter_string собирается как:
        "{scope.as_dotpath()} {message} {key=value ...}"
        Например: "TestAction.test.before Start middle end"
        Якоря ^ и $ работают относительно всей filter_string,
        поэтому ^Start не совпадёт, если строка начинается со scope.
        Используем re.search без якорей для поиска подстроки в сообщении.
        """
        logger = RecordingLogger(filters=[r"Start.*end"])
        await logger.handle(scope, "Start middle end", {}, context_fixture, BaseState(), params, 0)
        await logger.handle(scope, "Start middle", {}, context_fixture, BaseState(), params, 0)
        await logger.handle(scope, "middle end", {}, context_fixture, BaseState(), params, 0)
        # "Start middle end" — совпадает (содержит "Start...end")
        # "Start middle"     — не совпадает (нет "end" после "Start")
        # "middle end"       — не совпадает (нет "Start" перед "end")
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "Start middle end"

    @pytest.mark.anyio
    async def test_filter_with_or_condition(self, scope, context_fixture, params):
        """Фильтр поддерживает | (или) в регулярных выражениях."""
        logger = RecordingLogger(filters=[r"cat|dog"])
        await logger.handle(scope, "I have a cat", {}, context_fixture, BaseState(), params, 0)
        await logger.handle(scope, "I have a dog", {}, context_fixture, BaseState(), params, 0)
        await logger.handle(scope, "I have a bird", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 2
        assert logger.records[0]["message"] == "I have a cat"
        assert logger.records[1]["message"] == "I have a dog"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Передача параметров в write
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_handle_passes_all_params_to_write(self, scope, context_fixture, params):
        """write получает все параметры от handle."""
        logger = RecordingLogger()
        state = BaseState({"total": 100, "processed": True})
        var = {"key": "value", "count": 42}
        indent = 3
        await logger.handle(scope, "test message", var, context_fixture, state, params, indent)
        record = logger.records[0]
        assert record["scope"] is scope
        assert record["message"] == "test message"
        assert record["var"] == {"key": "value", "count": 42}
        assert record["ctx"] is context_fixture
        assert record["state"] == {"total": 100, "processed": True}
        assert record["params"] is params
        assert record["indent"] == indent

    @pytest.mark.anyio
    async def test_handle_preserves_var_original(self, scope, context_fixture, params):
        """handle не модифицирует исходный словарь var."""
        logger = RecordingLogger()
        original_var = {"key": "value"}
        var_copy = original_var.copy()
        await logger.handle(scope, "test", original_var, context_fixture, BaseState(), params, 0)
        assert original_var == var_copy  # не изменился
        assert logger.records[0]["var"] == {"key": "value"}

    @pytest.mark.anyio
    async def test_handle_preserves_state_original(self, scope, context_fixture, params):
        """handle не модифицирует исходное состояние state."""
        logger = RecordingLogger()
        original_state = BaseState({"total": 100})
        original_dict = original_state.to_dict()
        await logger.handle(scope, "test", {}, context_fixture, original_state, params, 0)
        # to_dict() возвращает копию — оригинал не изменился
        assert original_state.to_dict() == original_dict

    # ------------------------------------------------------------------
    # ТЕСТЫ: Разные типы значений в var
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_handle_with_complex_var_values(self, scope, context_fixture, params):
        """var может содержать сложные типы данных."""
        logger = RecordingLogger()
        var = {
            "string": "text",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
        }
        await logger.handle(scope, "complex", var, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1
        assert logger.records[0]["var"] == var

    # ------------------------------------------------------------------
    # ТЕСТЫ: Граничные случаи
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_handle_with_empty_filters_list(self, scope, context_fixture, params):
        """Пустой список фильтров означает 'принимать всё'."""
        logger = RecordingLogger(filters=[])
        await logger.handle(scope, "any message", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_with_none_filters(self, scope, context_fixture, params):
        """None в качестве фильтров означает 'принимать всё'."""
        logger = RecordingLogger(filters=None)
        await logger.handle(scope, "any message", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_handle_with_empty_message(self, scope, context_fixture, params):
        """Логер может обрабатывать пустые сообщения."""
        logger = RecordingLogger()
        await logger.handle(scope, "", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == ""

    @pytest.mark.anyio
    async def test_handle_with_empty_var(self, scope, context_fixture, params):
        """Логер может обрабатывать пустой словарь var."""
        logger = RecordingLogger()
        await logger.handle(scope, "test", {}, context_fixture, BaseState(), params, 0)
        assert len(logger.records) == 1
        assert logger.records[0]["var"] == {}