"""
Тесты класса LogScope.

LogScope — обёртка над словарём для описания местоположения в конвейере.
Проверяем:
- Создание скоупа с разными ключами
- Метод as_dotpath() и кеширование
- Dict-подобный интерфейс (__getitem__, __contains__, get)
- Неизменяемость после создания
"""

import pytest

from action_machine.Logging.log_scope import LogScope


class TestLogScope:
    """
    Тесты класса LogScope.

    LogScope наследует collections.abc.Mapping, поэтому методы
    keys(), values(), items() возвращают view-объекты, а не списки.
    В тестах используем list() для приведения к спискам перед
    сравнением — это работает единообразно.
    """

    # ------------------------------------------------------------------
    # ТЕСТЫ: as_dotpath() — склейка значений через точку
    # ------------------------------------------------------------------

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
        scope = LogScope(action="MyAction", aspect="", event="start", extra="")
        assert scope.as_dotpath() == "MyAction.start"

    def test_as_dotpath_with_none_values(self) -> None:
        """as_dotpath пропускает None значения (они не добавляются в словарь)."""
        # None нельзя передать напрямую, только через пропуск аргумента
        scope = LogScope(action="MyAction")
        assert scope.as_dotpath() == "MyAction"

    def test_as_dotpath_preserves_order(self) -> None:
        """as_dotpath сохраняет порядок добавления ключей."""
        scope = LogScope(first="1", second="2", third="3")
        assert scope.as_dotpath() == "1.2.3"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Кеширование as_dotpath()
    # ------------------------------------------------------------------

    def test_as_dotpath_cached(self) -> None:
        """as_dotpath кеширует результат при повторном вызове."""
        scope = LogScope(action="MyAction", aspect="load")

        # Первый вызов — вычисляет и кеширует
        result1 = scope.as_dotpath()
        assert result1 == "MyAction.load"

        # Проверяем что кеш заполнился
        assert scope._cached_path == "MyAction.load"

        # Второй вызов — возвращает из кеша
        result2 = scope.as_dotpath()
        assert result2 == "MyAction.load"

        # Убеждаемся что результат тот же объект (кеш)
        assert result2 is result1

    # ------------------------------------------------------------------
    # ТЕСТЫ: Dict-подобный доступ
    # ------------------------------------------------------------------

    def test_getitem(self) -> None:
        """Доступ по ключу через __getitem__."""
        scope = LogScope(action="MyAction")
        assert scope["action"] == "MyAction"

    def test_getitem_missing_raises_keyerror(self) -> None:
        """__getitem__ бросает KeyError для отсутствующего ключа."""
        scope = LogScope(action="MyAction")
        with pytest.raises(KeyError, match="missing"):
            _ = scope["missing"]

    def test_contains(self) -> None:
        """Оператор in проверяет наличие ключа."""
        scope = LogScope(action="MyAction", aspect="load")
        assert "action" in scope
        assert "aspect" in scope
        assert "missing" not in scope

    def test_get_with_default(self) -> None:
        """get возвращает default для отсутствующего ключа."""
        scope = LogScope(action="MyAction")
        assert scope.get("action") == "MyAction"
        assert scope.get("missing", "fallback") == "fallback"
        assert scope.get("missing") is None

    def test_get_existing_key(self) -> None:
        """get возвращает значение для существующего ключа."""
        scope = LogScope(action="MyAction", value="test")
        assert scope.get("value") == "test"

    def test_len(self) -> None:
        """len() возвращает количество ключей."""
        scope = LogScope(action="A", aspect="B")
        assert len(scope) == 2
        assert len(LogScope()) == 0

    def test_iter(self) -> None:
        """iter() возвращает итератор по ключам в порядке добавления."""
        scope = LogScope(action="A", aspect="B", event="C")
        assert list(scope) == ["action", "aspect", "event"]

    def test_keys(self) -> None:
        """keys() возвращает ключи в порядке добавления."""
        scope = LogScope(action="A", aspect="B", event="C")
        assert list(scope.keys()) == ["action", "aspect", "event"]

    def test_values(self) -> None:
        """values() возвращает значения в порядке добавления."""
        scope = LogScope(action="A", aspect="B", event="C")
        assert list(scope.values()) == ["A", "B", "C"]

    def test_items(self) -> None:
        """items() возвращает пары (ключ, значение) в порядке добавления."""
        scope = LogScope(action="A", aspect="B", event="C")
        assert list(scope.items()) == [("action", "A"), ("aspect", "B"), ("event", "C")]

    # ------------------------------------------------------------------
    # ТЕСТЫ: Неизменяемость и копирование
    # ------------------------------------------------------------------

    def test_to_dict_returns_copy(self) -> None:
        """to_dict возвращает копию, изменение не влияет на скоуп."""
        scope = LogScope(action="MyAction")
        d = scope.to_dict()
        d["action"] = "Modified"
        assert scope["action"] == "MyAction"
        assert d["action"] == "Modified"

    def test_cannot_modify_through_to_dict(self) -> None:
        """Изменение словаря из to_dict не влияет на оригинал."""
        scope = LogScope(action="A", aspect="B")
        d = scope.to_dict()
        d["new_key"] = "value"
        assert "new_key" not in scope
        assert len(scope) == 2

    # ------------------------------------------------------------------
    # ТЕСТЫ: Разные длины и содержимое
    # ------------------------------------------------------------------

    def test_different_scope_lengths(self) -> None:
        """Скоупы могут иметь разную длину и содержание."""
        scope1 = LogScope(action="A")
        scope2 = LogScope(action="A", aspect="B", event="C")
        scope3 = LogScope(action="A", plugin="MetricsPlugin")
        scope4 = LogScope(action="A", aspect="B", nested_action="ChildAction")

        assert scope1.as_dotpath() == "A"
        assert scope2.as_dotpath() == "A.B.C"
        assert scope3.as_dotpath() == "A.MetricsPlugin"
        assert scope4.as_dotpath() == "A.B.ChildAction"

    def test_scope_with_special_characters(self) -> None:
        """Скоуп может содержать специальные символы в значениях."""
        scope = LogScope(action="Test.Action", event="before:start", path="/api/v1/test")
        assert scope.as_dotpath() == "Test.Action.before:start./api/v1/test"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Строковое представление
    # ------------------------------------------------------------------

    def test_repr(self) -> None:
        """repr возвращает читаемое строковое представление."""
        scope = LogScope(action="MyAction")
        assert repr(scope) == "LogScope(action='MyAction')"

    def test_repr_multiple_keys(self) -> None:
        """repr с несколькими ключами."""
        scope = LogScope(action="A", aspect="B", event="C")
        expected = "LogScope(action='A', aspect='B', event='C')"
        assert repr(scope) == expected

    def test_repr_empty(self) -> None:
        """repr для пустого скоупа."""
        scope = LogScope()
        assert repr(scope) == "LogScope()"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Граничные случаи
    # ------------------------------------------------------------------

    def test_scope_with_empty_string_key(self) -> None:
        """Скоуп может содержать ключи с пустыми строками (не рекомендуется)."""
        scope = LogScope(action="", event="start")
        # Пустая строка должна игнорироваться в as_dotpath
        assert scope.as_dotpath() == "start"
        # Но ключ существует
        assert "action" in scope
        assert scope["action"] == ""

    def test_scope_with_unicode(self) -> None:
        """Скоуп поддерживает unicode-строки."""
        scope = LogScope(action="действие", event="🚀 старт")
        assert "действие" in scope.as_dotpath()
        assert "🚀" in scope.as_dotpath()
