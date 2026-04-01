# tests/testing/test_comparison.py
"""
Тесты для модуля сравнения результатов между машинами.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Совпадающие результаты:
    - Одинаковые pydantic-объекты — без ошибок.
    - Пустые pydantic-объекты одного типа — без ошибок.
    - Одинаковые примитивы (int, str, dict) — без ошибок.

Расходящиеся pydantic-результаты:
    - Одно поле различается — ошибка с именем поля и обоими значениями.
    - Несколько полей различаются — все указываются в differences.
    - Extra-поле в одном результате — обнаруживается как расхождение.

Разные типы:
    - Два pydantic-объекта разных классов — ошибка с указанием типов.
    - Pydantic vs примитив — ошибка с указанием типов.

Расходящиеся примитивы:
    - Разные числа, строки, словари — ошибка с repr обоих значений.

Атрибуты ResultMismatchError:
    - left_name, right_name, differences доступны программно.
    - Наследует AssertionError для корректного отображения в pytest.
"""

import pytest
from pydantic import Field

from action_machine.core.base_result import BaseResult
from action_machine.testing.comparison import ResultMismatchError, compare_results


class OrderResult(BaseResult):
    """Результат заказа для тестов сравнения."""
    order_id: str = Field(default="", description="ID заказа")
    status: str = Field(default="", description="Статус")
    total: float = Field(default=0.0, description="Итого")


class PingResult(BaseResult):
    """Другой тип результата для тестов несовпадения типов."""
    message: str = Field(default="pong", description="Сообщение")


class EmptyResult(BaseResult):
    """Пустой результат без полей."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Совпадающие результаты
# ═════════════════════════════════════════════════════════════════════════════


class TestMatchingResults:

    def test_identical_pydantic(self):
        """Два pydantic-объекта с одинаковыми значениями полей — сравнение проходит без ошибок."""
        left = OrderResult(order_id="ORD-1", status="created", total=100.0)
        right = OrderResult(order_id="ORD-1", status="created", total=100.0)
        compare_results(left, "Async", right, "Sync")

    def test_empty_pydantic(self):
        """Два пустых pydantic-объекта одного типа — сравнение проходит без ошибок."""
        compare_results(EmptyResult(), "Async", EmptyResult(), "Sync")

    def test_identical_int(self):
        """Одинаковые целые числа — сравнение проходит через fallback ==."""
        compare_results(42, "Async", 42, "Sync")

    def test_identical_string(self):
        """Одинаковые строки — сравнение проходит через fallback ==."""
        compare_results("hello", "Async", "hello", "Sync")

    def test_identical_dict(self):
        """Одинаковые словари — сравнение проходит через fallback ==."""
        compare_results({"a": 1}, "Async", {"a": 1}, "Sync")


# ═════════════════════════════════════════════════════════════════════════════
# Расходящиеся pydantic-результаты
# ═════════════════════════════════════════════════════════════════════════════


class TestMismatchPydantic:

    def test_one_field_differs(self):
        """
        Проверяет, что при расхождении одного поля ошибка содержит:

        1. Имя поля — чтобы тестировщик сразу видел где расхождение.
        2. Оба значения в differences — для сравнения без отладки.
        """
        left = OrderResult(order_id="ORD-1", status="created", total=100.0)
        right = OrderResult(order_id="ORD-2", status="created", total=100.0)

        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(left, "Async", right, "Sync")

        err = exc_info.value
        assert len(err.differences) == 1
        assert err.differences[0] == ("order_id", "ORD-1", "ORD-2")

    def test_multiple_fields_differ(self):
        """
        Проверяет, что при расхождении нескольких полей все они попадают в differences:

        Если бы сравнение останавливалось на первом расхождении — тестировщик
        чинил бы поля по одному, перезапуская тесты каждый раз.
        """
        left = OrderResult(order_id="ORD-1", status="created", total=100.0)
        right = OrderResult(order_id="ORD-2", status="paid", total=200.0)

        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(left, "Async", right, "Sync")

        diff_fields = {d[0] for d in exc_info.value.differences}
        assert "order_id" in diff_fields
        assert "status" in diff_fields
        assert "total" in diff_fields

    def test_extra_field_detected(self):
        """
        Проверяет, что extra-поле (записанное через WritableMixin) обнаруживается:

        model_dump() включает extra-поля, поэтому сравнение должно их учитывать.
        Без этого одна машина может добавить отладочное поле, а сравнение не заметит.
        """
        left = OrderResult(order_id="ORD-1", status="created", total=100.0)
        right = OrderResult(order_id="ORD-1", status="created", total=100.0)
        right["debug_info"] = "extra"

        with pytest.raises(ResultMismatchError, match="debug_info"):
            compare_results(left, "Async", right, "Sync")

    def test_error_contains_machine_names(self):
        """
        Проверяет, что сообщение об ошибке содержит имена обеих машин:

        Без имён тестировщик видит "ORD-1 vs ORD-2" но не знает какая машина
        вернула какой результат.
        """
        left = OrderResult(order_id="ORD-1")
        right = OrderResult(order_id="ORD-2")

        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(left, "AsyncMachine", right, "SyncMachine")

        msg = str(exc_info.value)
        assert "AsyncMachine" in msg
        assert "SyncMachine" in msg


# ═════════════════════════════════════════════════════════════════════════════
# Разные типы результатов
# ═════════════════════════════════════════════════════════════════════════════


class TestTypeMismatch:

    def test_different_pydantic_types(self):
        """
        Проверяет, что два pydantic-объекта разных классов дают ошибку с указанием типов:

        OrderResult и PingResult могут случайно иметь одинаковые значения model_dump(),
        но это разные типы — сравнение по типу должно быть первым шагом.
        """
        left = OrderResult(order_id="ORD-1")
        right = PingResult(message="pong")

        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(left, "Async", right, "Sync")

        msg = str(exc_info.value)
        assert "OrderResult" in msg
        assert "PingResult" in msg

    def test_pydantic_vs_primitive(self):
        """Pydantic-объект vs строка — ошибка с указанием типов."""
        with pytest.raises(ResultMismatchError, match="Типы результатов различаются"):
            compare_results(OrderResult(), "Async", "строка", "Sync")

    def test_int_vs_str(self):
        """int vs str — ошибка, даже если значение визуально совпадает ("42" vs 42)."""
        with pytest.raises(ResultMismatchError, match="int"):
            compare_results(42, "Async", "42", "Sync")


# ═════════════════════════════════════════════════════════════════════════════
# Расходящиеся примитивы
# ═════════════════════════════════════════════════════════════════════════════


class TestMismatchPrimitives:

    def test_different_ints(self):
        """Разные числа — ошибка с repr обоих значений."""
        with pytest.raises(ResultMismatchError, match="42"):
            compare_results(42, "Async", 99, "Sync")

    def test_different_strings(self):
        """Разные строки — ошибка с repr обоих значений."""
        with pytest.raises(ResultMismatchError, match="hello"):
            compare_results("hello", "Async", "world", "Sync")


# ═════════════════════════════════════════════════════════════════════════════
# Атрибуты ResultMismatchError
# ═════════════════════════════════════════════════════════════════════════════


class TestResultMismatchErrorAttributes:

    def test_stores_machine_names(self):
        """
        Проверяет, что атрибуты left_name и right_name доступны программно:

        Это позволяет тестам проверять не только текст ошибки,
        но и структурированно читать какие машины участвовали в сравнении.
        """
        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(
                OrderResult(order_id="A"), "MyAsync",
                OrderResult(order_id="B"), "MySync",
            )
        assert exc_info.value.left_name == "MyAsync"
        assert exc_info.value.right_name == "MySync"

    def test_differences_as_tuples(self):
        """
        Проверяет, что differences содержит список кортежей (поле, левое, правое):

        Программный доступ к расхождениям позволяет тестам делать
        точечные проверки без парсинга текста ошибки.
        """
        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(
                OrderResult(order_id="A", status="x", total=1.0), "Async",
                OrderResult(order_id="B", status="x", total=1.0), "Sync",
            )
        diffs = exc_info.value.differences
        assert len(diffs) == 1
        assert diffs[0] == ("order_id", "A", "B")

    def test_empty_differences_for_type_mismatch(self):
        """При расхождении типов differences пуст — расхождение на уровне типов, не полей."""
        with pytest.raises(ResultMismatchError) as exc_info:
            compare_results(42, "Async", "42", "Sync")
        assert exc_info.value.differences == []

    def test_inherits_assertion_error(self):
        """ResultMismatchError наследует AssertionError — pytest отображает как assertion failure."""
        with pytest.raises(AssertionError):
            compare_results(
                OrderResult(order_id="A"), "Async",
                OrderResult(order_id="B"), "Sync",
            )
