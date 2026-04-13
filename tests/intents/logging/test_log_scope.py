# tests/intents/logging/test_log_scope.py
"""
Тесты LogScope — объекта, описывающего местоположение в конвейере выполнения.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

LogScope — объект, хранящий информацию о контексте вызова логгера:
в каком действии, аспекте, плагине, на каком уровне вложенности
и при каком событии происходит логирование [1].

Значения передаются как kwargs и становятся атрибутами экземпляра [3].
LogScope не является pydantic-моделью и не наследует BaseSchema [3].
Это лёгкий объект с динамическими атрибутами и dict-подобным доступом
через __getitem__ [3].

═══════════════════════════════════════════════════════════════════════════════
ПОЛЯ SCOPE
═══════════════════════════════════════════════════════════════════════════════

Для аспектов действий:
    machine, mode, action, aspect, nest_level

Для плагинов:
    machine, mode, plugin, action, event, nest_level

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- as_dotpath() возвращает все непустые строковые значения, объединённые точками.
- Порядок ключей сохраняется, пустые значения пропускаются.
- Результат кешируется после первого вызова.
- Dict-подобный доступ (__getitem__, __contains__, get, keys, values, items) [3].
- to_dict() возвращает копию всех полей.
"""

import pytest

from action_machine.intents.logging.log_scope import LogScope

# ======================================================================
# ТЕСТЫ: as_dotpath()
# ======================================================================

class TestAsDotpath:
    """Метод as_dotpath() формирует строку из всех непустых полей."""

    def test_single_key(self) -> None:
        """Один ключ → просто значение."""
        # Arrange
        scope = LogScope(action="ProcessOrderAction")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "ProcessOrderAction"

    def test_multiple_keys(self) -> None:
        """Несколько ключей → значения через точку."""
        # Arrange
        scope = LogScope(
            action="ProcessOrderAction",
            aspect="validate_user",
            event="before",
        )

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "ProcessOrderAction.validate_user.before"

    def test_skips_empty_values(self) -> None:
        """Пустые строки и None пропускаются."""
        # Arrange
        scope = LogScope(
            action="MyAction",
            aspect="",
            event="start",
            extra=None,
        )

        # Act
        result = scope.as_dotpath()

        # Assert — aspect пропущен, extra пропущен
        assert result == "MyAction.start"

    def test_preserves_order(self) -> None:
        """Порядок ключей соответствует порядку kwargs при создании."""
        # Arrange
        scope = LogScope(first="1", second="2", third="3")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "1.2.3"

    def test_caches_result(self) -> None:
        """Результат кешируется после первого вызова."""
        # Arrange
        scope = LogScope(action="MyAction", aspect="load")

        # Act
        first = scope.as_dotpath()
        second = scope.as_dotpath()

        # Assert
        assert first == "MyAction.load"
        assert second == "MyAction.load"
        assert first is second
        assert scope._cached_path == "MyAction.load"

    def test_empty_scope(self) -> None:
        """Пустой scope → пустая строка."""
        # Arrange
        scope = LogScope()

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == ""

    def test_scope_with_unicode(self) -> None:
        """Юникодные символы корректно включаются в dotpath."""
        # Arrange
        scope = LogScope(action="действие", event="🚀 старт")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert "действие" in result
        assert "🚀" in result

    def test_scope_with_special_characters(self) -> None:
        """Специальные символы (точки, слеши) не обрабатываются особым образом."""
        # Arrange
        scope = LogScope(action="Test.Action", event="before:start", path="/api/v1/test")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "Test.Action.before:start./api/v1/test"


# ======================================================================
# ТЕСТЫ: Dict-подобный доступ (LogScope)
# ======================================================================

class TestDictAccess:
    """LogScope поддерживает dict-подобный доступ через __getitem__."""

    def test_getitem(self) -> None:
        """__getitem__ возвращает значение поля."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act & Assert
        assert scope["action"] == "MyAction"

    def test_getitem_missing_raises_key_error(self) -> None:
        """Несуществующий ключ → KeyError."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act & Assert
        with pytest.raises(KeyError):
            _ = scope["missing"]

    def test_contains(self) -> None:
        """Оператор in проверяет наличие атрибута."""
        # Arrange
        scope = LogScope(action="MyAction", aspect="load")

        # Act & Assert
        assert "action" in scope
        assert "aspect" in scope
        assert "missing" not in scope

    def test_get_with_default(self) -> None:
        """get() возвращает значение или default."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act & Assert
        assert scope.get("action") == "MyAction"
        assert scope.get("missing", "fallback") == "fallback"
        assert scope.get("missing") is None

    def test_keys(self) -> None:
        """keys() возвращает список имён публичных полей."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C")

        # Act
        keys = scope.keys()

        # Assert
        assert set(keys) == {"action", "aspect", "event"}

    def test_values(self) -> None:
        """values() возвращает список значений."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C")

        # Act
        values = scope.values()

        # Assert
        assert set(values) == {"A", "B", "C"}

    def test_items(self) -> None:
        """items() возвращает пары (ключ, значение)."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C")

        # Act
        items = scope.items()

        # Assert
        assert len(items) == 3
        assert ("action", "A") in items
        assert ("aspect", "B") in items
        assert ("event", "C") in items


# ======================================================================
# ТЕСТЫ: to_dict()
# ======================================================================

class TestToDict:
    """to_dict() возвращает копию всех полей."""

    def test_returns_copy(self) -> None:
        """to_dict() возвращает новый словарь, изменения не влияют на scope."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act
        d = scope.to_dict()
        d["action"] = "Modified"

        # Assert
        assert scope["action"] == "MyAction"
        assert d["action"] == "Modified"

    def test_includes_all_fields(self) -> None:
        """to_dict() включает все переданные поля."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C", nest_level=2)

        # Act
        d = scope.to_dict()

        # Assert
        assert d == {"action": "A", "aspect": "B", "event": "C", "nest_level": 2}


# ======================================================================
# ТЕСТЫ: Различные конфигурации scope
# ======================================================================

class TestDifferentScopes:
    """Различные наборы полей для scope."""

    def test_aspect_scope(self) -> None:
        """Scope для аспекта действия."""
        # Arrange & Act
        scope = LogScope(
            machine="ActionProductMachine",
            mode="production",
            action="module.CreateOrderAction",
            aspect="process_payment",
            nest_level=0,
        )

        # Assert
        assert scope.as_dotpath() == "ActionProductMachine.production.module.CreateOrderAction.process_payment.0"
        assert scope["machine"] == "ActionProductMachine"
        assert scope["aspect"] == "process_payment"

    def test_plugin_scope(self) -> None:
        """Scope для обработчика плагина."""
        # Arrange & Act
        scope = LogScope(
            machine="ActionProductMachine",
            mode="production",
            plugin="MetricsPlugin",
            action="module.CreateOrderAction",
            event="global_finish",
            nest_level=1,
        )

        # Assert
        assert scope.as_dotpath() == "ActionProductMachine.production.MetricsPlugin.module.CreateOrderAction.global_finish.1"
        assert "plugin" in scope
        assert "event" in scope
        assert "aspect" not in scope

    def test_empty_string_key(self) -> None:
        """Пустое строковое значение пропускается в dotpath, но поле существует."""
        # Arrange
        scope = LogScope(action="", event="start")

        # Act
        dotpath = scope.as_dotpath()

        # Assert — action пропущен, event остался
        assert dotpath == "start"
        assert "action" in scope
        assert scope["action"] == ""

    def test_none_key(self) -> None:
        """None-значение пропускается в dotpath."""
        # Arrange
        scope = LogScope(action="MyAction", aspect=None, event="start")

        # Act
        dotpath = scope.as_dotpath()

        # Assert — aspect пропущен
        assert dotpath == "MyAction.start"
