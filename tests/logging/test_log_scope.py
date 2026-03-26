import pytest

from action_machine.logging.log_scope import LogScope


class TestLogScope:

    def test_as_dotpath_single_key(self):
        scope = LogScope(action="ProcessOrderAction")
        assert scope.as_dotpath() == "ProcessOrderAction"

    def test_as_dotpath_multiple_keys(self):
        scope = LogScope(
            action="ProcessOrderAction",
            aspect="validate_user",
            event="before",
        )
        assert scope.as_dotpath() == "ProcessOrderAction.validate_user.before"

    def test_as_dotpath_empty_scope(self):
        scope = LogScope()
        assert scope.as_dotpath() == ""

    def test_as_dotpath_skips_empty_values(self):
        scope = LogScope(action="MyAction", aspect="", event="start", extra="")
        assert scope.as_dotpath() == "MyAction.start"

    def test_as_dotpath_preserves_order(self):
        scope = LogScope(first="1", second="2", third="3")
        assert scope.as_dotpath() == "1.2.3"

    def test_as_dotpath_cached(self):
        scope = LogScope(action="MyAction", aspect="load")
        result1 = scope.as_dotpath()
        assert result1 == "MyAction.load"
        assert scope._cached_path == "MyAction.load"
        result2 = scope.as_dotpath()
        assert result2 == "MyAction.load"
        assert result2 is result1

    def test_getitem(self):
        scope = LogScope(action="MyAction")
        assert scope["action"] == "MyAction"

    def test_getitem_missing_raises_keyerror(self):
        scope = LogScope(action="MyAction")
        with pytest.raises(KeyError, match="missing"):
            _ = scope["missing"]

    def test_contains(self):
        scope = LogScope(action="MyAction", aspect="load")
        assert "action" in scope
        assert "aspect" in scope
        assert "missing" not in scope

    def test_get_with_default(self):
        scope = LogScope(action="MyAction")
        assert scope.get("action") == "MyAction"
        assert scope.get("missing", "fallback") == "fallback"
        assert scope.get("missing") is None

    def test_keys(self):
        scope = LogScope(action="A", aspect="B", event="C")
        # keys() возвращает список публичных атрибутов
        assert set(scope.keys()) == {"action", "aspect", "event"}

    def test_values(self):
        scope = LogScope(action="A", aspect="B", event="C")
        assert set(scope.values()) == {"A", "B", "C"}

    def test_items(self):
        scope = LogScope(action="A", aspect="B", event="C")
        items = scope.items()
        assert len(items) == 3
        assert ("action", "A") in items
        assert ("aspect", "B") in items
        assert ("event", "C") in items

    def test_to_dict_returns_copy(self):
        scope = LogScope(action="MyAction")
        d = scope.to_dict()
        d["action"] = "Modified"
        assert scope["action"] == "MyAction"
        assert d["action"] == "Modified"

    def test_different_scope_lengths(self):
        scope1 = LogScope(action="A")
        scope2 = LogScope(action="A", aspect="B", event="C")
        scope3 = LogScope(action="A", plugin="MetricsPlugin")
        scope4 = LogScope(action="A", aspect="B", nested_action="ChildAction")

        assert scope1.as_dotpath() == "A"
        assert scope2.as_dotpath() == "A.B.C"
        assert scope3.as_dotpath() == "A.MetricsPlugin"
        assert scope4.as_dotpath() == "A.B.ChildAction"

    def test_scope_with_special_characters(self):
        scope = LogScope(action="Test.Action", event="before:start", path="/api/v1/test")
        assert scope.as_dotpath() == "Test.Action.before:start./api/v1/test"

    # Тесты для __repr__ удалены, так как мы не определяем кастомный __repr__

    def test_scope_with_empty_string_key(self):
        scope = LogScope(action="", event="start")
        assert scope.as_dotpath() == "start"
        assert "action" in scope
        assert scope["action"] == ""

    def test_scope_with_unicode(self):
        scope = LogScope(action="действие", event="🚀 старт")
        assert "действие" in scope.as_dotpath()
        assert "🚀" in scope.as_dotpath()